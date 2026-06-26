/* motion.js — Givan Research Design System
   Additive entrance motion. No deps. Safe to load on every page.
   See MOTION-HANDOFF.md for the full spec. */
(function () {
  var REDUCE = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function snap(el) { el.classList.add('is-instant', 'is-in'); }

  /* ── Core reveal system (§1b) ─────────────────────────────── */
  function initReveals() {
    var nodes = [].slice.call(document.querySelectorAll('.reveal:not(.is-in)'));
    if (!nodes.length) return;

    if (REDUCE || typeof IntersectionObserver === 'undefined') {
      nodes.forEach(snap);
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add('is-in');
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -7% 0px' });

    nodes.forEach(function (el) {
      io.observe(el);
      // Safety net: if the observer never fires (frozen compositor /
      // headless capture), snap visible after 1.1s so nothing stays hidden.
      setTimeout(function () {
        if (!el.classList.contains('is-in')) snap(el);
      }, 1100);
    });
  }

  /* ── onReveal helper for data-viz (§5) ───────────────────── */
  function onReveal(el, fn) {
    if (REDUCE || typeof IntersectionObserver === 'undefined') { fn(true); return; }
    var done = false;
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (e.isIntersecting && !done) {
          done = true;
          fn(false);
          io.disconnect();
        }
      });
    }, { threshold: 0.3 });
    io.observe(el);
    setTimeout(function () {
      if (!done) { done = true; fn(true); io.disconnect(); }
    }, 1100);
  }

  /* ── Scroll-progress hairline (§4b) ──────────────────────── */
  function initScrollProgress() {
    var nav = document.querySelector('nav');
    if (!nav) return;
    var bar = document.createElement('div');
    bar.className = 'nav__progress';
    nav.appendChild(bar);
    var raf = 0;
    function onScroll() {
      if (raf) return;
      raf = requestAnimationFrame(function () {
        var h = document.documentElement;
        var max = h.scrollHeight - h.clientHeight;
        bar.style.width = (max > 0 ? Math.min(1, h.scrollTop / max) * 100 : 0) + '%';
        raf = 0;
      });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ── Init ─────────────────────────────────────────────────── */
  function init() {
    initReveals();
    initScrollProgress();
  }

  if (document.readyState !== 'loading') init();
  else document.addEventListener('DOMContentLoaded', init);

  /* Expose for JS-injected content (call after appending new rows) */
  window.initReveals = initReveals;
  window.onReveal    = onReveal;
})();
