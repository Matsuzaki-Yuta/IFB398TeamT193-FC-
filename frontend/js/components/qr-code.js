/* ============================================================================
   QR PLACEHOLDER  (qr-code.js)
   ----------------------------------------------------------------------------
   Draws a QR-shaped graphic into #qrSvg as inline SVG rects — no image file, so
   it stays sharp at any size and picks up the theme tokens.

   IMPORTANT: this does NOT encode a real URL. The module pattern comes from a
   seeded pseudo-random generator, so it looks structurally right (finder
   patterns, timing rows, alignment square) but a phone camera reads nothing
   from it. Swap this for a real encoder once there is a pairing endpoint to
   point at — generating it server-side (python "qrcode" emits SVG) keeps the
   pairing URL out of client-side code.
   ========================================================================== */
(function () {
  "use strict";

  var svg = document.getElementById("qrSvg");
  if (!svg) return;

  var N = 25;
  var NS = "http://www.w3.org/2000/svg";
  var grid = [], reserved = [];
  var y, x, i;

  for (y = 0; y < N; y++) {
    grid.push(new Array(N).fill(false));
    reserved.push(new Array(N).fill(false));
  }

  // reserve the three finder patterns plus their one-module quiet ring
  function reserveFinder(r, c) {
    for (var dy = -1; dy <= 7; dy++) {
      for (var dx = -1; dx <= 7; dx++) {
        var gy = r + dy, gx = c + dx;
        if (gy < 0 || gx < 0 || gy >= N || gx >= N) continue;
        reserved[gy][gx] = true;
      }
    }
  }
  reserveFinder(0, 0);
  reserveFinder(0, N - 7);
  reserveFinder(N - 7, 0);

  // timing rows and the alignment square
  for (i = 0; i < N; i++) { reserved[6][i] = true; reserved[i][6] = true; }
  for (y = 16; y < 21; y++) for (x = 16; x < 21; x++) reserved[y][x] = true;

  // fixed seed so the code renders identically on every load
  var seed = 0x9e3779b9;
  function rand() {
    seed = (seed ^ (seed << 13)) >>> 0;
    seed = (seed ^ (seed >>> 17)) >>> 0;
    seed = (seed ^ (seed << 5)) >>> 0;
    return seed / 4294967296;
  }
  for (y = 0; y < N; y++) for (x = 0; x < N; x++)
    if (!reserved[y][x]) grid[y][x] = rand() > 0.5;

  function add(tag, attrs) {
    var el = document.createElementNS(NS, tag);
    for (var k in attrs) el.setAttribute(k, attrs[k]);
    svg.appendChild(el);
    return el;
  }

  var ink = "var(--text)", paper = "var(--bg-elev)";

  // data modules, softly rounded so the code reads as designed
  for (y = 0; y < N; y++) for (x = 0; x < N; x++)
    if (grid[y][x]) add("rect", { x: x + 0.1, y: y + 0.1, width: 0.8, height: 0.8, rx: 0.28, fill: ink });

  // timing patterns
  for (i = 8; i < N - 8; i++) {
    if (i % 2 === 0) {
      add("rect", { x: i + 0.1, y: 6.1, width: 0.8, height: 0.8, rx: 0.28, fill: ink });
      add("rect", { x: 6.1, y: i + 0.1, width: 0.8, height: 0.8, rx: 0.28, fill: ink });
    }
  }

  // finder patterns
  [[0, 0], [0, N - 7], [N - 7, 0]].forEach(function (pos) {
    var r = pos[0], c = pos[1];
    add("rect", { x: c, y: r, width: 7, height: 7, rx: 2, fill: ink });
    add("rect", { x: c + 1, y: r + 1, width: 5, height: 5, rx: 1.4, fill: paper });
    add("rect", { x: c + 2, y: r + 2, width: 3, height: 3, rx: 0.9, fill: ink });
  });

  // alignment pattern
  add("rect", { x: 16, y: 16, width: 5, height: 5, rx: 1.4, fill: ink });
  add("rect", { x: 17, y: 17, width: 3, height: 3, rx: 0.9, fill: paper });
  add("rect", { x: 18, y: 18, width: 1, height: 1, rx: 0.3, fill: ink });

  // brand mark punched through the middle
  add("rect", { x: 9.6, y: 9.6, width: 5.8, height: 5.8, rx: 1.6, fill: paper });
  add("rect", { x: 10.4, y: 10.4, width: 4.2, height: 4.2, rx: 1.2, fill: "var(--fc-red)" });
  var mark = add("text", {
    x: 12.5, y: 12.5, "text-anchor": "middle", "dominant-baseline": "central",
    fill: "#fff", "font-size": "2.6", "font-weight": "400"
  });
  mark.textContent = "✕";
})();
