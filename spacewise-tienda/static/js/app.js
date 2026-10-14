// Mostrar/ocultar el menú lateral del panel
document.getElementById("toggle-nav")?.addEventListener("click", () => {
  document.querySelector(".app")?.classList.toggle("nav-collapsed");
});
