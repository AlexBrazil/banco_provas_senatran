(function () {
  const pageDataEl = document.getElementById("pr-page-data");
  const voicePayloadEl = document.getElementById("pr-voice-payload");
  const autoToggleEl = document.getElementById("pr-auto-toggle");
  const statusEl = document.getElementById("pr-status");
  if (!pageDataEl || !autoToggleEl || !statusEl) return;

  function parseJson(el, fallback) {
    try {
      return JSON.parse(el.textContent || "");
    } catch (_) {
      return fallback;
    }
  }

  const data = parseJson(pageDataEl, {});
  const payload = voicePayloadEl ? parseJson(voicePayloadEl, {}) : {};
  const hasNext = Boolean(data.hasNext);
  const nextUrl = data.nextUrl || "";
  const tempoSegundos = Number(data.tempoSegundos || 3);
  const searchParams = new URLSearchParams(window.location.search || "");
  const autoFromUrl = searchParams.get("auto");
  const manualNavLinks = Array.from(document.querySelectorAll(".pr-manual-nav"));
  let timer = null;
  let autoRunning = false;
  let speechRunToken = 0;
  let voiceBlocked = false;

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function withStudyState(rawUrl) {
    if (!rawUrl) return "";
    const url = new URL(rawUrl, window.location.origin);
    url.searchParams.set("auto", autoRunning ? "1" : "0");
    return `${url.pathname}${url.search}`;
  }

  function syncManualNavState(enabled) {
    manualNavLinks.forEach((link) => {
      const originalHref = link.dataset.href || link.getAttribute("href") || "";
      if (!link.dataset.href && originalHref) {
        link.dataset.href = originalHref;
      }
      if (enabled) {
        if (originalHref) {
          link.setAttribute("href", withStudyState(originalHref));
        }
        link.classList.remove("pr-btn-disabled", "pr-btn-inert");
        link.removeAttribute("aria-disabled");
      } else {
        link.classList.add("pr-btn-disabled", "pr-btn-inert");
        link.setAttribute("aria-disabled", "true");
        link.removeAttribute("href");
      }
    });
  }

  function clearRunState() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    autoRunning = false;
    speechRunToken += 1;
    window.speechSynthesis?.cancel();
    autoToggleEl.textContent = "Iniciar leitura e avanco automatico";
    syncManualNavState(true);
  }

  function stopAutomatic(message) {
    clearRunState();
    setStatus(message || "Modo manual ativo.");
  }

  function getChunks() {
    const chunks = [];
    if (payload.intro) chunks.push(payload.intro);
    if (payload.enunciado) chunks.push(`Enunciado. ${payload.enunciado}`);
    if (payload.resposta) chunks.push(`Resposta correta. ${payload.resposta}`);
    if (payload.comentario) chunks.push(`Comentario. ${payload.comentario}`);
    return chunks;
  }

  function speakQueue() {
    if (!("speechSynthesis" in window)) {
      return Promise.resolve();
    }
    const chunks = getChunks();
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

  async function runAutomaticCycle() {
    if (!autoRunning) return;
    if (!hasNext || !nextUrl) {
      stopAutomatic("Sessao concluida.");
      return;
    }

    setStatus("Leitura e avanco automatico em execucao.");
    await speakQueue();
    if (!autoRunning) return;

    if (voiceBlocked) {
      setStatus("Leitura bloqueada pelo navegador nesta pagina. Avanco automatico mantido.");
      voiceBlocked = false;
    }

    timer = setTimeout(() => {
      window.location.href = withStudyState(nextUrl);
    }, Math.max(1, tempoSegundos) * 1000);
  }

  function startAutomatic() {
    if (!hasNext || !nextUrl) {
      setStatus("Nao existe proxima questao.");
      return;
    }
    autoRunning = true;
    autoToggleEl.textContent = "Parar leitura e avanco automatico";
    syncManualNavState(false);
    runAutomaticCycle();
  }

  autoToggleEl.addEventListener("click", () => {
    if (autoRunning) {
      stopAutomatic("Modo manual ativo.");
    } else {
      startAutomatic();
    }
  });

  document.querySelectorAll(".pr-header-actions a").forEach((link) => {
    link.addEventListener("click", () => {
      clearRunState();
    });
  });

  manualNavLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      if (link.classList.contains("pr-btn-inert")) {
        event.preventDefault();
        return;
      }
      clearRunState();
    });
  });

  window.addEventListener("beforeunload", () => {
    clearRunState();
  });

  syncManualNavState(true);
  if (autoFromUrl === "1" || Boolean(data.autoDefault)) {
    startAutomatic();
  } else {
    setStatus("Modo manual ativo.");
  }
})();
