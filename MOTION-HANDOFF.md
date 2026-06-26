# Motion & Polish — Handoff for the live site (`givanchris/News`)

**Goal:** port the motion layer prototyped in `ui_kits/portfolio-site/` (React) into the
real, vanilla-JS multipage site (`givanchris/News`) without changing any functionality,
markup structure, content, or data wiring. This is **additive**: new CSS + one small JS
module. No framework, no build step.

> **Reference spec:** `ui_kits/portfolio-site/` in the Givan Research Design System project.
> `shared.jsx` (Reveal/useInView), `chrome.jsx` (Nav), and the four `*Screen.jsx` files
> show the intended behavior. This doc translates those into plain JS/CSS.

The live site is **multipage** (`index`, `brief.html`, `options.html`, `fed-signal.html`,
`portfolio-lab.html`), not a SPA — so the React "view transition" becomes a **page-load
entrance**, and the React "nav active state" is just a per-page CSS class.

---

## 0. Non-negotiable principles (learned the hard way)

1. **Never leave content at `opacity:0` waiting on an animation.** If the compositor is
   frozen (background tab, print, PDF/screenshot capture) or the observer never fires,
   content must still be visible. Every reveal has a **timed fallback that snaps content
   visible with NO transition**.
2. **Respect `prefers-reduced-motion: reduce`** — skip all entrance motion, show final state.
3. **State indicators (nav active link) must NOT depend on a transition to reach their
   target** — they snap, so they're always correct in a static capture.
4. **4px rhythm, existing tokens, eased-out, 120–320ms.** No bounce, no flashy effects.
   Reuse the site's existing CSS custom properties (`--accent`, durations, easings). If the
   live `site.css` doesn't define easing tokens, add:
   `--ease-out: cubic-bezier(0.16,1,0.3,1);`

---

## 1. Core reveal system

### 1a. CSS — add to `Assets/site.css`

```css
/* ---- Scroll-reveal primitives ---------------------------------- */
.reveal {
  opacity: 0;
  transform: translateY(18px);
  transition: opacity 0.66s var(--ease-out), transform 0.66s var(--ease-out);
  will-change: opacity, transform;
}
.reveal.is-in {            /* added by JS when the element scrolls into view */
  opacity: 1;
  transform: none;
}
.reveal.is-instant {       /* fallback / reduced-motion: snap, no animation */
  transition: none;
}

/* Stagger: children of a [data-stagger] container get an increasing delay.
   Covers up to ~12 siblings; extend if a grid is larger. */
[data-stagger] > .reveal { transition-delay: 0ms; }
[data-stagger] > .reveal:nth-child(1)  { transition-delay: 0ms;   }
[data-stagger] > .reveal:nth-child(2)  { transition-delay: 70ms;  }
[data-stagger] > .reveal:nth-child(3)  { transition-delay: 140ms; }
[data-stagger] > .reveal:nth-child(4)  { transition-delay: 210ms; }
[data-stagger] > .reveal:nth-child(5)  { transition-delay: 280ms; }
[data-stagger] > .reveal:nth-child(6)  { transition-delay: 350ms; }
[data-stagger] > .reveal:nth-child(n+7){ transition-delay: 420ms; }
.reveal.is-instant { transition-delay: 0ms !important; }

@media (prefers-reduced-motion: reduce) {
  .reveal { opacity: 1; transform: none; transition: none; }
}
```

### 1b. JS — new file `Assets/motion.js`, loaded after `site.js`

```js
/* motion.js — additive entrance motion. No deps. Safe to load on every page. */
(function () {
  var REDUCE = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function snap(el) { el.classList.add('is-instant', 'is-in'); }

  function initReveals() {
    var nodes = [].slice.call(document.querySelectorAll('.reveal'));
    if (!nodes.length) return;

    if (REDUCE || typeof IntersectionObserver === 'undefined') {
      nodes.forEach(snap);
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add('is-in');     // animate
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -7% 0px' });

    nodes.forEach(function (el) {
      io.observe(el);
      // Safety net: if the observer never fires (frozen compositor /
      // headless capture / never scrolled), reveal INSTANTLY after 1.1s
      // so content is never stuck hidden. is-instant also kills the
      // transition (which would otherwise freeze mid-interpolation).
      setTimeout(function () {
        if (!el.classList.contains('is-in')) snap(el);
      }, 1100);
    });
  }

  if (document.readyState !== 'loading') initReveals();
  else document.addEventListener('DOMContentLoaded', initReveals);
})();
```

