(function () {
  const $ = (sel) => document.querySelector(sel);

  // Config injetada pelo backend (JSON no template)
  const DEFAULT_SIMCFG = {
    defaults: {
      modo: "PROVA",
      dificuldade: "",
      com_imagem: false,
      so_placas: false,
      qtd: 10,
    },
    inicio_rapido: {
      habilitado: true,
      label: "Início rápido",
      hint: "",
      tooltip: "Curso padrão não encontrado",
      override_filtros: {},
    },
    ui: {
      messages: {
        selecione_curso: "Selecione um curso para ver as estatísticas.",
        carregando_stats: "Carregando estatísticas...",
        pronto: "Pronto para iniciar.",
        sem_questoes: "Não há questões para os filtros selecionados.",
        erro_generico: "Falha ao carregar dados.",
      },
    },
    limits: { qtd_min: 1, qtd_max: 50, modes: ["PROVA", "ESTUDO"] },
    quick_curso_id: "",
  };

  function deepMerge(target, source) {
    const result = { ...target };
    if (!source || typeof source !== "object") return result;
    for (const [k, v] of Object.entries(source)) {
      if (v && typeof v === "object" && !Array.isArray(v)) {
        result[k] = deepMerge(target[k] || {}, v);
      } else {
        result[k] = v;
      }
    }
    return result;
  }

  function loadSimuladoConfig() {
    const el = document.getElementById("simulado-config");
    if (!el) return { ...DEFAULT_SIMCFG };
    try {
      const parsed = JSON.parse(el.textContent || "{}");
      return deepMerge(DEFAULT_SIMCFG, parsed);
    } catch (e) {
      return { ...DEFAULT_SIMCFG };
    }
  }

  const SIMCFG = loadSimuladoConfig();
  const limits = SIMCFG.limits || DEFAULT_SIMCFG.limits;

  function getMsg(key, fallback) {
    return (SIMCFG.ui && SIMCFG.ui.messages && SIMCFG.ui.messages[key]) || fallback;
  }

  function getDefaults() {
    return SIMCFG.defaults || DEFAULT_SIMCFG.defaults;
  }

  function getQuickFilters() {
    const base = getDefaults();
    const override = (SIMCFG.inicio_rapido && SIMCFG.inicio_rapido.override_filtros) || {};
    return {
      modo: override.modo || base.modo || "PROVA",
      dificuldade: override.dificuldade || base.dificuldade || "",
      com_imagem: Boolean(override.com_imagem ?? base.com_imagem ?? false),
      so_placas: Boolean(override.so_placas ?? base.so_placas ?? false),
      qtd: Number(override.qtd ?? base.qtd ?? 10),
    };
  }

  const curso = $("#curso_id");
  const modulo = $("#modulo_id");
  const modo = $("#modo");
  const dificuldade = $("#dificuldade");
  const qtd = $("#qtd");
  const comImagem = $("#com_imagem");
  const soPlacas = $("#so_placas");

  const btnIniciar = $("#btn-iniciar");
  const btnLimpar = $("#btn-limpar");
  const btnInicioRapido = $("#btn-inicio-rapido");

  const statTotalDisponivel = $("#stat-total");
  const statComImagem = $("#stat-imagem");
  const statPlacas = $("#stat-placas");
  const statFacil = $("#stat-facil");
  const statIntermediario = $("#stat-intermediario");
  const statDificil = $("#stat-dificil");

  const statsHint = $("#stats_hint");
  const statsError = $("#stats_error");

  function setEnabled(el, enabled) {
    if (!el) return;
    el.disabled = !enabled;
  }

  function showError(msg) {
    statsError.textContent = msg;
    statsError.classList.remove("is-hidden");
  }

  function clearError() {
    statsError.textContent = "";
    statsError.classList.add("is-hidden");
  }

  function setHint(msg) {
    statsHint.textContent = msg;
  }

  function resetStatsUI() {
    statTotalDisponivel.textContent = "—";
    statComImagem.textContent = "—";
    statPlacas.textContent = "—";
    statFacil.textContent = "—";
    statIntermediario.textContent = "—";
    statDificil.textContent = "—";
  }

  function resetFiltersOnly() {
    const d = getDefaults();
    if (modulo) modulo.value = "";
    if (dificuldade) dificuldade.value = d.dificuldade || "";
    if (modo) modo.value = d.modo || "PROVA";
    if (comImagem) comImagem.checked = Boolean(d.com_imagem);
    if (soPlacas) soPlacas.checked = Boolean(d.so_placas);
    if (qtd) {
      const min = Number(limits.qtd_min || 1);
      const max = Number(limits.qtd_max || 50);
      const val = Number(d.qtd || min);
      qtd.min = String(min);
      qtd.max = String(max);
      qtd.value = String(Math.min(Math.max(val, min), max));
    }
  }

  async function fetchJSON(url) {
    const resp = await fetch(url, { headers: { Accept: "application/json" } });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || data.ok === false) {
      const msg = data && data.error ? data.error : `Erro ao buscar ${url}`;
      throw new Error(msg);
    }
    return data;
  }

  async function loadModulos(cursoId) {
    setEnabled(modulo, false);
    modulo.innerHTML = `<option value="">Carregando...</option>`;

    const url = `${window.SIMULADO_ENDPOINTS.modulos}?curso_id=${encodeURIComponent(cursoId)}`;
    const data = await fetchJSON(url);

    const items = data.modulos || [];
    let html = `<option value="">Todos</option>`;
    for (const m of items) {
      html += `<option value="${m.id}">M${m.ordem} - ${m.nome}</option>`;
    }
    modulo.innerHTML = html;
    setEnabled(modulo, true);
  }

  function getStatsParams() {
    const cursoId = curso.value;
    const params = new URLSearchParams();
    params.set("curso_id", cursoId);

    if (modulo.value) params.set("modulo_id", modulo.value);
    if (dificuldade.value) params.set("dificuldade", dificuldade.value);

    params.set("com_imagem", comImagem.checked ? "1" : "0");
    params.set("so_placas", soPlacas.checked ? "1" : "0");
    return params;
  }

  async function refreshStats() {
    clearError();

    const cursoId = curso.value;
    if (!cursoId) {
      resetStatsUI();
      setHint(getMsg("selecione_curso", "Selecione um curso para ver as estatísticas."));
      return;
    }

    setHint(getMsg("carregando_stats", "Carregando estatísticas..."));
    const url = `${window.SIMULADO_ENDPOINTS.stats}?${getStatsParams().toString()}`;

    const data = await fetchJSON(url);

    const painel = data.painel || {};
    const porD = painel.por_dificuldade || {};
    const totalDisponivel = data.total_disponivel;

    statTotalDisponivel.textContent = String(totalDisponivel ?? "—");
    statComImagem.textContent = String(painel.com_imagem ?? "—");
    statPlacas.textContent = String(painel.placas ?? "—");

    const f = porD.FACIL ?? 0;
    const i = porD.INTERMEDIARIO ?? 0;
    const d = porD.DIFICIL ?? 0;
    statFacil.textContent = String(f);
    statIntermediario.textContent = String(i);
    statDificil.textContent = String(d);

    const okToStart = Number(totalDisponivel || 0) > 0;
    setEnabled(btnIniciar, okToStart);
    setEnabled(qtd, true);
    setEnabled(dificuldade, true);
    setEnabled(comImagem, true);
    setEnabled(soPlacas, true);
    setEnabled(btnLimpar, true);
    if (modo) setEnabled(modo, true);

    const maxLimit = Number(limits.qtd_max || 50);
    const max = Math.min(maxLimit, Number(totalDisponivel || 0));
    qtd.max = String(max);
    if (Number(qtd.value || limits.qtd_min || 1) > max) qtd.value = String(max);

    setHint(
      okToStart
        ? getMsg("pronto", "Pronto para iniciar.")
        : getMsg("sem_questoes", "Não há questões para os filtros selecionados.")
    );
  }

  curso.addEventListener("change", async () => {
    clearError();
    resetFiltersOnly();
    resetStatsUI();

    const cursoId = curso.value;
    const enabled = Boolean(cursoId);

    setEnabled(modulo, enabled);
    setEnabled(dificuldade, enabled);
    setEnabled(qtd, enabled);
    setEnabled(comImagem, enabled);
    setEnabled(soPlacas, enabled);
    setEnabled(btnLimpar, enabled);
    if (modo) setEnabled(modo, enabled);

    if (!cursoId) {
      modulo.innerHTML = `<option value="">Selecione um curso primeiro...</option>`;
      setEnabled(btnIniciar, false);
      setHint(getMsg("selecione_curso", "Selecione um curso para ver as estatísticas."));
      return;
    }

    try {
      await loadModulos(cursoId);
      await refreshStats();
    } catch (e) {
      showError(e.message);
      setEnabled(btnIniciar, false);
      setHint(getMsg("erro_generico", "Falha ao carregar dados."));
    }
  });

  [modulo, dificuldade, qtd, comImagem, soPlacas].forEach((el) => {
    el.addEventListener("change", async () => {
      try {
        await refreshStats();
      } catch (e) {
        showError(e.message);
        setEnabled(btnIniciar, false);
        setHint(getMsg("erro_generico", "Falha ao carregar estatísticas."));
      }
    });
  });

  btnLimpar.addEventListener("click", async () => {
    resetFiltersOnly();
    try {
      await refreshStats();
    } catch (e) {
      showError(e.message);
    }
  });

  setEnabled(modulo, false);
  setEnabled(dificuldade, false);
  setEnabled(qtd, false);
  setEnabled(comImagem, false);
  setEnabled(soPlacas, false);
  setEnabled(btnIniciar, false);
  setEnabled(btnLimpar, false);
  if (modo) setEnabled(modo, false);
  resetStatsUI();
  setHint(getMsg("selecione_curso", "Selecione um curso para ver as estatísticas."));

  if (btnInicioRapido) {
    const quickCursoId = btnInicioRapido.dataset.cursoId || SIMCFG.quick_curso_id || "";
    const quickFilters = getQuickFilters();
    if (!quickCursoId) {
      setEnabled(btnInicioRapido, false);
    } else {
      btnInicioRapido.addEventListener("click", async () => {
        try {
          clearError();
          curso.value = quickCursoId;
          modulo.value = "";
          dificuldade.value = quickFilters.dificuldade || "";
          if (modo) modo.value = quickFilters.modo || "PROVA";
          comImagem.checked = Boolean(quickFilters.com_imagem);
          soPlacas.checked = Boolean(quickFilters.so_placas);
          const minQ = Number(limits.qtd_min || 1);
          const maxQ = Number(limits.qtd_max || 50);
          const valQ = Math.min(Math.max(Number(quickFilters.qtd || minQ), minQ), maxQ);
          qtd.value = String(valQ);

          setEnabled(modulo, true);
          setEnabled(dificuldade, true);
          setEnabled(qtd, true);
          setEnabled(comImagem, true);
          setEnabled(soPlacas, true);
          setEnabled(btnLimpar, true);
          setEnabled(btnIniciar, true);
          if (modo) setEnabled(modo, true);

          try {
            await loadModulos(quickCursoId);
          } catch (e) {
            /* ignore */
          }
          try {
            await refreshStats();
          } catch (e) {
            /* ignore */
          }

          document.getElementById("simulado-form").submit();
        } catch (e) {
          showError(e.message);
        }
      });
    }
  }
})();
