(function () {
  const btnOpen = document.getElementById("btn-meu-plano");
  const modal = document.getElementById("modal-meu-plano");
  if (!btnOpen || !modal) return;

  const panel = modal.querySelector(".inicio-modal__panel");
  const closeTargets = modal.querySelectorAll("[data-modal-close]");
  let lastFocus = null;

  function openModal() {
    lastFocus = document.activeElement;
    if (typeof modal.showModal === "function") {
      modal.showModal();
    } else {
      modal.setAttribute("open", "");
    }
    document.body.classList.add("inicio-modal-open");
    if (panel && typeof panel.focus === "function") panel.focus();
  }

  function closeModal() {
    if (typeof modal.close === "function") {
      modal.close();
    } else {
      modal.removeAttribute("open");
    }
    document.body.classList.remove("inicio-modal-open");
    if (lastFocus && typeof lastFocus.focus === "function") {
      lastFocus.focus();
    }
  }

  btnOpen.addEventListener("click", openModal);

  closeTargets.forEach((el) => {
    el.addEventListener("click", closeModal);
  });

  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });

  modal.addEventListener("close", () => {
    document.body.classList.remove("inicio-modal-open");
  });

  modal.addEventListener("cancel", () => {
    document.body.classList.remove("inicio-modal-open");
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal.hasAttribute("open")) {
      event.preventDefault();
      closeModal();
    }
  });
})();
