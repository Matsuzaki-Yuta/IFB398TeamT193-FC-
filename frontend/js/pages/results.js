/* Guarded: if the id is missing the call throws and nothing below it runs. */
var ctaBtn = document.getElementById("ctaBtn");
if (ctaBtn) LiquidGlass.apply(ctaBtn, {
  bandX: 12, bandY: 9, strengthY: .82, bend: 24, dispersion: 6,
  rimBlur: 1.2, rimSaturate: 1.65,
  centerBlur: 4, centerSaturate: 1.28, centerBrightness: .94,
  tintTop: "rgba(30,34,43,.82)", tintBottom: "rgba(10,12,18,.72)",
  fallbackBlur: 16, fallbackSaturate: 1.55
});

var esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function packageCard(pkg) {
  const image = pkg.image_url
    ? `<img src="${esc(pkg.image_url)}" alt="" onerror="this.style.display='none'"/>`
    : "";
  // three at most: the tag row is one line high, so anything beyond that would
  // be hidden anyway
  const tags = (pkg.vibe_tags || []).slice(0, 3)
    .map(t => `<span class="tag">${esc(t)}</span>`).join("");

  // Roughly half the packages have no destination recorded, so the parts are
  // filtered before they are joined — otherwise those cards open on a stray "|".
  const meta = [pkg.destination, `${pkg.duration_nights} nights`, pkg.category]
    .filter(Boolean).map(esc).join(" &nbsp;|&nbsp; ");

  // A card is here to be chosen between, so it carries only what separates one
  // package from the next — the prose and the matcher's reasoning live on the
  // package's own page, behind "View Package".
  // The whole card is the target, so the button below is a label for what a
  // click does rather than the only way to choose.
  return `
    <div class="package-card lift" role="radio" aria-checked="false" tabindex="0" data-id="${esc(pkg.id)}">
      ${image}
      <h3>${esc(pkg.name)}</h3>
      <div class="price">From A$${pkg.price_from_aud.toLocaleString()}</div>
      <div class="meta">${meta}</div>
      <div class="tags">${tags}</div>
      <div class="card-foot">
        <span class="choose-mark">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
          <b class="choose-label">Choose this package</b>
        </span>
        <a href="${esc(pkg.url)}" target="_blank" rel="noopener">View Package &rarr;</a>
      </div>
    </div>`;
}

(function () {
  const stored = sessionStorage.getItem("tripBridgePackages");

  if (!stored) {
    $("no-match").textContent =
      "No packages yet — head back to the upload step and choose a travel video.";
    $("no-match").hidden = false;
    return;
  }

  const packages = JSON.parse(stored);

  if (!packages.length) {
    $("no-match").hidden = false;
    return;
  }

  $("resultsHeading").textContent = `Matched Packages (${packages.length})`;
  $("results").innerHTML = packages.map(packageCard).join("");

  const cards = Array.from($("results").querySelectorAll(".package-card"));

  // The choice is this step's output: the quote page reads it back out of the
  // same record the rest of the flow uses.
  function select(id) {
    var found = false;
    cards.forEach((card) => {
      var on = card.dataset.id === id;
      if (on) found = true;
      card.classList.toggle("is-selected", on);
      card.setAttribute("aria-checked", on ? "true" : "false");
      card.querySelector(".choose-label").textContent = on ? "Selected" : "Choose this package";
    });
    if (found) FlowStore.patch(FlowStore.QUOTE, { packageId: id });
    gate(found);
  }

  // Nothing to quote until one is picked, so the forward button stays shut.
  function gate(open) {
    $("ctaBtn").setAttribute("aria-disabled", open ? "false" : "true");
    $("ctaBtn").classList.toggle("is-locked", !open);
    $("chooseHint").hidden = open;
  }

  $("results").addEventListener("click", (e) => {
    // the package's own link is the one thing that is not a selection
    if (e.target.closest("a")) return;
    var card = e.target.closest(".package-card");
    if (card) select(card.dataset.id);
  });

  $("results").addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    var card = e.target.closest(".package-card");
    if (!card) return;
    e.preventDefault();
    select(card.dataset.id);
  });

  $("ctaBtn").addEventListener("click", (e) => {
    if ($("ctaBtn").getAttribute("aria-disabled") === "true") e.preventDefault();
  });

  select(FlowStore.read(FlowStore.QUOTE).packageId);
})();
