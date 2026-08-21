/* Guarded: if an id is missing the call throws and nothing below it runs.
   Both the rail's send button and the CTA on the sent card get the treatment. */
["sendBtn", "sentCta"].forEach(function (id) {
  var el = document.getElementById(id);
  if (el) LiquidGlass.apply(el, {
    bandX: 12, bandY: 9, strengthY: .82, bend: 24, dispersion: 6,
    rimBlur: 1.2, rimSaturate: 1.65,
    centerBlur: 4, centerSaturate: 1.28, centerBrightness: .94,
    tintTop: "rgba(30,34,43,.82)", tintBottom: "rgba(10,12,18,.72)",
    fallbackBlur: 16, fallbackSaturate: 1.55
  });
});

(function () {
  var BOOKING_FEE = 49;      // per booking, not per traveller
  var DEPOSIT_RATE = .20;

  var customer = FlowStore.read(FlowStore.CUSTOMER);
  var selected = null;

  // ── formatting ──────────────────────────────────────────────────────────────
  var money = (n) => "A$" + Math.round(n).toLocaleString("en-AU");
  var esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function longDate(d) {
    return d.toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
  }

  // ── the package chosen on the Build Package step ────────────────────────────
  // Both the shortlist and the choice come from the session, so this page only
  // has to find the one that was picked.
  function chosenPackage() {
    var id = FlowStore.read(FlowStore.QUOTE).packageId;
    if (!id) return null;
    try {
      var all = JSON.parse(sessionStorage.getItem("tripBridgePackages"));
      return (Array.isArray(all) ? all : []).find(p => p.id === id) || null;
    } catch (e) {
      return null;
    }
  }

  function renderChosen() {
    $("chosen").hidden = !selected;
    $("changeLink").hidden = !selected;
    $("pickEmpty").hidden = !!selected;
    if (!selected) return;

    if (selected.image_url) {
      $("chosenThumb").style.backgroundImage = 'url("' + selected.image_url + '")';
    }
    $("chosenName").textContent = selected.name;
    $("chosenMeta").textContent = selected.destination + " · " +
      selected.duration_nights + " nights · " + selected.category;
    $("chosenPrice").textContent = money(selected.price_from_aud);

    // the styles the video actually matched lead, the rest follow
    var matched = selected.matched_vibes || [];
    var tags = matched.slice(0, 2).map(t => '<span class="pick-tag pick-tag--match">' + esc(t) + "</span>")
      .concat((selected.vibe_tags || []).filter(t => matched.indexOf(t) === -1).slice(0, 2)
        .map(t => '<span class="pick-tag">' + esc(t) + "</span>"));
    $("chosenTags").innerHTML = tags.join("");
  }

  // ── the running total ───────────────────────────────────────────────────────
  function totals() {
    var travellers = Math.max(1, Number($("qTravellers").value) || 1);
    var perPerson = selected ? Number(selected.price_from_aud) || 0 : 0;
    var subtotal = perPerson * travellers;
    var fee = selected ? BOOKING_FEE : 0;
    var total = subtotal + fee;
    return { travellers, perPerson, subtotal, fee, total, deposit: total * DEPOSIT_RATE };
  }

  function render() {
    var t = totals();

    $("sumName").textContent = selected ? selected.name : "No package selected";
    $("sumMeta").textContent = selected
      ? selected.destination + " · " + selected.duration_nights + " nights"
      : "Pick one on the Build Package step.";

    $("sumPer").textContent = selected ? money(t.perPerson) : "—";
    $("sumTravellersLabel").textContent = "Travellers × " + t.travellers;
    $("sumTravellers").textContent = selected ? money(t.subtotal) : "—";
    $("sumFee").textContent = selected ? money(t.fee) : "—";

    $("sumTotal").textContent = money(selected ? t.total : 0);
    $("sumDeposit").textContent = money(selected ? t.deposit : 0);

    $("sendBtn").disabled = !selected;

    var days = Math.max(1, Number($("qValid").value) || 1);
    var until = new Date();
    until.setDate(until.getDate() + days);
    $("validUntil").textContent = "Valid until " + longDate(until);
  }

  // ── what this page remembers ────────────────────────────────────────────────
  // packageId belongs to the Build Package step and the name and email belong to
  // the customer step, so neither is written back from here. basedOn records the
  // customer answers this page was last built from — see restore().
  function save() {
    FlowStore.patch(FlowStore.QUOTE, {
      travellers: $("qTravellers").value,
      departure: $("qDeparture").value,
      validDays: $("qValid").value,
      message: $("qMessage").value,
      basedOn: { travellers: customer.travellers, dateFrom: customer.dateFrom }
    });
  }

  function restore() {
    var saved = FlowStore.read(FlowStore.QUOTE);
    var basedOn = saved.basedOn || {};

    // The party size and the dates come from the customer step, but an agent can
    // still tune them for this one quote. So: a fresh answer over there wins, and
    // otherwise whatever was last set here holds.
    function carried(field, edited, fallback) {
      var answer = customer[field];
      if (answer && answer !== basedOn[field]) return answer;
      return edited || answer || fallback;
    }
    $("qTravellers").value = carried("travellers", saved.travellers, 2);
    $("qDeparture").value = carried("dateFrom", saved.departure, "");

    // display-only, so they track the customer step and nothing else
    $("qName").value = customer.custName || "";
    $("qEmail").value = customer.custEmail || "";

    if (saved.validDays) $("qValid").value = saved.validDays;
    if (saved.message) $("qMessage").value = saved.message;
  }

  ["qTravellers", "qDeparture", "qValid", "qMessage"]
    .forEach(id => $(id).addEventListener("input", () => { save(); render(); }));

  // ── sending ─────────────────────────────────────────────────────────────────
  // Nothing leaves the browser: there is no mail route yet, so this is the
  // confirmation the real one will show once /send-quote exists.
  $("sendBtn").addEventListener("click", () => {
    if (!selected) return;
    var to = $("qEmail").value.trim();

    $("sentSub").textContent = to ? "Sent to " + to : "Add an email address to send it on.";
    $("sentPkg").textContent = selected.name;
    $("sentTotal").textContent = money(totals().total);
    $("sentVeil").hidden = false;
    $("sentCta").focus();
  });

  // The card's only button starts a new trip, so escape and a click on the
  // backdrop are what dismiss it rather than trapping anyone behind it.
  function closeSent() {
    $("sentVeil").hidden = true;
    $("sendBtn").focus();
  }
  $("sentVeil").addEventListener("click", (e) => {
    if (e.target === $("sentVeil")) closeSent();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !$("sentVeil").hidden) closeSent();
  });

  // ── design-time sample data ─────────────────────────────────────────────────
  // Lets this page be looked at without re-running a video analysis. Remove
  // this block and #sampleBtn in finalquote.html once the flow is demoed live.
  $("sampleBtn").addEventListener("click", () => {
    sessionStorage.setItem("tripBridgePackages", JSON.stringify([
      { id: "sample-1", name: "European Whirl", destination: "Europe", duration_nights: 11,
        price_from_aud: 6135, category: "tour", vibe_tags: ["cultural", "city", "food"],
        matched_vibes: ["cultural", "city"] }
    ]));
    FlowStore.patch(FlowStore.QUOTE, { packageId: "sample-1" });
    window.location.reload();
  });

  // ── go ──────────────────────────────────────────────────────────────────────
  selected = chosenPackage();
  restore();
  renderChosen();
  render();
  // records basedOn, so a later change on the customer step is recognisable
  save();
})();
