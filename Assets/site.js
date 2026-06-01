/* ==========================================================
   site.js — shared helpers for all pages
   Pure functions, no globals beyond window.CG namespace.
   ========================================================== */

window.CG = window.CG || {};

(function (CG) {
  'use strict';

  var DAYS   = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  var MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];

  /**
   * Fetch JSON with cache-busting query param. Resolves to parsed JSON
   * or rejects if HTTP status is not 2xx.
   */
  CG.fetchJSON = function (url) {
    var sep = url.indexOf('?') === -1 ? '?' : '&';
    return fetch(url + sep + '_=' + Date.now())
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status + ' from ' + url);
        return r.json();
      });
  };

  /**
   * Try a primary JSON file, fall back to a secondary if primary 404s.
   * Useful during data-file migrations.
   */
  CG.fetchJSONWithFallback = function (primary, fallback) {
    return CG.fetchJSON(primary).catch(function () {
      return CG.fetchJSON(fallback);
    });
  };

  /** Long date: "Thursday, April 16, 2026" */
  CG.fmtDate = function (d) {
    if (!(d instanceof Date)) d = new Date(d);
    return DAYS[d.getDay()] + ', ' + MONTHS[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear();
  };

  /** Compact date: "Apr 16, 2026" */
  CG.fmtDateShort = function (d) {
    if (!(d instanceof Date)) d = new Date(d);
    return MONTHS[d.getMonth()].slice(0,3) + ' ' + d.getDate() + ', ' + d.getFullYear();
  };

  /** "Updated Apr 16, 7:00 PM MDT" */
  CG.fmtUpdated = function (d) {
    if (!(d instanceof Date)) d = new Date(d);
    return 'Updated ' + d.toLocaleString('en-US', {
      month: 'short', day: 'numeric',
      hour: 'numeric', minute: '2-digit', timeZoneName: 'short'
    });
  };

  /** Hours since a timestamp (number or Date). */
  CG.hoursSince = function (t) {
    var then = t instanceof Date ? t.getTime() : new Date(t).getTime();
    return (Date.now() - then) / 3600000;
  };

  /**
   * Render a simple SVG sparkline. Returns an SVG string.
   * values: [Number]. width/height/stroke optional.
   */
  CG.sparkline = function (values, opts) {
    opts = opts || {};
    var w = opts.width  || 120;
    var h = opts.height || 30;
    var stroke = opts.stroke || 'var(--blue2)';
    if (!values || values.length < 2) return '';
    var min = Math.min.apply(null, values);
    var max = Math.max.apply(null, values);
    var range = max - min || 1;
    var step  = w / (values.length - 1);
    var pts = values.map(function (v, i) {
      var x = (i * step).toFixed(2);
      var y = (h - ((v - min) / range) * h).toFixed(2);
      return x + ',' + y;
    }).join(' ');
    return '<svg viewBox="0 0 ' + w + ' ' + h + '" width="' + w + '" height="' + h + '" '
      + 'preserveAspectRatio="none" style="display:block;">'
      + '<polyline fill="none" stroke="' + stroke + '" stroke-width="1.5" '
      + 'stroke-linecap="round" stroke-linejoin="round" points="' + pts + '"/>'
      + '</svg>';
  };

  /**
   * Classify a metric against its historical mean/stdev.
   * Returns one of: 'cheap', 'fair', 'rich', 'expensive'.
   * Lower z = cheaper for valuation metrics (P/E, P/GDP).
   * For yield-like metrics where higher = cheaper, pass invert: true.
   */
  CG.classifyZ = function (value, mean, stdev, opts) {
    opts = opts || {};
    if (stdev === 0 || stdev == null) return 'fair';
    var z = (value - mean) / stdev;
    if (opts.invert) z = -z;
    if (z < -1) return 'cheap';
    if (z <  0) return 'fair';
    if (z <= 1) return 'rich';
    return 'expensive';
  };

  /** Escape HTML to prevent injection when rendering user-editable JSON. */
  CG.esc = function (s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  };

})(window.CG);
