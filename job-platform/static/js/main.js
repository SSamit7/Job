document.addEventListener("DOMContentLoaded", () => {
  // Mobile sidebar drawer: hamburger opens it as an overlay, backdrop/link click closes it.
  const sidebar = document.querySelector(".sidebar");
  const hamburger = document.getElementById("hamburger-btn");
  const backdrop = document.getElementById("sidebar-backdrop");

  function openDrawer() {
    if (!sidebar) return;
    sidebar.classList.add("open");
    if (backdrop) backdrop.classList.add("visible");
    document.body.style.overflow = "hidden";
  }

  function closeDrawer() {
    if (!sidebar) return;
    sidebar.classList.remove("open");
    if (backdrop) backdrop.classList.remove("visible");
    document.body.style.overflow = "";
  }

  if (hamburger) hamburger.addEventListener("click", openDrawer);
  if (backdrop) backdrop.addEventListener("click", closeDrawer);

  // Tapping any nav link inside the drawer should close it too, since it's about to navigate away.
  if (sidebar) {
    sidebar.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeDrawer));
  }
});