### 1c. How to apply

In each page's HTML, add `class="reveal"` to the blocks you want to animate in, and
`data-stagger` to a container whose direct children should cascade.

- **Add `reveal`** to: section headers, the deep-dive block, the about text block,
  each project card, each market tile, each story, each watchlist item, each table row,
  each valuation/metric row, stat groups, the chart panel, the gauge panel.
- **Add `data-stagger`** to the *parent* of any repeated set so the children cascade:
  the projects grid, the market-snapshot grid, the story feed, the watchlist, the ticker
  table body, the valuation list, the sector-heatmap grid, the about-facts row.

> If your existing markup already has a class on these (it does — e.g. `.market-tile`,
> `.project-card`), just **add** `reveal`, don't replace. Server-rendered/JS-rendered
> rows (the ones `site.js` injects from JSON): add `reveal` to each row **at the moment
> you create it**, then call `initReveals()` once after the list is built (see §6).

---

## 2. Hero load-in (above the fold)

The hero shouldn't wait for scroll. Animate **transform only** (never opacity) so a frozen
compositor leaves it visible, just un-shifted.

```css
@keyframes cg-rise { from { transform: translateY(18px); } to { transform: none; } }
.cg-load { animation: cg-rise 0.6s var(--ease-out) both; }
.cg-load--2 { animation-delay: 0.09s; }
.cg-load--3 { animation-delay: 0.18s; }
@media (prefers-reduced-motion: reduce) { .cg-load { animation: none; } }
```

Add `cg-load` (and `cg-load--2` / `--3` for the staggered lines) to the hero eyebrow,
the big `<h1>`, and the intro row on each page's hero.

> **Why transform-only, not opacity:** a `from{opacity:0}` keyframe leaves the hero
> invisible if the animation engine is paused. Transform-only degrades to "visible, not
> shifted" instead of "blank".

---

## 3. Page-load entrance (replaces the SPA "view transition")

Because the live site navigates between real pages, give the main content a one-shot
transform fade on load:

```css
@keyframes cg-page-in { from { transform: translateY(10px); } to { transform: none; } }
main, .page-main { animation: cg-page-in 0.5s var(--ease-out) both; }
@media (prefers-reduced-motion: reduce) { main, .page-main { animation: none; } }
```

(Use whatever the page's top-level content wrapper is.)

---

## 4. Nav — active link + scroll progress

### 4a. Active link (CRITICAL: snap, do not transition)

The live site already marks the current page's nav link (commonly an `.active`/
`aria-current` class set server-side or by `site.js`). Style it as an **instant** accent +
underline. **Do not put a `transition` on the active color/underline** — a transition
freezes mid-interpolation in static captures and makes the wrong link look active.

```css
.nav a { position: relative; color: var(--text-muted); transition: none; }
.nav a::after {                       /* underline */
  content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 1.5px;
  background: currentColor; transform: scaleX(0); transform-origin: left;
  transition: none;                   /* snap — never lag the active state */
}
.nav a:hover { color: var(--text-primary); }
.nav a:hover::after { transform: scaleX(1); }
.nav a.active { color: var(--accent); }
.nav a.active::after { transform: scaleX(1); background: var(--accent); }
```

> Hover uses pure CSS `:hover` (no JS hover state), which sidesteps the React bug we hit
> where a click re-render left a stale "hovered" link lit. Active is driven solely by the
> `.active` class the page already sets — guaranteed correct per page.

### 4b. Scroll-progress hairline (nice-to-have)

```css
.nav { position: relative; }
.nav__progress {
  position: absolute; left: 0; bottom: -1px; height: 2px; width: 0;
  background: var(--accent); transition: width 90ms linear; pointer-events: none;
}
```
```js
/* append inside motion.js */
(function () {
  var nav = document.querySelector('.nav'); if (!nav) return;
  var bar = document.createElement('div');
  bar.className = 'nav__progress'; nav.appendChild(bar);
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
})();
```

---

## 5. Data-viz animations (brief / options / portfolio-lab)

Same rule: drive from an in-view trigger, but **snap to final on the fallback** so a frozen
capture shows the finished chart, not a blank one.

- **Monte Carlo fan chart (SVG line):** draw-on with `stroke-dasharray`/`stroke-dashoffset`.
  Set `dashoffset = pathLength` initially, transition to `0` when revealed; bands fade
  `opacity 0→target`. On the 1.1s fallback, set `transition:none` then the final values.
