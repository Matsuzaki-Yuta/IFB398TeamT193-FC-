/* ============================================================================
   LIQUID GLASS  (liquid-glass.js)
   ----------------------------------------------------------------------------
   Frosted centre + chromatic rim for any element, via a generated SVG
   backdrop-filter. No dependencies.

     LiquidGlass.apply(document.querySelector(".topbar"));
     LiquidGlass.apply(el, { bend: 30, dispersion: 8 });   // override any option

   Chromium gets the full effect; everything else falls back to a plain frosted
   blur automatically. Shape and layout (border-radius, size, overflow:hidden)
   stay in your CSS -- the filter clips to the element's rounded border box.

   OPTIONS
     tintTop / tintBottom      body tint gradient, or null to leave background
     fallbackBlur/Saturate     the non-Chromium frosted look
     centerBlur / centerSaturate / centerBrightness   the middle of the pane
     bandX / bandY             rim thickness left-right / top-bottom
     strengthY (0-1)           vertical bend as a fraction of horizontal
     bend                      how hard the rim warps the backdrop
     dispersion                R/B split around bend = chromatic fringe width
     rimBlur / rimSaturate     haze and colour intensity on the rim
     glowSlope / glowIntercept rim brightness lift (1 / 0 = none)
   ========================================================================== */
