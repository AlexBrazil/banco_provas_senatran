(function () {
  const $ = (sel) => document.querySelector(sel);

  const curso = $("#curso_id");
  const modulo = $("#modulo_id");
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
    modulo.value = "";
    dificuldade.value = "";
    comImagem.checked = false;
    soPlacas.checked = false;
    qtd.value = "10";
  }

  async function fetchJSON(url) {
    const resp = await fetch(url, { headers: { "Accept": "application/json" } });
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
      setHint("Selecione um curso para ver as estatísticas.");
      return;
    }

    setHint("Carregando estatísticas...");
    const url = `${window.SIMULADO_ENDPOINTS.stats}?${getStatsParams().toString()}`;

    const data = await fetchJSON(url);

    const painel = data.painel || {};
    const porD = (painel.por_dificuldade || {});
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

    // habilita iniciar se tem questões
    const okToStart = Number(totalDisponivel || 0) > 0;
    setEnabled(btnIniciar, okToStart);
    setEnabled(qtd, true);
    setEnabled(dificuldade, true);
    setEnabled(comImagem, true);
    setEnabled(soPlacas, true);
    setEnabled(btnLimpar, true);

    // Ajusta max de qtd dinamicamente (UX)
    const max = Math.min(50, Number(totalDisponivel || 0));
    qtd.max = String(max);
    if (Number(qtd.value || 10) > max) qtd.value = String(max);

    setHint(okToStart ? "Pronto para iniciar." : "Não há questões para os filtros selecionados.");
  }

  // Eventos
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

    if (!cursoId) {
      modulo.innerHTML = `<option value="">Selecione um curso primeiro...</option>`;
      setEnabled(btnIniciar, false);
      setHint("Selecione um curso para ver as estatísticas.");
      return;
    }

    try {
      await loadModulos(cursoId);
      await refreshStats();
    } catch (e) {
      showError(e.message);
      setEnabled(btnIniciar, false);
      setHint("Falha ao carregar dados.");
    }
  });

  // atualizar stats quando mexe nos filtros
  [modulo, dificuldade, qtd, comImagem, soPlacas].forEach((el) => {
    el.addEventListener("change", async () => {
      try {
        await refreshStats();
      } catch (e) {
        showError(e.message);
        setEnabled(btnIniciar, false);
        setHint("Falha ao carregar estatísticas.");
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

  // Estado inicial
  setEnabled(modulo, false);
  setEnabled(dificuldade, false);
  setEnabled(qtd, false);
  setEnabled(comImagem, false);
  setEnabled(soPlacas, false);
  setEnabled(btnIniciar, false);
  setEnabled(btnLimpar, false);
  resetStatsUI();

  // Início rápido: preenche filtros e envia com o curso padrão
  if (btnInicioRapido) {
    const quickCursoId = btnInicioRapido.dataset.cursoId || "";
    if (!quickCursoId) {
      setEnabled(btnInicioRapido, false);
    } else {
      btnInicioRapido.addEventListener("click", async () => {
        try {
          clearError();
          curso.value = quickCursoId;
          modulo.value = "";
          dificuldade.value = "";
          comImagem.checked = false;
          soPlacas.checked = false;
          qtd.value = "10";

          // habilita campos necessários
          setEnabled(modulo, true);
          setEnabled(dificuldade, true);
          setEnabled(qtd, true);
          setEnabled(comImagem, true);
          setEnabled(soPlacas, true);
          setEnabled(btnLimpar, true);
          setEnabled(btnIniciar, true);

          // tenta carregar módulos/stats, mas não bloqueia o submit
          try { await loadModulos(quickCursoId); } catch (e) { /* ignore */ }
          try { await refreshStats(); } catch (e) { /* ignore */ }

          document.getElementById("simulado-form").submit();
        } catch (e) {
          showError(e.message);
        }
      });
    }
  }
})();
