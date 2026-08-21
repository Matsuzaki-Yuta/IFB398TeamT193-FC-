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
  var selectedAge = null;
  var travellers = 2;

  // Coming back from a later step reloads this page from scratch, so every
  // answer is written to the flow store as it is made and read back on load.
  function save() {
    FlowStore.patch(FlowStore.CUSTOMER, {
      custName: document.getElementById('custName').value,
      custEmail: document.getElementById('custEmail').value,
      ageRange: selectedAge,
      travellers: travellers,
      dateFrom: document.getElementById('dateFrom').value,
      dateTo: document.getElementById('dateTo').value,
      budget: document.getElementById('budget').value
    });
  }

  // age-range chips: single-select
  var ageChips = document.getElementById('ageChips');
  var ageError = document.getElementById('ageError');
  var chips = Array.from(ageChips.querySelectorAll('.chip'));
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      selectAge(chip.dataset.value);
      showAgeError(false);
      save();
    });
  });

  function selectAge(value) {
    var match = chips.find(c => c.dataset.value === value);
    if (!match) return;
    chips.forEach(c => c.classList.remove('is-selected'));
    match.classList.add('is-selected');
    selectedAge = value;
  }

  // the chips are buttons, so there is no native validity to lean on here
  function showAgeError(show) {
    ageError.hidden = !show;
    ageChips.setAttribute('aria-invalid', show ? 'true' : 'false');
  }

  // Required inputs: the browser blocks the submit and fires "invalid" at each
  // offending field. That is the moment to paint it red — not on page load,
  // when nothing has been filled in yet and everything is legitimately empty.
  // The event does not bubble, hence the capture phase.
  var form = document.getElementById('customerForm');
  form.addEventListener('invalid', (e) => {
    e.target.classList.add('is-invalid');
  }, true);
  form.addEventListener('input', (e) => {
    if (e.target.checkValidity && e.target.checkValidity()) {
      e.target.classList.remove('is-invalid');
    }
    save();
  });

  // traveller stepper
  var travellersValue = document.getElementById('travellersValue');
  document.getElementById('travellerStepper').addEventListener('click', (e) => {
    var action = e.target.closest('button');
    if (!action) return;
    if (action.dataset.action === 'inc') travellers = Math.min(12, travellers + 1);
    if (action.dataset.action === 'dec') travellers = Math.max(1, travellers - 1);
    travellersValue.textContent = travellers;
    save();
  });

  // budget: number field <-> slider, two-way
  var budgetInput = document.getElementById('budget');
  var budgetSlider = document.getElementById('budgetSlider');
  budgetSlider.addEventListener('input', () => { budgetInput.value = budgetSlider.value; save(); });
  budgetInput.addEventListener('input', () => {
    var v = Math.max(500, Math.min(15000, Number(budgetInput.value) || 0));
    budgetSlider.value = v;
  });

  // Put back whatever was entered earlier in this session. The slider mirrors
  // the number field, so it is set from the restored budget rather than stored
  // separately.
  (function restore() {
    var saved = FlowStore.read(FlowStore.CUSTOMER);
    ['custName', 'custEmail', 'dateFrom', 'dateTo', 'budget'].forEach((id) => {
      if (saved[id]) document.getElementById(id).value = saved[id];
    });
    if (saved.budget) budgetSlider.value = saved.budget;
    if (saved.ageRange) selectAge(saved.ageRange);
    if (saved.travellers) {
      travellers = saved.travellers;
      travellersValue.textContent = travellers;
    }
  })();

  // Continue on to the Inspiration step (the /match page's upload section).
  // The browser has already enforced every required input by the time this
  // fires — an invalid one blocks the submit event entirely — so only the age
  // chips are left to check.
  document.getElementById('customerForm').addEventListener('submit', () => {
    if (!selectedAge) {
      showAgeError(true);
      chips[0].focus();
      return;
    }
    save();
    window.location.href = '/match';
  });
})();