(function (global) {
  "use strict";

  var SVGNS = "http://www.w3.org/2000/svg";
  var uid = 0;
  var defsSvg = null;

  var supported =
    typeof CSS !== "undefined" &&
    !!global.chrome &&
    CSS.supports("backdrop-filter", "url(#x)");

  var DEFAULTS = {
    tintTop: "rgba(28,32,38,0.08)",
    tintBottom: "rgba(28,32,38,0.14)",
    fallbackBlur: 18,
    fallbackSaturate: 1.65,
    centerBlur: 9,
    centerSaturate: 1.55,
    centerBrightness: 0.92,
    bandX: 38,
    bandY: 14,
    strengthY: 0.30,
    bend: 135,
    dispersion: 18,
    rimBlur: 3,
    rimSaturate: 1.8,
    glowSlope: 1.08,
    glowIntercept: 0.02
  };

  /* single-channel pass-throughs, used to split the backdrop into R/G/B */
  var CHANNELS = {
    R: "1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0",
    G: "0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0",
    B: "0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0"
  };

  function el(name, attrs, parent) {
    var n = document.createElementNS(SVGNS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  function ensureDefs() {
    if (!defsSvg) {
      defsSvg = el("svg", { width: 0, height: 0, "aria-hidden": "true", focusable: "false" });
      defsSvg.style.position = "absolute";
      document.body.appendChild(defsSvg);
    }
    return defsSvg;
  }

  /* Builds the filter with its option values baked in. Returns only the nodes
     that need updating later: the filter itself plus the two generated images. */
  function buildFilter(id, opt) {
    var f = el("filter", {
      id: id, x: 0, y: 0, width: 10, height: 10,
      filterUnits: "userSpaceOnUse", "color-interpolation-filters": "sRGB"
    }, ensureDefs());

    var map = el("feImage", { x: 0, y: 0, width: 10, height: 10, result: "map", href: "" }, f);
    var mask = el("feImage", { x: 0, y: 0, width: 10, height: 10, result: "edgemask", href: "" }, f);

    /* centre: blur, saturate, then dim slightly so the pane reads as smoked */
    el("feGaussianBlur", { "in": "SourceGraphic", stdDeviation: opt.centerBlur, result: "cBlur" }, f);
    el("feColorMatrix", { "in": "cBlur", type: "saturate", values: opt.centerSaturate, result: "cSat" }, f);
    var dim = el("feComponentTransfer", { "in": "cSat", result: "centerLayer" }, f);
    ["feFuncR", "feFuncG", "feFuncB"].forEach(function (fn) {
      el(fn, { type: "linear", slope: opt.centerBrightness, intercept: 0 }, dim);
    });

    /* rim: displace each colour channel by a different amount, then recombine.
       The R/B offset either side of `bend` is what creates the fringing. */
    var scales = { R: opt.bend - opt.dispersion, G: opt.bend, B: opt.bend + opt.dispersion };
    ["R", "G", "B"].forEach(function (c) {
      el("feDisplacementMap", {
        "in": "SourceGraphic", in2: "map", scale: scales[c],
        xChannelSelector: "R", yChannelSelector: "G", result: "disp" + c
      }, f);
      el("feColorMatrix", { "in": "disp" + c, type: "matrix", values: CHANNELS[c], result: "chan" + c }, f);
    });
    el("feBlend", { "in": "chanR", in2: "chanG", mode: "screen", result: "chanRG" }, f);
    el("feBlend", { "in": "chanRG", in2: "chanB", mode: "screen", result: "dispersed" }, f);

    el("feGaussianBlur", { "in": "dispersed", stdDeviation: opt.rimBlur, result: "rBlur" }, f);
    el("feColorMatrix", { "in": "rBlur", type: "saturate", values: opt.rimSaturate, result: "rSat" }, f);
    var glow = el("feComponentTransfer", { "in": "rSat", result: "rimGlow" }, f);
    ["feFuncR", "feFuncG", "feFuncB"].forEach(function (fn) {
      el(fn, { type: "linear", slope: opt.glowSlope, intercept: opt.glowIntercept }, glow);
    });

    /* keep the rim only where the edge mask says, then lay it over the centre */
    el("feComposite", { "in": "rimGlow", in2: "edgemask", operator: "in", result: "rimMasked" }, f);
    var stack = el("feMerge", {}, f);
    el("feMergeNode", { "in": "centerLayer" }, stack);
    el("feMergeNode", { "in": "rimMasked" }, stack);

    return { filter: f, map: map, mask: mask };
  }

  function apply(target, options) {
    var opt = {};
    for (var k in DEFAULTS) opt[k] = DEFAULTS[k];
    for (var j in (options || {})) if (options[j] !== undefined) opt[j] = options[j];

    if (opt.tintTop || opt.tintBottom) {
      target.style.background = "linear-gradient(180deg, " +
        (opt.tintTop || "transparent") + ", " + (opt.tintBottom || "transparent") + ")";
    }

    if (!supported) {
      var plain = "blur(" + opt.fallbackBlur + "px) saturate(" + (opt.fallbackSaturate * 100) + "%)";
      target.style.webkitBackdropFilter = plain;
      target.style.backdropFilter = plain;
      return;
    }

    var id = "liquid-glass-" + (++uid);
    var refs = buildFilter(id, opt);
    target.style.webkitBackdropFilter = "url(#" + id + ")";
    target.style.backdropFilter = "url(#" + id + ")";

    var mapCanvas = document.createElement("canvas");
    var maskCanvas = document.createElement("canvas");

    /* Both images depend on the element's pixel size, so they are rebuilt
       whenever it resizes. */
    function buildImages() {
      var w = Math.max(4, Math.round(target.offsetWidth));
      var h = Math.max(4, Math.round(target.offsetHeight));

      /* displacement map: neutral (128) centre, ramps confined to the rim bands */
      mapCanvas.width = w; mapCanvas.height = h;
      var ctx = mapCanvas.getContext("2d");
      var fx = Math.min(0.49, opt.bandX / w);
      var gx = ctx.createLinearGradient(0, 0, w, 0);
      gx.addColorStop(0, "rgb(0,0,0)");
      gx.addColorStop(fx, "rgb(128,0,0)");
      gx.addColorStop(1 - fx, "rgb(128,0,0)");
      gx.addColorStop(1, "rgb(255,0,0)");
      ctx.fillStyle = gx;
      ctx.fillRect(0, 0, w, h);

      ctx.globalCompositeOperation = "lighter";
      var lo = Math.round(128 - 128 * opt.strengthY);
      var hi = Math.round(128 + 127 * opt.strengthY);
      var fy = Math.min(0.49, opt.bandY / h);
      var gy = ctx.createLinearGradient(0, 0, 0, h);
      gy.addColorStop(0, "rgb(0," + lo + ",0)");
      gy.addColorStop(fy, "rgb(0,128,0)");
      gy.addColorStop(1 - fy, "rgb(0,128,0)");
      gy.addColorStop(1, "rgb(0," + hi + ",0)");
      ctx.fillStyle = gy;
      ctx.fillRect(0, 0, w, h);
      ctx.globalCompositeOperation = "source-over";

      /* rim mask: a white band fading inwards from each edge */
      maskCanvas.width = w; maskCanvas.height = h;
      var m = maskCanvas.getContext("2d");
      m.clearRect(0, 0, w, h);
      function band(x0, y0, x1, y1, vertical, reverse) {
        var g = vertical ? m.createLinearGradient(0, y0, 0, y1)
                         : m.createLinearGradient(x0, 0, x1, 0);
        g.addColorStop(0, reverse ? "rgba(255,255,255,0)" : "rgba(255,255,255,1)");
        g.addColorStop(1, reverse ? "rgba(255,255,255,1)" : "rgba(255,255,255,0)");
        m.fillStyle = g;
        m.fillRect(Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0), Math.abs(y1 - y0));
      }
      band(0, 0, w, opt.bandY, true, false);
      band(0, h - opt.bandY, w, h, true, true);
      band(0, 0, opt.bandX, h, false, false);
      band(w - opt.bandX, 0, w, h, false, true);

      [[refs.map, mapCanvas], [refs.mask, maskCanvas]].forEach(function (pair) {
        pair[0].setAttribute("href", pair[1].toDataURL("image/png"));
        pair[0].setAttribute("width", w);
        pair[0].setAttribute("height", h);
      });
      refs.filter.setAttribute("width", w);
      refs.filter.setAttribute("height", h);
    }

    buildImages();
    if (global.ResizeObserver) new ResizeObserver(buildImages).observe(target);
    else global.addEventListener("resize", buildImages);
  }

  global.LiquidGlass = { apply: apply, supported: supported };
})(window);
