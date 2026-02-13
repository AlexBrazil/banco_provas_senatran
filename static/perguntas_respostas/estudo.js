(function () {
  const pageDataEl = document.getElementById("pr-page-data");
  const voicePayloadEl = document.getElementById("pr-voice-payload");
  if (!pageDataEl) return;

  function parseJson(el, fallback) {
    try {
      return JSON.parse(el.textContent || "");
    } catch (_) {
      return fallback;
    }
  }

  const data = parseJson(pageDataEl, {});
  const voicePayload = voicePayloadEl ? parseJson(voicePayloadEl, {}) : {};
  const autoModeEl = document.getElementById("pr-auto-mode");
  const voiceEnabledEl = document.getElementById("pr-voice-enabled");
  const tempoRangeEl = document.getElementById("pr-tempo-range");
  const tempoInputEl = document.getElementById("pr-tempo-input");
  const autoToggleEl = document.getElementById("pr-auto-toggle");
  const statusEl = document.getElementById("pr-status");

  if (!autoModeEl || !voiceEnabledEl || !tempoRangeEl || !tempoInputEl || !autoToggleEl || !statusEl) return;

  const tempoMin = Number(data.tempoMin || 1);
  const tempoMax = Number(data.tempoMax || 120);
  const nextUrl = data.nextUrl || "";
  const hasNext = Boolean(data.hasNext);
  const saveTempoUrl = data.saveTempoUrl || "";
  const searchParams = new URLSearchParams(window.location.search || "");
  const autoFromUrl = searchParams.get("auto");
  const voiceFromUrl = searchParams.get("voice");
  let timer = null;
  let autoRunning = false;
  let voiceBlocked = false;
  let speechRunToken = 0;

  function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split("; ") : [];
    for (const c of cookies) {
      const parts = c.split("=");
      const key = decodeURIComponent(parts[0] || "");
      if (key === name) {
        return decodeURIComponent(parts.slice(1).join("="));
      }
    }
    return "";
  }

  function clampTempo(raw) {
    const num = Number(raw);
    if (!Number.isFinite(num)) return tempoMin;
    return Math.max(tempoMin, Math.min(tempoMax, Math.round(num)));
  }

  function currentTempo() {
    return clampTempo(tempoRangeEl.value);
  }

  function syncTempoInputs(newValue) {
    const v = clampTempo(newValue);
    tempoRangeEl.value = String(v);
    tempoInputEl.value = String(v);
  }

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function withStudyState(rawUrl) {
    if (!rawUrl) return "";
    const url = new URL(rawUrl, window.location.origin);
    url.searchParams.set("auto", autoModeEl.checked ? "1" : "0");
    url.searchParams.set("voice", voiceEnabledEl.checked ? "1" : "0");
    url.searchParams.set("tempo", String(currentTempo()));
    return `${url.pathname}${url.search}`;
  }

  function syncNavLinks() {
    const links = document.querySelectorAll(".pr-nav a[href]");
    links.forEach((link) => {
      const href = link.getAttribute("href") || "";
      if (!href) return;
      link.setAttribute("href", withStudyState(href));
    });
  }

  async function persistTempo() {
    if (!saveTempoUrl) return;
    const body = new URLSearchParams();
    body.set("tempo", String(currentTempo()));
    body.set("modo_automatico", autoModeEl.checked ? "1" : "0");

    try {
      await fetch(saveTempoUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: body.toString(),
        credentials: "same-origin",
      });
    } catch (_) {
      // Keep flow running even on transient network failure.
    }
  }

  function clearRunState() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    autoRunning = false;
    speechRunToken += 1;
    window.speechSynthesis?.cancel();
    autoToggleEl.textContent = "Iniciar automatico";
  }

  function stopOnNavigate() {
    clearRunState();
  }

  function speakQueue() {
    if (!voiceEnabledEl.checked || !("speechSynthesis" in window)) {
      return Promise.resolve();
    }

    const chunks = [];
    if (voicePayload.intro) chunks.push(voicePayload.intro);
    if (voicePayload.enunciado) chunks.push(`Enunciado. ${voicePayload.enunciado}`);
    if (voicePayload.resposta) chunks.push(`Resposta correta. ${voicePayload.resposta}`);
    if (voicePayload.comentario) chunks.push(`Comentario. ${voicePayload.comentario}`);
    if (!chunks.length) return Promise.resolve();

    window.speechSynthesis.cancel();
    return new Promise((resolve) => {
      const runToken = ++speechRunToken;
      let idx = 0;
      let finished = false;
      let firstStarted = false;

      const settle = function () {
        if (finished) return;
        finished = true;
        resolve();
      };

      const startupGuard = setTimeout(() => {
        if (runToken !== speechRunToken) {
          settle();
          return;
        }
        if (!firstStarted) {
          voiceBlocked = true;
          window.speechSynthesis.cancel();
          settle();
        }
      }, 2200);

      const playNext = function () {
        if (runToken !== speechRunToken) {
          clearTimeout(startupGuard);
          settle();
          return;
        }
        if (idx >= chunks.length) {
          clearTimeout(startupGuard);
          settle();
          return;
        }
        const utter = new SpeechSynthesisUtterance(chunks[idx]);
        utter.lang = "pt-BR";
        utter.rate = 1;
        utter.pitch = 1;
        utter.onstart = function () {
          firstStarted = true;
        };
        utter.onend = function () {
          if (runToken !== speechRunToken) {
            clearTimeout(startupGuard);
            settle();
            return;
          }
          idx += 1;
          playNext();
        };
        utter.onerror = function () {
          if (runToken !== speechRunToken) {
            clearTimeout(startupGuard);
            settle();
            return;
          }
          idx += 1;
          playNext();
        };
        window.speechSynthesis.speak(utter);
      };
      playNext();
    });
  }

  async function runAutomatic() {
    if (!autoRunning) return;
    if (!hasNext || !nextUrl) {
      clearRunState();
      setStatus("Sessao concluida.");
      return;
    }
    setStatus("Modo automatico em execucao.");
    await speakQueue();
    if (!autoRunning) return;
    if (voiceBlocked) {
      setStatus("Modo automatico em execucao. Leitura automatica bloqueada pelo navegador nesta pagina.");
      voiceBlocked = false;
    }
    const waitMs = currentTempo() * 1000;
    timer = setTimeout(() => {
      window.location.href = withStudyState(nextUrl);
    }, waitMs);
  }

  function startAutomatic() {
    if (!autoModeEl.checked) {
      setStatus("Ative o modo automatico para iniciar.");
      return;
    }
    if (!hasNext || !nextUrl) {
      setStatus("Nao existe proxima questao.");
      return;
    }
    autoRunning = true;
    autoToggleEl.textContent = "Parar automatico";
    runAutomatic();
  }

  function stopAutomatic(statusText) {
    clearRunState();
    setStatus(statusText || "Modo manual ativo.");
  }

  autoToggleEl.addEventListener("click", () => {
    if (autoRunning) {
      stopAutomatic("Modo manual ativo.");
      return;
    }
    startAutomatic();
  });

  autoModeEl.addEventListener("change", () => {
    persistTempo();
    syncNavLinks();
    if (!autoModeEl.checked && autoRunning) {
      stopAutomatic("Modo manual ativo.");
    }
  });

  voiceEnabledEl.addEventListener("change", () => {
    syncNavLinks();
    if (!voiceEnabledEl.checked) {
      window.speechSynthesis?.cancel();
    }
  });

  let saveTimer = null;
  function schedulePersist() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      persistTempo();
    }, 350);
  }

  tempoRangeEl.addEventListener("input", () => {
    syncTempoInputs(tempoRangeEl.value);
    syncNavLinks();
    schedulePersist();
  });

  tempoInputEl.addEventListener("input", () => {
    syncTempoInputs(tempoInputEl.value);
    syncNavLinks();
    schedulePersist();
  });

  document.querySelectorAll(".pr-header-actions a, .pr-nav a").forEach((link) => {
    link.addEventListener("click", stopOnNavigate);
  });

  window.addEventListener("beforeunload", () => {
    clearRunState();
  });

  syncTempoInputs(data.tempoAtual || tempoRangeEl.value);
  if (searchParams.get("tempo")) {
    syncTempoInputs(searchParams.get("tempo"));
  }

  const autoDefault = autoFromUrl === null ? Boolean(data.autoDefault) : autoFromUrl === "1";
  const voiceDefault = voiceFromUrl === null ? Boolean(data.voiceDefault) : voiceFromUrl === "1";
  autoModeEl.checked = autoDefault;
  voiceEnabledEl.checked = voiceDefault;
  syncNavLinks();

  if (autoFromUrl === "1" && hasNext) {
    startAutomatic();
  } else {
    setStatus(autoModeEl.checked ? "Modo automatico pronto para iniciar." : "Modo manual ativo.");
  }
})();
