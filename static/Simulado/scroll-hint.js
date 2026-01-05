(function () {
  const SENTINEL_SELECTOR = ".scroll-hint__sentinel";
  const THRESHOLD = 6;

  function createButton() {
    if (document.querySelector(".scroll-hint")) return document.querySelector(".scroll-hint");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "scroll-hint";
    btn.setAttribute("aria-label", "Ver mais conteúdo");
    btn.innerHTML = `
      <svg class="scroll-hint__icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M12 16.5c-.3 0-.5-.1-.7-.3l-7-7a1 1 0 1 1 1.4-1.4L12 14.1l6.3-6.3a1 1 0 0 1 1.4 1.4l-7 7c-.2.2-.4.3-.7.3Z"/>
      </svg>
    `;
    document.body.appendChild(btn);
    return btn;
  }

  function getSentinel() {
    let sentinel = document.querySelector(SENTINEL_SELECTOR);
    if (!sentinel) {
      sentinel = document.createElement("div");
      sentinel.className = "scroll-hint__sentinel";
      sentinel.setAttribute("aria-hidden", "true");
      document.body.appendChild(sentinel);
    }
    return sentinel;
  }

  function hasOverflow() {
    const doc = document.documentElement;
    return doc.scrollHeight > doc.clientHeight + THRESHOLD;
  }

  function initScrollHint() {
    if (!hasOverflow()) return;

    const sentinel = getSentinel();
    const btn = createButton();

    function show() {
      btn.classList.add("is-visible");
    }

    function hide() {
      btn.classList.remove("is-visible");
    }

    btn.addEventListener("click", () => {
      sentinel.scrollIntoView({ behavior: "smooth", block: "end" });
    });

    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver(
        (entries) => {
          const entry = entries[0];
          if (!entry) return;
          if (entry.isIntersecting) {
            hide();
          } else {
            show();
          }
        },
        { root: null, threshold: 0.05 }
      );
      io.observe(sentinel);
    } else {
      const handler = () => {
        const doc = document.documentElement;
        const atBottom = window.scrollY + window.innerHeight >= doc.scrollHeight - THRESHOLD;
        if (atBottom) hide();
        else show();
      };
      window.addEventListener("scroll", handler, { passive: true });
      window.addEventListener("resize", handler);
      handler();
    }
  }

  if (document.readyState === "complete" || document.readyState === "interactive") {
    initScrollHint();
  } else {
    document.addEventListener("DOMContentLoaded", initScrollHint);
  }
})();
