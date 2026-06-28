/**
 * Test documents view - upload and test document extraction via BDA.
 */
import * as BlueprintTestService from "../../services/blueprint-test.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Helpers from "../../utils/helpers.js";
import * as Toast from "../../utils/toast.js";
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import html from "./test-documents.html";

const tmpl = tpl(html);

let _root = null;
let _fileInput, _runBtn, _cancelBtn;
let _dropzone, _dropzoneIdle, _dropzoneSelected, _fileName, _fileClear;
let _elapsed, _results, _historyList;
let _abortController = null;
let _startTime = null;
let _elapsedTimer = null;
let _history = [];
let _tenantUnsub = null;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  Helpers.setViewActions(); // no header actions for this view

  _fileInput = root.querySelector("#test-file-input");
  _runBtn = root.querySelector("#test-run-btn");
  _cancelBtn = root.querySelector("#test-cancel-btn");
  _dropzone = root.querySelector("#test-dropzone");
  _dropzoneIdle = root.querySelector("#test-dropzone-idle");
  _dropzoneSelected = root.querySelector("#test-dropzone-selected");
  _fileName = root.querySelector("#test-file-name");
  _fileClear = root.querySelector("#test-file-clear");
  _elapsed = root.querySelector("#test-elapsed");
  _results = root.querySelector("#test-results");
  _historyList = root.querySelector("#test-history-list");

  // Click dropzone to browse
  _dropzone.addEventListener("click", (e) => {
    if (e.target === _fileClear || _fileClear.contains(e.target)) return;
    _fileInput.click();
  });

  // File input change
  _fileInput.addEventListener("change", () => {
    const file = _fileInput.files[0];
    if (file) setFile(file);
  });

  // Clear file
  _fileClear.addEventListener("click", (e) => {
    e.stopPropagation();
    clearFile();
  });

  // Drag and drop
  _dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    _dropzone.classList.add("drag-over");
  });
  _dropzone.addEventListener("dragleave", () => {
    _dropzone.classList.remove("drag-over");
  });
  _dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    _dropzone.classList.remove("drag-over");
    const file = e.dataTransfer?.files[0];
    if (file) setFile(file);
  });

  _runBtn.addEventListener("click", runTest);
  _cancelBtn.addEventListener("click", cancelTest);

  _tenantUnsub = TenantContext.onChange(() => updateRunButton());
  updateRunButton();
}

export function unmount(_root) {
  cancelTest();
  if (_tenantUnsub) {
    _tenantUnsub();
    _tenantUnsub = null;
  }
  if (_root) _root.replaceChildren();
}

function setFile(file) {
  // Transfer to the real input if dropped
  const dt = new DataTransfer();
  dt.items.add(file);
  _fileInput.files = dt.files;

  _fileName.textContent = file.name;
  _dropzoneIdle.classList.add("hidden");
  _dropzoneSelected.classList.remove("hidden");
  updateRunButton();
}

function clearFile() {
  _fileInput.value = "";
  _dropzoneIdle.classList.remove("hidden");
  _dropzoneSelected.classList.add("hidden");
  updateRunButton();
}

function updateRunButton() {
  _runBtn.disabled = !(TenantContext.getTenantId() && _fileInput.files.length > 0);
}

async function runTest() {
  const tenantId = TenantContext.getTenantId();
  const file = _fileInput.files[0];
  if (!tenantId || !file) return;

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
      null,
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
    updateRunButton();
    _abortController = null;
  }
}

function cancelTest() {
  if (_abortController) _abortController.abort();
}

function updateElapsed() {
  if (!_startTime) return;
  const seconds = Math.floor((Date.now() - _startTime) / 1000);
  _elapsed.textContent = `Processing… ${seconds}s`;
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