- **Composite valuation gauge marker:** animate `left: 0% → pct%` (`transition: left .9s`).
- **VIX term bars / any bar:** animate `width: 0 → target%`.

Generic helper to reuse the reveal observer for "animate once in view":

```js
/* in motion.js — call onReveal(el, fn): fn(instant) runs once when el is in view,
   or instantly via the same 1.1s fallback. */
function onReveal(el, fn) {
  if (REDUCE || typeof IntersectionObserver === 'undefined') { fn(true); return; }
  var done = false;
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting && !done) { done = true; fn(false); io.disconnect(); } });
  }, { threshold: 0.3 });
  io.observe(el);
  setTimeout(function () { if (!done) { done = true; fn(true); io.disconnect(); } }, 1100);
}
// expose if charts live in site.js:  window.onReveal = onReveal;
```

Example (fan chart, after `site.js` has rendered the SVG path `#median`):
```js
var path = document.querySelector('#fanchart #median');
if (path) {
  var L = path.getTotalLength();
  path.style.strokeDasharray = L;
  path.style.strokeDashoffset = L;
  window.onReveal(path, function (instant) {
    path.style.transition = instant ? 'none' : 'stroke-dashoffset 1.1s var(--ease-out)';
    path.style.strokeDashoffset = 0;
  });
}
```

---

## 6. Hover micro-interactions (pure CSS — preferred)

Do these in CSS so they never interact with JS state. Reuse the site's existing shadow/
border tokens.

```css
/* project / research cards */
.project-card { transition: transform .18s var(--ease-out), box-shadow .18s var(--ease-out), border-color .18s; }
.project-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-lg); border-color: var(--accent); }
.project-card:hover .card-arrow { transform: translateX(5px); }   /* footer "→" */
.card-arrow { transition: transform .18s var(--ease-out); }

/* options ticker rows */
.ticker-row { transition: background .18s, box-shadow .18s; }
.ticker-row:hover { background: var(--surface-sunken); box-shadow: inset 2px 0 0 var(--accent); }

/* sector heatmap cells */
.heat-cell { transition: transform .18s var(--ease-out), filter .18s, box-shadow .18s; }
.heat-cell:hover { transform: translateY(-1px); filter: brightness(1.06); box-shadow: var(--shadow-sm); position: relative; z-index: 1; }

/* brief story (expandable): tie color to the [aria-expanded]/.is-open state site.js sets */
.brief-story { cursor: pointer; }
.brief-story:hover .brief-story__headline { color: var(--accent); }
.brief-story__plus { display: inline-block; transition: transform .18s var(--ease-out); }
.brief-story.is-open .brief-story__plus { transform: rotate(45deg); }
.brief-story:hover .brief-story__plus { transform: rotate(90deg); }
```

> The expand/collapse accordion the site already has stays exactly as-is — only the
> hover/`+`-rotation polish is added.

### For JS-injected rows
`site.js` builds market tiles, ticker rows, story cards, valuation rows, and the heatmap
from JSON. Two-line change per list:
1. add `'reveal'` to the className of each element you create (and `data-stagger` on its
   container, once, in the HTML);
2. after the list is appended, call `window.initReveals()` once (expose `initReveals`
   from `motion.js` via `window.initReveals = initReveals;`).

---

## 7. Load order (per page)

```html
<link rel="stylesheet" href="Assets/site.css">
...
<script src="Assets/site.js"></script>
<script src="Assets/motion.js"></script>   <!-- after site.js so it sees rendered DOM -->
```
If `site.js` renders lists asynchronously (fetch → render), call `window.initReveals()`
in that render callback instead of relying solely on `DOMContentLoaded`.

---

## 8. Acceptance checklist

- [ ] No element is ever stuck invisible — disable JS, or throttle/background the tab, and
      all content still shows.
- [ ] `prefers-reduced-motion: reduce` → everything visible, no entrance motion.
- [ ] Nav: the current page's link is accent + underlined **immediately** on load and in a
      screenshot/PDF (no transition lag, never the wrong link).
- [ ] Cards/rows/tiles cascade in on scroll; each reveals once and stays.
- [ ] Fan chart draws its median line; gauge marker + bars animate; a print/PDF shows the
      finished chart, not a blank one.
- [ ] Hover: cards lift + arrow slides, ticker rows highlight, heatmap cells brighten —
      all CSS-only, no JS hover state.
- [ ] Timings 120–320ms (reveals up to ~0.66s), eased-out, no bounce. Functionality, IA,
      content, and JSON wiring unchanged.
