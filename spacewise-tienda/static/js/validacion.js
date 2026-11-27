// Filtra lo que se puede escribir según data-filtro (el servidor vuelve a validar todo).
//   entero:   solo dígitos, sin negativos, decimales ni la "e" de notación científica
//   letras:   letras (con tildes y ñ), espacios, apóstrofo, guion y punto
//   telefono: dígitos y espacios, con + solo al inicio
//   rut:      dígitos, puntos, guion y K
(function () {
  const PERMITIDOS = {
    letras: /[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ '\-.]/g,
    telefono: /[^0-9 +]/g,
    rut: /[^0-9kK.\-]/g,
  };

  document.addEventListener("keydown", (ev) => {
    if (ev.target.dataset?.filtro === "entero" && ["e", "E", "+", "-", ".", ","].includes(ev.key)) {
      ev.preventDefault();
    }
  });

  document.addEventListener("input", (ev) => {
    const campo = ev.target;
    const filtro = campo.dataset?.filtro;
    if (!filtro) return;
    if (filtro === "entero") {
      // Al pegar "-3" o "2.5" se deja vacío o se trunca al entero positivo
      const n = Number(campo.value);
      if (campo.value !== "" && (Number.isNaN(n) || n < 0)) campo.value = "";
      else if (campo.value.includes(".") || /^0\d/.test(campo.value)) campo.value = Math.floor(n);
      return;
    }
    let valor = campo.value.replace(PERMITIDOS[filtro], "");
    if (filtro === "telefono") valor = valor.replace(/(?!^)\+/g, "");
    if (filtro === "rut") valor = valor.toUpperCase();
    if (valor !== campo.value) campo.value = valor;
  });

  // Prevención de doble envío en formularios (anti-double-submit)
  document.addEventListener("submit", (ev) => {
    const form = ev.target;
    if (ev.defaultPrevented) return;
    if (form.dataset.submitting === "true") {
      ev.preventDefault();
      return;
    }
    form.dataset.submitting = "true";

    const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
    if (submitBtn) {
      submitBtn.dataset.originalContent = submitBtn.tagName === "BUTTON" ? submitBtn.innerHTML : submitBtn.value;
      submitBtn.disabled = true;
      if (submitBtn.tagName === "BUTTON") {
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Procesando...';
      } else {
        submitBtn.value = "Procesando...";
      }
    }

    // Temporizador de seguridad: si la validación HTML5 o backend canceló o tardó, re-habilitar a los 10 segundos
    setTimeout(() => {
      form.dataset.submitting = "false";
      if (submitBtn) {
        submitBtn.disabled = false;
        if (submitBtn.tagName === "BUTTON") {
          submitBtn.innerHTML = submitBtn.dataset.originalContent || "Enviar";
        } else {
          submitBtn.value = submitBtn.dataset.originalContent || "Enviar";
        }
      }
    }, 10000);
  });
})();
