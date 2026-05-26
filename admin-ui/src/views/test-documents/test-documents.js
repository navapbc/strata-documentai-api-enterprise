/**
 * Test documents view - upload and test document extraction via BDA.
 */
import * as BlueprintTestService from "../../services/blueprint-test.js";
import * as CategoriesService from "../../services/document-categories.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Helpers from "../../utils/helpers.js";
import * as Toast from "../../utils/toast.js";
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import html from "./test-documents.html";

const tmpl = tpl(html);

let _root = null;
let _tenantSelect, _categorySelect, _fileInput, _runBtn, _cancelBtn;
let _elapsed, _results, _historyList;
let _abortController = null;
let _startTime = null;
let _elapsedTimer = null;
let _history = [];
let _tenantUnsub = null;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  // Inject actions into shared header
  _tenantSelect = h(
    "select",
    { className: "tenant-select", id: "test-tenant-select" },
    h("option", { value: "" }, "- Select tenant -"),
  );
  _categorySelect = h(
    "select",
    { className: "tenant-select", id: "test-category-select" },
    h("option", { value: "" }, "- Select category -"),
  );
  _fileInput = h("input", {
    type: "file",
    id: "test-file-input",
    accept: ".pdf,.png,.jpg,.jpeg,.tiff,.tif",
  });
  _runBtn = h("button", { className: "btn-primary", disabled: "true" }, "Run Extraction");
  _cancelBtn = h("button", { className: "btn-secondary hidden" }, "Cancel");
  Helpers.setViewActions(_tenantSelect, _categorySelect, _fileInput, _runBtn, _cancelBtn);
  _elapsed = root.querySelector("#test-elapsed");
  _results = root.querySelector("#test-results");
  _historyList = root.querySelector("#test-history-list");

  _runBtn.addEventListener("click", runTest);
  _cancelBtn.addEventListener("click", cancelTest);
  _tenantSelect.addEventListener("change", loadCategories);
  _fileInput.addEventListener("change", updateRunButton);
  _categorySelect.addEventListener("change", updateRunButton);

  _tenantUnsub = TenantContext.onChange(() => {
    _tenantSelect.value = TenantContext.getTenantId() || "";
    loadCategories();
  });

  populateTenantSelect();
}

export function unmount(root) {
  cancelTest();
  if (_tenantUnsub) {
    _tenantUnsub();
    _tenantUnsub = null;
  }
  if (_root) _root.replaceChildren();
}

function populateTenantSelect() {
  /** @type {HTMLSelectElement} */
  const globalSelect = document.querySelector("#global-tenant-select");
  if (!globalSelect) return;
  _tenantSelect.innerHTML = '<option value="">- Select tenant -</option>';
  for (const opt of globalSelect.options) {
    if (opt.value) {
      const newOpt = document.createElement("option");
      newOpt.value = opt.value;
      newOpt.textContent = opt.textContent;
      _tenantSelect.appendChild(newOpt);
    }
  }
  const current = TenantContext.getTenantId();
  if (current) {
    _tenantSelect.value = current;
    loadCategories();
  }
}

async function loadCategories() {
  const tenantId = _tenantSelect.value;
  _categorySelect.innerHTML = '<option value="">- Select category -</option>';
  if (!tenantId) return;

  try {
    const data = await CategoriesService.list(tenantId);
    for (const cat of data.categories || []) {
      const opt = document.createElement("option");
      opt.value = cat.categoryName;
      opt.textContent = cat.displayName || cat.categoryName;
      _categorySelect.appendChild(opt);
    }
  } catch {
    // leave empty
  }
  updateRunButton();
}

function updateRunButton() {
  _runBtn.disabled = !(_tenantSelect.value && _categorySelect.value && _fileInput.files.length > 0);
}

async function runTest() {
  const tenantId = _tenantSelect.value;
  const category = _categorySelect.value;
  const file = _fileInput.files[0];
  if (!tenantId || !category || !file) return;

  _runBtn.disabled = true;
  _cancelBtn.classList.remove("hidden");
  _elapsed.classList.remove("hidden");
  _results.classList.add("hidden");
  _startTime = Date.now();
  _abortController = new AbortController();

  _elapsedTimer = setInterval(updateElapsed, 1000);
  updateElapsed();

  try {
    const result = await BlueprintTestService.run(
      file,
      tenantId,
      category,
      null,
      _abortController.signal,
    );
    renderResult(result);
    addToHistory(result);
  } catch (e) {
    if (e.name !== "AbortError") {
      Toast.show(`Test failed: ${e.message}`);
    }
  } finally {
    if (_elapsedTimer) {
      clearInterval(_elapsedTimer);
      _elapsedTimer = null;
    }
    _cancelBtn.classList.add("hidden");
    _elapsed.classList.add("hidden");
    _runBtn.disabled = false;
    _abortController = null;
  }
}

function cancelTest() {
  if (_abortController) _abortController.abort();
}

function updateElapsed() {
  if (!_startTime) return;
  const seconds = Math.floor((Date.now() - _startTime) / 1000);
  _elapsed.textContent = `Elapsed: ${seconds}s`;
}

function renderResult(result) {
  _results.classList.remove("hidden");
  _results.replaceChildren();

  if (result.status === "FAILED") {
    _results.appendChild(
      h("p", { className: "error" }, `Test failed: ${result.error || "Unknown error"}`),
    );
    return;
  }

  const fields = result.fields || {};
  const tbody = h("tbody", null);
  for (const [name, data] of Object.entries(fields)) {
    const conf = data.confidence != null ? `${(data.confidence * 100).toFixed(0)}%` : "-";
    tbody.appendChild(
      h(
        "tr",
        null,
        h("td", null, name),
        h("td", null, String(data.value ?? "-")),
        h("td", null, conf),
      ),
    );
  }

  _results.appendChild(h("h3", null, `Results: ${result.matchedBlueprint || "-"}`));
  const table = h(
    "table",
    { className: "detail-table" },
    h(
      "thead",
      null,
      h("tr", null, h("th", null, "Field"), h("th", null, "Value"), h("th", null, "Confidence")),
    ),
    tbody,
  );
  _results.appendChild(table);
}

function addToHistory(result) {
  _history.unshift(result);
  renderHistory();
}

function renderHistory() {
  _historyList.replaceChildren();
  if (_history.length === 0) {
    _historyList.appendChild(h("li", { className: "empty-state" }, "No tests yet"));
    return;
  }
  _history.forEach((r, i) => {
    const li = h(
      "li",
      { className: "clickable-row" },
      `${r.matchedBlueprint || "Unknown"} - ${r.status}`,
    );
    li.addEventListener("click", () => renderResult(_history[i]));
    _historyList.appendChild(li);
  });
}
