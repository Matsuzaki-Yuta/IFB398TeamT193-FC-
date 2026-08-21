/* --------------------------------------------------------------------------
   SCROLL REVEALS
   Elements with the .reveal class move into place when they enter the screen.
   -------------------------------------------------------------------------- */
(function () {
  "use strict";

  var items = document.querySelectorAll(".reveal");
  if (!items.length) return;

  function show(item) {
    item.classList.add("in");
  }

  if (!("IntersectionObserver" in window)) {
    items.forEach(show);
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      show(entry.target);
      observer.unobserve(entry.target);
    });
  }, {
    rootMargin: "0px 0px -12% 0px",
    threshold: 0.12
  });

  items.forEach(function (item) {
    observer.observe(item);
  });
})();
