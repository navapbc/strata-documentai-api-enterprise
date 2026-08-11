/**
 * Date range picker component.
 *
 * Usage:
 *   const picker = mount(root);
 *   picker.getRange();         // { dateFrom, dateTo } as YYYY-MM-DD strings or null
 *   picker.onChange(cb);       // cb called with { dateFrom, dateTo } on change
 *   picker.reset();            // resets to default preset, hides custom inputs
 *   picker.unmount();
 */

function fmt(d) {
  return d.toISOString().slice(0, 10);
}

export function mount(root, { placeholder = "Any date", defaultPreset = "" } = {}) {
  root.innerHTML = `
<select class="drp-preset">
  <option value=""></option>
  <option value="1">Yesterday</option>
  <option value="7">Last 7 days</option>
  <option value="30">Last 30 days</option>
  <option value="90">Last 90 days</option>
  <option value="custom">Custom</option>
</select>
<div class="drp-custom hidden" style="margin-top:0.5rem">
  <div class="metrics-timeframe">
    <label class="metrics-timeframe-label">From</label>
    <input type="date" class="drp-from" />
  </div>
  <div class="metrics-timeframe" style="margin-top:0.5rem">
    <label class="metrics-timeframe-label">To</label>
    <input type="date" class="drp-to" />
  </div>
</div>
`;
  root.querySelector(".drp-preset option[value='']").textContent = placeholder;

  const preset = root.querySelector(".drp-preset");
  const customEl = root.querySelector(".drp-custom");
  const fromInput = root.querySelector(".drp-from");
  const toInput = root.querySelector(".drp-to");

  if (defaultPreset) {
    preset.value = defaultPreset;
    customEl.classList.toggle("hidden", defaultPreset !== "custom");
  }

  const today = fmt(new Date());
  fromInput.max = today;
  toInput.max = today;

  const listeners = [];

  function getRange() {
    const val = preset.value;
    if (!val) return { dateFrom: null, dateTo: null };
    if (val === "custom")
      return { dateFrom: fromInput.value || null, dateTo: toInput.value || null };
    const end = new Date();
    const start = new Date();
    if (val === "1") {
      start.setDate(start.getDate() - 1);
      end.setDate(end.getDate() - 1);
    } else {
      start.setDate(start.getDate() - parseInt(val));
    }
    return { dateFrom: fmt(start), dateTo: fmt(end) };
  }

  function notify() {
    const range = getRange();
    listeners.forEach((cb) => cb(range));
  }

  preset.addEventListener("change", () => {
    customEl.classList.toggle("hidden", preset.value !== "custom");
    if (preset.value !== "custom") notify();
  });

  fromInput.addEventListener("change", notify);
  toInput.addEventListener("change", notify);

  function onChange(cb) {
    listeners.push(cb);
    return () => listeners.splice(listeners.indexOf(cb), 1);
  }

  function reset() {
    preset.value = "";
    fromInput.value = "";
    toInput.value = "";
    customEl.classList.add("hidden");
  }

  function unmount() {
    root.innerHTML = "";
    listeners.length = 0;
  }

  return { getRange, onChange, reset, unmount };
}
