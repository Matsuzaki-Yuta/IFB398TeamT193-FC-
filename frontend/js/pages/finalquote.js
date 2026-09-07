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

    // "sending" is declared further down; var-hoisting makes it undefined on the
    // first pass, which is falsy, so the button behaves normally on load and
    // stays locked if an input changes mid-send.
    $("sendBtn").disabled = !selected || !!sending;

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
  // The page adds up the total on the left for the agent to watch, but that
  // number is not what gets emailed. Only the package id goes to the server,
  // which rebuilds every figure from packages.db — a price typed into the dev
  // tools must never reach a customer's inbox.

  var sending = false;

  function showError(message) {
    $("sendError").textContent = message;
    $("sendError").hidden = !message;
  }

  function setSending(on) {
    sending = on;
    $("sendBtn").disabled = on || !selected;
    $("sendBtn").classList.toggle("is-sending", on);
    $("sendLabel").textContent = on ? "Sending\u2026" : "Send quote";
    $("sendBtn").setAttribute("aria-busy", on ? "true" : "false");
  }

  // The two readonly fields are filled from the customer step. If the agent
  // skipped it there is nothing to send to, and saying so here is more use than
  // letting the request fail with a 400.
  function recipient() {
    var email = $("qEmail").value.trim();
    if (!email) {
      showError("No email address yet — add one on the Customer step, then come back.");
      return null;
    }
    return email;
  }

  function payload() {
    return {
      customer: {
        name: $("qName").value.trim(),
        email: $("qEmail").value.trim(),
        travellers: Number($("qTravellers").value) || 1
      },
      quote: {
        departure: $("qDeparture").value,
        valid_days: Number($("qValid").value) || 14,
        message: $("qMessage").value.trim()
      },
      selected_package_id: selected.id
    };
  }

  // Every error path ends with a sentence the agent can act on. A bare
  // "something went wrong" in front of the industry partner is worse than
  // no message at all.
  function messageFor(status, body) {
    if (body && body.error && body.error.message) return body.error.message;
    if (status === 0) return "Could not reach the server. Check that Flask is still running.";
    return "The quote could not be sent (error " + status + "). Please try again.";
  }

  function showSent(result) {
    var pdfNote = result.attached_pdf
      ? "The quote is attached as a PDF."
      : "The quote is in the body of the email.";

    $("sentTitle").textContent = "Quote sent";
    $("sentSub").textContent =
      "We've emailed it to " + result.sent_to +
      ". It usually arrives within a minute. If not, check your spam folder.";
    $("sentTo").textContent = result.sent_to;
    $("sentPkg").textContent = selected.name;
    $("sentTotal").textContent = result.total;
    $("sentRef").textContent = result.quote_reference;
    $("sentNote").textContent = pdfNote + " Valid until " + result.valid_until + ".";

    $("sentVeil").hidden = false;
    $("sentCta").focus();

    // and the strip that survives the card being dismissed
    $("sentStripText").textContent =
      "Sent to " + result.sent_to + " · reference " + result.quote_reference;
    $("sentStrip").hidden = false;
  }

  $("sendBtn").addEventListener("click", function () {
    if (!selected || sending) return;

    showError("");
    if (!recipient()) return;

    setSending(true);

    fetch("/api/quote/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload())
    })
      .then(function (response) {
        // .json() rejects on an empty or HTML body — a 500 page, most often —
        // so it is caught here and the status still drives the message.
        return response.json()
          .catch(function () { return null; })
          .then(function (body) { return { status: response.status, body: body }; });
      })
      .then(function (result) {
        if (result.status === 200 && result.body && result.body.success) {
          showSent(result.body);
        } else {
          showError(messageFor(result.status, result.body));
        }
      })
      .catch(function () {
        // Network-level failure: the request never got an answer at all.
        showError(messageFor(0, null));
      })
      .then(function () {
        setSending(false);
      });
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
  // Lets this page be worked on, and the email tested, without re-running a
  // video analysis every time.
  //
  // It asks the backend for real packages rather than inventing one. A made-up
  // id would render fine here and then be rejected by /api/quote/send, which
  // rebuilds the quote from packages.db and has never heard of it — so the one
  // button meant to make testing easy would fail at the only step worth testing.
  //
  // Remove this block and #sampleBtn in finalquote.html once the flow is being
  // demoed live end to end.
  $("sampleBtn").addEventListener("click", function () {
    var button = $("sampleBtn");
    button.disabled = true;
    button.textContent = "Loading a sample…";

    fetch("/api/packages/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analysis: {
          detected_destinations: ["Europe"],
          destination_region: "Europe",
          travel_style: ["cultural", "city"]
        }
      })
    })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var packages = (data && data.packages) || [];
        if (!packages.length) throw new Error("no packages matched");

        sessionStorage.setItem("tripBridgePackages", JSON.stringify(packages.slice(0, 3)));
        FlowStore.patch(FlowStore.QUOTE, { packageId: packages[0].id });

        // Only fills in what the customer step has not already answered, so
        // this never overwrites a real address someone is testing with.
        var saved = FlowStore.read(FlowStore.CUSTOMER);
        FlowStore.patch(FlowStore.CUSTOMER, {
          custName: saved.custName || "Jordan Lee",
          custEmail: saved.custEmail || "",
          travellers: saved.travellers || 2
        });

        window.location.reload();
      })
      .catch(function () {
        button.disabled = false;
        button.textContent = "Preview with sample data";
        showError("Could not load a sample package. Is packages.db in the project root?");
      });
  });

  // ── go ──────────────────────────────────────────────────────────────────────
  selected = chosenPackage();
  restore();
  renderChosen();
  render();
  // records basedOn, so a later change on the customer step is recognisable
  save();
})();
