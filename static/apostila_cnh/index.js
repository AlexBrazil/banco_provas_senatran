(function () {
  const configNode = document.getElementById("acnh-viewer-config");
  if (!configNode) return;

  const statusEl = document.getElementById("acnh-status");
  const titleEl = document.getElementById("acnh-documento-titulo");
  const hintEl = document.getElementById("acnh-gesture-hint");
  const viewerEl = document.querySelector(".acnh-viewer");
  const trackEl = document.getElementById("acnh-canvas-track");
  const canvasPrimary = document.getElementById("acnh-canvas-primary");
  const canvasSecondary = document.getElementById("acnh-canvas-secondary");
  const prevBtn = document.getElementById("acnh-prev-btn");
  const nextBtn = document.getElementById("acnh-next-btn");
  const pageInlineInfoEl = document.getElementById("acnh-page-inline-info");
  const pageInput = document.getElementById("acnh-page-input");
  const pageTotal = document.getElementById("acnh-page-total");
  const goBtn = document.getElementById("acnh-go-btn");
  const zoomOutBtn = document.getElementById("acnh-zoom-out-btn");
  const zoomInBtn = document.getElementById("acnh-zoom-in-btn");
  const zoomLabel = document.getElementById("acnh-zoom-label");
  const openSearchBtn = document.getElementById("acnh-open-search-btn");
  const searchModalEl = document.getElementById("acnh-search-modal");
  const searchModalBackdropEl = document.getElementById("acnh-search-modal-backdrop");
  const closeSearchBtn = document.getElementById("acnh-close-search-btn");
  const searchInput = document.getElementById("acnh-search-input");
  const searchBtn = document.getElementById("acnh-search-btn");
  const searchStatusEl = document.getElementById("acnh-search-status");
  const searchResultsEl = document.getElementById("acnh-search-results");

  const config = JSON.parse(configNode.textContent || "{}");
  const CACHE_WINDOW_RADIUS = 1;
  const CACHE_MAX_PAGES = 3;

  const state = {
    pdfDoc: null,
    pageNum: 1,
    totalPages: 0,
    zoomFactor: 1,
    renderInProgress: false,
    pendingPageNum: null,
    saveTimer: null,
    lastPersistedPage: null,
    saveInFlight: false,
    pendingPersistPage: null,
    searchInFlight: false,
    renderCache: new Map(),
    cacheScaleToken: null,
    prefetchInFlight: false,
    touch: {
      pinchActive: false,
      pinchStartDistance: 0,
      pinchStartZoom: 1,
      pinchPendingZoom: 1,
      swipeStartX: null,
      swipeStartY: null,
      swipeStartAt: null,
    },
  };

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function isZoomActive() {
    return state.zoomFactor > 1.01;
  }

  function isSmartphoneLayout() {
    return window.matchMedia("(max-width: 40em)").matches;
  }

  function clampPage(pageNum) {
    if (!state.totalPages) return Math.max(pageNum, 1);
    return Math.min(Math.max(pageNum, 1), state.totalPages);
  }



  function updateLayoutMode() {
    if (hintEl) {
      if (isZoomActive()) {
        hintEl.textContent =
          "Zoom ativo: arraste para navegar no conteudo. Reduza para 100% para habilitar troca por gesto lateral.";
      } else {
        hintEl.textContent =
          "Dica: em telas touch, use pinca para zoom e deslize lateral para trocar de pagina quando o zoom estiver em 100%.";
      }
    }
    document.body.classList.toggle("acnh-zoom-active", isZoomActive());
  }

  function updateControls() {
    const hasDoc = Boolean(state.pdfDoc);

    prevBtn.disabled = !hasDoc || state.pageNum <= 1 || state.renderInProgress;
    nextBtn.disabled = !hasDoc || state.pageNum >= state.totalPages || state.renderInProgress;
    goBtn.disabled = !hasDoc || state.renderInProgress;
    zoomOutBtn.disabled = !hasDoc || state.renderInProgress;
    zoomInBtn.disabled = !hasDoc || state.renderInProgress;
    pageInput.disabled = !hasDoc || state.renderInProgress;
    pageInput.max = String(state.totalPages || 1);
    pageInput.value = String(state.pageNum || 1);
    pageTotal.textContent = `/ ${state.totalPages || "-"}`;
    if (pageInlineInfoEl) {
      pageInlineInfoEl.textContent = `${state.pageNum || 1} / ${state.totalPages || "-"}`;
    }
    zoomLabel.textContent = `${Math.round(state.zoomFactor * 100)}%`;
    if (openSearchBtn) openSearchBtn.disabled = !hasDoc;
    if (searchBtn) searchBtn.disabled = !hasDoc || state.searchInFlight;
    if (searchInput) searchInput.disabled = !hasDoc || state.searchInFlight;
  }

  function getCsrfToken() {
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (const cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith("csrftoken=")) {
        return decodeURIComponent(trimmed.slice("csrftoken=".length));
      }
    }
    return "";
  }

  function releaseCacheEntry(entry) {
    if (!entry || !entry.canvas) return;
    entry.canvas.width = 0;
    entry.canvas.height = 0;
  }

  function clearRenderCache() {
    for (const entry of state.renderCache.values()) {
      releaseCacheEntry(entry);
    }
    state.renderCache.clear();
    state.cacheScaleToken = null;
  }

  function getScaleToken(scale) {
    return String(Math.round(scale * 1000) / 1000);
  }

  function ensureScaleCacheToken(scale) {
    const token = getScaleToken(scale);
    if (state.cacheScaleToken !== token) {
      clearRenderCache();
      state.cacheScaleToken = token;
    }
    return token;
  }

  function getWindowPages(anchorPage) {
    const pages = [];
    for (let p = anchorPage - CACHE_WINDOW_RADIUS; p <= anchorPage + CACHE_WINDOW_RADIUS; p += 1) {
      if (p >= 1 && p <= state.totalPages) {
        pages.push(p);
      }
    }
    return pages;
  }

  function trimCacheToWindow(anchorPage) {
    const windowSet = new Set(getWindowPages(anchorPage));
    for (const [pageNum, entry] of state.renderCache.entries()) {
      if (!windowSet.has(pageNum)) {
        releaseCacheEntry(entry);
        state.renderCache.delete(pageNum);
      }
    }

    if (state.renderCache.size <= CACHE_MAX_PAGES) return;
    const entries = Array.from(state.renderCache.entries()).sort((a, b) => a[1].usedAt - b[1].usedAt);
    while (state.renderCache.size > CACHE_MAX_PAGES && entries.length) {
      const [pageNum] = entries.shift();
      const entry = state.renderCache.get(pageNum);
      releaseCacheEntry(entry);
      state.renderCache.delete(pageNum);
    }
  }

  async function ensurePageCached(pageNum, renderScale) {
    if (pageNum < 1 || pageNum > state.totalPages) return;
    ensureScaleCacheToken(renderScale);

    const cached = state.renderCache.get(pageNum);
    if (cached) {
      cached.usedAt = Date.now();
      return;
    }

    const page = await state.pdfDoc.getPage(pageNum);
    const viewport = page.getViewport({ scale: renderScale });
    const offscreen = document.createElement("canvas");
    offscreen.width = Math.floor(viewport.width);
    offscreen.height = Math.floor(viewport.height);
    const ctx = offscreen.getContext("2d");
    await page.render({ canvasContext: ctx, viewport }).promise;

    state.renderCache.set(pageNum, {
      canvas: offscreen,
      usedAt: Date.now(),
    });
  }

  function drawCachedPage(pageNum, targetCanvas) {
    const cached = state.renderCache.get(pageNum);
    if (!cached || !cached.canvas) {
      targetCanvas.style.display = "none";
      return false;
    }
    targetCanvas.width = cached.canvas.width;
    targetCanvas.height = cached.canvas.height;
    const ctx = targetCanvas.getContext("2d");
    ctx.clearRect(0, 0, targetCanvas.width, targetCanvas.height);
    ctx.drawImage(cached.canvas, 0, 0);
    targetCanvas.style.display = "block";
    cached.usedAt = Date.now();
    return true;
  }

  async function prefetchWindow(anchorPage, renderScale) {
    if (state.prefetchInFlight || !state.pdfDoc) return;
    const targets = getWindowPages(anchorPage).filter((p) => !state.renderCache.has(p));
    if (!targets.length) {
      trimCacheToWindow(anchorPage);
      return;
    }

    state.prefetchInFlight = true;
    try {
      for (const pageNum of targets) {
        await ensurePageCached(pageNum, renderScale);
      }
      trimCacheToWindow(anchorPage);
    } catch (error) {
      console.error(error);
    } finally {
      state.prefetchInFlight = false;
    }
  }

  async function fetchProgressStartPage() {
    if (!config.api_progresso_url) return 1;
    try {
      const resp = await fetch(config.api_progresso_url, { credentials: "same-origin" });
      const data = await resp.json();
      if (!resp.ok || !data.ok || !data.progresso) return 1;
      const page = Number.parseInt(String(data.progresso.ultima_pagina_lida || "1"), 10);
      const safePage = Number.isFinite(page) ? Math.max(page, 1) : 1;
      state.lastPersistedPage = safePage;
      return safePage;
    } catch (error) {
      console.error(error);
      return 1;
    }
  }

  async function persistProgress(pageNum, { force = false } = {}) {
    if (!config.api_progresso_url) return;
    const safePage = clampPage(pageNum);
    if (!force && state.lastPersistedPage === safePage) return;
    if (state.saveInFlight) {
      state.pendingPersistPage = safePage;
      return;
    }

    state.saveInFlight = true;
    try {
      const resp = await fetch(config.api_progresso_url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({ pagina: safePage }),
      });
      const data = await resp.json();
      if (resp.ok && data.ok && data.progresso) {
        state.lastPersistedPage = Number.parseInt(String(data.progresso.ultima_pagina_lida || safePage), 10) || safePage;
      }
    } catch (error) {
      console.error(error);
    } finally {
      state.saveInFlight = false;
      if (state.pendingPersistPage !== null && state.pendingPersistPage !== state.lastPersistedPage) {
        const pending = state.pendingPersistPage;
        state.pendingPersistPage = null;
        persistProgress(pending);
      }
    }
  }

  function scheduleProgressSave() {
    if (state.saveTimer) clearTimeout(state.saveTimer);
    state.saveTimer = window.setTimeout(() => {
      persistProgress(state.pageNum);
    }, 2000);
  }

  function setSearchStatus(text) {
    if (searchStatusEl) searchStatusEl.textContent = text || "";
  }

  function clearSearchResults() {
    if (searchResultsEl) searchResultsEl.innerHTML = "";
  }

  function isSearchModalOpen() {
    return Boolean(searchModalEl && !searchModalEl.hasAttribute("hidden"));
  }

  function openSearchModal() {
    if (!searchModalEl) return;
    searchModalEl.removeAttribute("hidden");
    document.body.classList.add("acnh-modal-open");
    if (searchInput) searchInput.focus();
  }

  function closeSearchModal({ refocusTrigger = false } = {}) {
    if (!searchModalEl) return;
    searchModalEl.setAttribute("hidden", "");
    document.body.classList.remove("acnh-modal-open");
    if (refocusTrigger && openSearchBtn) openSearchBtn.focus();
  }

  function renderSearchResults(resultados) {
    if (!searchResultsEl) return;
    clearSearchResults();
    for (const item of resultados) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = `Pagina ${item.pagina}: ${item.trecho}`;
      btn.addEventListener("click", () => {
        closeSearchModal();
        gotoPage(item.pagina);
      });
      li.appendChild(btn);
      searchResultsEl.appendChild(li);
    }
  }

  async function performSearch() {
    if (!config.api_busca_url || !searchInput) return;
    const termo = String(searchInput.value || "").trim();
    if (!termo) {
      clearSearchResults();
      setSearchStatus("Informe um termo para buscar.");
      return;
    }

    state.searchInFlight = true;
    updateControls();
    setSearchStatus(`Buscando por "${termo}"...`);

    try {
      const params = new URLSearchParams({ q: termo });
      const resp = await fetch(`${config.api_busca_url}?${params.toString()}`, { credentials: "same-origin" });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        clearSearchResults();
        setSearchStatus(data.error || "Falha na busca.");
        return;
      }

      const resultados = Array.isArray(data.resultados) ? data.resultados : [];
      renderSearchResults(resultados);
      if (!resultados.length) {
        setSearchStatus(`Nenhum resultado para "${termo}".`);
      } else {
        setSearchStatus(`${resultados.length} resultado(s) para "${termo}". Clique para ir para a pagina.`);
      }
    } catch (error) {
      clearSearchResults();
      setSearchStatus("Erro ao buscar no documento.");
      console.error(error);
    } finally {
      state.searchInFlight = false;
      updateControls();
    }
  }

  function getFitScale(page) {
    const baseViewport = page.getViewport({ scale: 1 });
    const availableWidth = Math.max((viewerEl ? viewerEl.clientWidth : baseViewport.width) - 30, 100);
    return availableWidth / baseViewport.width;
  }

  async function renderPages(pageNum) {
    if (!state.pdfDoc) return;
    state.renderInProgress = true;
    updateLayoutMode();
    updateControls();
    setStatus(`Renderizando pagina ${pageNum}...`);

    try {
      const pageA = await state.pdfDoc.getPage(pageNum);
      const fitScale = getFitScale(pageA);
      const renderScale = fitScale * state.zoomFactor;

      ensureScaleCacheToken(renderScale);
      await ensurePageCached(pageNum, renderScale);

      drawCachedPage(pageNum, canvasPrimary);
      if (canvasSecondary) canvasSecondary.style.display = "none";

      trimCacheToWindow(pageNum);
      prefetchWindow(pageNum, renderScale);

      if (isSmartphoneLayout()) {
        setStatus(`Pagina ${pageNum} de ${state.totalPages}`);
      } else {
        setStatus(`Pagina ${pageNum} de ${state.totalPages} | Zoom ${Math.round(state.zoomFactor * 100)}%`);
      }
      scheduleProgressSave();
    } catch (error) {
      setStatus("Falha ao renderizar pagina.");
      console.error(error);
    } finally {
      state.renderInProgress = false;
      updateLayoutMode();
      updateControls();
      if (state.pendingPageNum !== null) {
        const pending = state.pendingPageNum;
        state.pendingPageNum = null;
        state.pageNum = pending;
        renderPages(pending);
      }
    }
  }

  function queueRender(pageNum) {
    const safePage = clampPage(pageNum);
    if (state.renderInProgress) {
      state.pendingPageNum = safePage;
      return;
    }
    state.pageNum = safePage;
    renderPages(safePage);
  }

  function gotoPage(rawValue) {
    if (!state.pdfDoc) return;
    const num = Number.parseInt(String(rawValue || ""), 10);
    if (!Number.isFinite(num)) {
      setStatus("Informe um numero de pagina valido.");
      pageInput.value = String(state.pageNum);
      return;
    }
    queueRender(num);
  }

  function goNextPage() {
    queueRender(state.pageNum + 1);
  }

  function goPrevPage() {
    queueRender(state.pageNum - 1);
  }

  function setZoom(nextZoom) {
    state.zoomFactor = Math.min(Math.max(nextZoom, 0.5), 3);
    queueRender(state.pageNum);
  }

  function resetZoom() {
    state.zoomFactor = 1;
    queueRender(state.pageNum);
  }

  function distance(t1, t2) {
    const dx = t1.clientX - t2.clientX;
    const dy = t1.clientY - t2.clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function setupTouchGestures() {
    if (!trackEl) return;

    trackEl.addEventListener(
      "touchstart",
      (event) => {
        if (event.touches.length === 2) {
          state.touch.pinchActive = true;
          state.touch.pinchStartDistance = distance(event.touches[0], event.touches[1]);
          state.touch.pinchStartZoom = state.zoomFactor;
          state.touch.pinchPendingZoom = state.zoomFactor;
          state.touch.swipeStartX = null;
          state.touch.swipeStartY = null;
          state.touch.swipeStartAt = null;
          return;
        }
        if (event.touches.length === 1 && !isZoomActive()) {
          state.touch.swipeStartX = event.touches[0].clientX;
          state.touch.swipeStartY = event.touches[0].clientY;
          state.touch.swipeStartAt = Date.now();
        }
      },
      { passive: true }
    );

    trackEl.addEventListener(
      "touchmove",
      (event) => {
        if (state.touch.pinchActive && event.touches.length === 2) {
          event.preventDefault();
          const currentDistance = distance(event.touches[0], event.touches[1]);
          const ratio = currentDistance / Math.max(state.touch.pinchStartDistance, 1);
          state.touch.pinchPendingZoom = Math.min(Math.max(state.touch.pinchStartZoom * ratio, 0.5), 3);
          zoomLabel.textContent = `${Math.round(state.touch.pinchPendingZoom * 100)}%`;
        }
      },
      { passive: false }
    );

    trackEl.addEventListener(
      "touchend",
      (event) => {
        if (state.touch.pinchActive && event.touches.length < 2) {
          state.touch.pinchActive = false;
          if (Math.abs(state.touch.pinchPendingZoom - state.zoomFactor) >= 0.02) {
            setZoom(state.touch.pinchPendingZoom);
          } else {
            updateControls();
          }
          return;
        }

        if (isZoomActive()) {
          state.touch.swipeStartX = null;
          state.touch.swipeStartY = null;
          state.touch.swipeStartAt = null;
          return;
        }

        if (state.touch.swipeStartX === null || state.touch.swipeStartY === null || state.touch.swipeStartAt === null) {
          return;
        }

        const touch = event.changedTouches && event.changedTouches[0];
        if (!touch) return;
        const dx = touch.clientX - state.touch.swipeStartX;
        const dy = touch.clientY - state.touch.swipeStartY;
        const dt = Date.now() - state.touch.swipeStartAt;

        state.touch.swipeStartX = null;
        state.touch.swipeStartY = null;
        state.touch.swipeStartAt = null;

        if (dt > 500) return;
        if (Math.abs(dx) < 70) return;
        if (Math.abs(dy) > 60) return;

        if (dx < 0) goNextPage();
        else goPrevPage();
      },
      { passive: true }
    );
  }

  function setupKeyboardControls() {
    document.addEventListener("keydown", (event) => {
      const target = event.target;
      const tag = target && target.tagName ? target.tagName.toLowerCase() : "";
      if (
        tag === "input"
        || tag === "textarea"
        || tag === "select"
        || tag === "button"
        || (target && target.isContentEditable)
      ) {
        return;
      }
      if (!state.pdfDoc) return;

      if (event.key === "ArrowRight" || event.key === "PageDown") {
        event.preventDefault();
        goNextPage();
        return;
      }
      if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault();
        goPrevPage();
        return;
      }
      if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        setZoom(state.zoomFactor + 0.1);
        return;
      }
      if (event.key === "-" || event.key === "_") {
        event.preventDefault();
        setZoom(state.zoomFactor - 0.1);
        return;
      }
      if (event.key === "0") {
        event.preventDefault();
        resetZoom();
      }
    });
  }

  async function loadDocument() {
    if (!window.pdfjsLib) {
      setStatus("PDF.js nao foi carregado.");
      return;
    }
    window.pdfjsLib.GlobalWorkerOptions.workerSrc =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

    setStatus("Buscando metadados do documento...");
    const metaResp = await fetch(config.api_documento_ativo_url, { credentials: "same-origin" });
    const metaData = await metaResp.json();
    if (!metaResp.ok || !metaData.ok || !metaData.documento) {
      setStatus(metaData.error || "Nao foi possivel carregar o documento ativo.");
      return;
    }

    titleEl.textContent = `${metaData.documento.titulo} (${metaData.documento.total_paginas} paginas)`;
    const pdfUrl = metaData.documento.pdf_url || config.api_documento_ativo_pdf_url;
    if (!pdfUrl) {
      setStatus("URL do PDF ativo nao encontrada.");
      return;
    }

    setStatus("Abrindo PDF...");
    const task = window.pdfjsLib.getDocument({
      url: pdfUrl,
      withCredentials: true,
      disableRange: false,
      disableStream: false,
      disableAutoFetch: false,
      rangeChunkSize: 64 * 1024,
    });
    state.pdfDoc = await task.promise;
    state.totalPages = state.pdfDoc.numPages || 0;
    clearRenderCache();
    const progressPage = await fetchProgressStartPage();
    state.pageNum = clampPage(progressPage);
    updateLayoutMode();
    updateControls();
    renderPages(state.pageNum);
  }

  prevBtn.addEventListener("click", () => {
    if (state.pageNum <= 1) return;
    goPrevPage();
  });

  nextBtn.addEventListener("click", () => {
    if (state.pageNum >= state.totalPages) return;
    goNextPage();
  });

  goBtn.addEventListener("click", () => gotoPage(pageInput.value));
  pageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") gotoPage(pageInput.value);
  });

  zoomInBtn.addEventListener("click", () => setZoom(state.zoomFactor + 0.1));
  zoomOutBtn.addEventListener("click", () => setZoom(state.zoomFactor - 0.1));

  if (openSearchBtn) {
    openSearchBtn.addEventListener("click", () => openSearchModal());
  }
  if (closeSearchBtn) {
    closeSearchBtn.addEventListener("click", () => closeSearchModal({ refocusTrigger: true }));
  }
  if (searchModalBackdropEl) {
    searchModalBackdropEl.addEventListener("click", () => closeSearchModal({ refocusTrigger: true }));
  }
  if (searchBtn) searchBtn.addEventListener("click", () => performSearch());
  if (searchInput) {
    searchInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        performSearch();
      }
    });
  }
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && isSearchModalOpen()) {
      event.preventDefault();
      closeSearchModal({ refocusTrigger: true });
    }
  });

  window.addEventListener("resize", () => {
    if (!state.pdfDoc) return;
    queueRender(state.pageNum);
  });

  window.addEventListener("beforeunload", () => {
    clearRenderCache();
  });

  setupTouchGestures();
  setupKeyboardControls();
  updateLayoutMode();
  updateControls();
  loadDocument().catch((error) => {
    setStatus("Erro inesperado ao abrir o documento.");
    console.error(error);
  });
})();


