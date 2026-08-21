/* Guarded: if the id is missing the call throws and nothing below it runs. */
var ctaBtn = document.getElementById("ctaBtn");
if (ctaBtn) LiquidGlass.apply(ctaBtn, {
  bandX: 12, bandY: 9, strengthY: .82, bend: 24, dispersion: 6,
  rimBlur: 1.2, rimSaturate: 1.65,
  centerBlur: 4, centerSaturate: 1.28, centerBrightness: .94,
  tintTop: "rgba(30,34,43,.82)", tintBottom: "rgba(10,12,18,.72)",
  fallbackBlur: 16, fallbackSaturate: 1.55
});

(function () {
  const stored = sessionStorage.getItem("tripBridgeAnalysis");

  if (!stored) {
    $("analysisJson").textContent =
      "No analysis yet — head back to the upload step and choose a travel video.";
    $("ctaBtn").setAttribute("aria-disabled", "true");
    $("ctaBtn").style.pointerEvents = "none";
    $("ctaBtn").style.opacity = ".5";
    return;
  }

  $("analysisJson").textContent = JSON.stringify(JSON.parse(stored), null, 2);
})();
