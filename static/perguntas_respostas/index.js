(function () {
  const courseSelect = document.getElementById("curso_id");
  const moduleSelect = document.getElementById("modulo_id");
  if (!courseSelect || !moduleSelect) return;

  const options = Array.from(moduleSelect.options);

  function filterModules() {
    const courseId = courseSelect.value;
    options.forEach((opt) => {
      if (!opt.value) {
        opt.hidden = false;
        return;
      }
      const belongsTo = opt.getAttribute("data-curso-id");
      opt.hidden = Boolean(courseId && belongsTo !== courseId);
    });

    const selected = moduleSelect.selectedOptions[0];
    if (selected && selected.hidden) {
      moduleSelect.value = "";
    }
  }

  courseSelect.addEventListener("change", filterModules);
  filterModules();
})();
