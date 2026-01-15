(() => {
  const MAX_WIDTH = 640;
  const SELECTOR =
    "[vw], [vw-access-button], [vw-plugin-wrapper], .vw-access-button, .vw-plugin-wrapper, .vw-plugin-top-wrapper";

  function toggleVlibras() {
    const width = window.innerWidth || document.documentElement.clientWidth;
    const hide = width <= MAX_WIDTH;
    document.querySelectorAll(SELECTOR).forEach((el) => {
      if (hide) {
        el.style.setProperty("display", "none", "important");
      } else {
        el.style.removeProperty("display");
      }
    });
  }

  toggleVlibras();
  window.addEventListener("resize", toggleVlibras);
  window.addEventListener("orientationchange", toggleVlibras);
  setTimeout(toggleVlibras, 500);
})();
