(function () {
  var toggleButtons = document.querySelectorAll("[data-toggle-password]");
  if (!toggleButtons.length) {
    return;
  }

  function setButtonState(button, visible) {
    button.classList.toggle("is-visible", visible);
    button.setAttribute("aria-pressed", visible ? "true" : "false");
    button.setAttribute("aria-label", visible ? "Ocultar senha" : "Mostrar senha");
  }

  toggleButtons.forEach(function (button) {
    var targetId = button.getAttribute("data-target");
    if (!targetId) {
      return;
    }

    var input = document.getElementById(targetId);
    if (!input) {
      return;
    }

    setButtonState(button, input.type === "text");

    button.addEventListener("click", function () {
      var visible = input.type === "text";
      input.type = visible ? "password" : "text";
      setButtonState(button, !visible);
      input.focus({ preventScroll: true });
    });
  });
})();
