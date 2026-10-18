// Botones [data-agregar="<prefijo>"]: agregan una fila al formset copiando el
// <template id="<prefijo>-vacio"> y reemplazando __prefix__ por el siguiente índice.
document.querySelectorAll("[data-agregar]").forEach((boton) => {
  boton.addEventListener("click", () => {
    const prefijo = boton.dataset.agregar;
    const total = document.getElementById(`id_${prefijo}-TOTAL_FORMS`);
    const html = document.getElementById(`${prefijo}-vacio`).innerHTML.replace(/__prefix__/g, total.value);
    document.getElementById(`${prefijo}-filas`).insertAdjacentHTML("beforeend", html);
    total.value = Number(total.value) + 1;
  });
});
