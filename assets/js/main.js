/* Geng Xiang — Portfolio interactions
   Reveal on scroll · nav state · back to top · year */
(function () {
  'use strict';

  /* Navigation state on scroll */
  var nav = document.querySelector('.nav');
  var toTop = document.querySelector('.to-top');
  function onScroll() {
    if (nav) nav.classList.toggle('nav--scrolled', window.scrollY > 40);
    if (toTop) toTop.classList.toggle('is-shown', window.scrollY > 600);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* Reveal on scroll */
  var reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add('is-visible'); });
  }

  /* Back to top */
  if (toTop) {
    toTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* Footer year */
  var year = document.querySelector('[data-year]');
  if (year) year.textContent = new Date().getFullYear();
})();
