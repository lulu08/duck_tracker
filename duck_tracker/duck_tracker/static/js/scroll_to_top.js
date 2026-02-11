/**
 * Scroll to Top Button Functionality
 */

document.addEventListener("DOMContentLoaded", function () {
  const upBtn = document.getElementById("scroll-to-top");
  if (!upBtn) return;

  // Initially hidden
  upBtn.style.display = "none";

  window.addEventListener("scroll", () => {
    if (window.scrollY > 300) {
      upBtn.style.display = "inline-flex";
    } else {
      upBtn.style.display = "none";
    }
  });

  // Smooth scroll to top
  upBtn.addEventListener("click", () => {
    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });
  });
});