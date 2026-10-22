import * as ExtractionTestRunnerService from "../../services/extraction-test-runner.js";
import * as DocumentsService from "../../services/documents.js";
import * as TenantContext from "../../utils/tenant-context.js";
import { createElapsedTimer } from "../../../../shared/utils/elapsed-timer.js";
import { renderExtractedData } from "../../../../shared/components/document-viewer.js";
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import html from "./extraction-test-runner.html";

const tmpl = tpl(html);

const STATUS_LABELS = {
  success: "Extracted",
  no_custom_blueprint_matched: "No blueprint",
  not_started: "Pending",
  started: "Processing",
  failed: "Failed",
};

let _root;
let _tenantUnsub;
let _runBtn, _fileInput, _dropzone, _dropzoneIdle, _dropzoneSelected, _fileName, _fileClear;
let _statusEl,
  _resultsEl,
  _resultHeaderEl,
  _resultFieldsEl,
  _emptyEl,
  _historyEl,
  _historyEmptyEl,
  _backBtn;
let _selectedFile = null;
let _abortController = null;
let _elapsedTimer = null;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  _runBtn = root.querySelector("#extraction-test-run-btn");
  _fileInput = root.querySelector("#extraction-test-file");
  _dropzone = root.querySelector("#extraction-test-dropzone");
  _dropzoneIdle = root.querySelector("#extraction-test-dropzone-idle");
  _dropzoneSelected = root.querySelector("#extraction-test-dropzone-selected");
  _fileName = root.querySelector("#extraction-test-file-name");
  _fileClear = root.querySelector("#extraction-test-file-clear");
  _statusEl = root.querySelector("#extraction-test-status");
  _resultsEl = root.querySelector("#extraction-test-results");
  _resultHeaderEl = root.querySelector("#extraction-test-result-header");
  _resultFieldsEl = root.querySelector("#extraction-test-result-fields");
  _emptyEl = root.querySelector("#extraction-test-empty");
  _historyEl = root.querySelector("#extraction-test-history");
  _historyEmptyEl = root.querySelector("#extraction-test-history-empty");
  _backBtn = root.querySelector("#extraction-test-back");
  _backBtn.addEventListener("click", _showList);

  TenantContext.mountSelect(root.querySelector("#tenant-select"), {
    placeholder: "- Select tenant -",
  });
  _tenantUnsub = TenantContext.onChange(() => {
    _updateRunBtn();
    _resultsEl.classList.add("hidden");
    _emptyEl.classList.remove("hidden");
    _loadHistory();
  });

  _dropzone.addEventListener("click", (e) => {
    if (e.target === _fileClear || _fileClear.contains(e.target)) {
      return;
    }
    _fileInput.click();
  });
  _fileInput.addEventListener("change", () => {
    if (_fileInput.files[0]) {
      _setFile(_fileInput.files[0]);
    }
  });
  _fileClear.addEventListener("click", (e) => {
    e.stopPropagation();
    _clearFile();
  });
  _dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    _dropzone.classList.add("drag-over");
  });
  _dropzone.addEventListener("dragleave", () => _dropzone.classList.remove("drag-over"));
  _dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    _dropzone.classList.remove("drag-over");
    if (e.dataTransfer?.files[0]) {
      _setFile(e.dataTransfer.files[0]);
    }
  });

  _runBtn.addEventListener("click", _runTest);

  _loadHistory();
}

export function unmount(root) {
  _abortController?.abort();
  _abortController = null;
  _elapsedTimer?.stop();
  _elapsedTimer = null;
  _selectedFile = null;
  if (_tenantUnsub) {
    _tenantUnsub();
    _tenantUnsub = null;
  }
  const sel = root.querySelector("#tenant-select");
  if (sel) {
    TenantContext.unmountSelect(sel);
  }
  root.replaceChildren();
}

function _setFile(file) {
  _selectedFile = file;
  _fileName.textContent = file.name;
  _dropzoneIdle.classList.add("hidden");
  _dropzoneSelected.classList.remove("hidden");
  _updateRunBtn();
}

function _clearFile() {
  _selectedFile = null;
  _fileInput.value = "";
  _dropzoneIdle.classList.remove("hidden");
  _dropzoneSelected.classList.add("hidden");
  _updateRunBtn();
}

function _updateRunBtn() {
  _runBtn.disabled = !TenantContext.getTenantId() || !_selectedFile;
}

async function _runTest() {
  const tenantId = TenantContext.getTenantId();
  if (!tenantId || !_selectedFile) {
    return;
  }

  _abortController?.abort();
  _abortController = new AbortController();

  _runBtn.disabled = true;
  _emptyEl.classList.add("hidden");
  _resultsEl.classList.add("hidden");
  _setStatus("Running extraction… 0s");
  _elapsedTimer = createElapsedTimer((s) => _setStatus(`Running extraction… ${s}s`));
  _elapsedTimer.start();

  try {
    const file = _selectedFile;
    _clearFile();
    const result = await ExtractionTestRunnerService.run(file, tenantId, _abortController.signal);
    const doc = await DocumentsService.get(result.jobId, { includeExtractedData: true });
    _setStatus(null);
    _renderResults(doc);
    _showDetail();
    await _loadHistory(result.jobId);
  } catch (e) {
    if (e.name === "AbortError") {
      return;
    }
    _setStatus(`Error: ${e instanceof Error ? e.message : JSON.stringify(e)}`, true);
  } finally {
    _elapsedTimer?.stop();
    _elapsedTimer = null;
    _runBtn.disabled = false;
    _updateRunBtn();
  }
}

async function _loadHistory(activeJobId = null) {
  const tenantId = TenantContext.getTenantId();
  if (!tenantId) {
    _historyEl.replaceChildren();
    _historyEmptyEl.classList.remove("hidden");
    return;
  }

  try {
    const resp = await DocumentsService.list({ tenantId, isTestRun: true, limit: 20 });
    const docs = resp.documents || [];
    _historyEl.replaceChildren();

    if (!docs.length) {
      _historyEmptyEl.classList.remove("hidden");
      return;
    }

    _historyEmptyEl.classList.add("hidden");
    for (const doc of docs) {
      const name = doc.fileName || doc.jobId?.slice(0, 8);
      const statusLabel = STATUS_LABELS[doc.processStatus] ?? doc.processStatus ?? "—";
      const li = h(
        "li",
        {
          className: `doc-list-item${doc.jobId === activeJobId ? " active" : ""}`,
          "data-job-id": doc.jobId,
        },
        h("div", { className: "doc-list-name" }, name),
        h("span", { className: "badge badge-neutral" }, statusLabel),
      );
      li.addEventListener("click", () => {
        _historyEl
          .querySelectorAll(".doc-list-item")
          .forEach((el) => el.classList.remove("active"));
        li.classList.add("active");
        _loadResult(doc.jobId);
      });
      _historyEl.appendChild(li);
    }
  } catch {
    // history is optional — fail silently
  }
}

async function _loadResult(jobId) {
  _emptyEl.classList.add("hidden");
  _resultsEl.classList.add("hidden");
  _setStatus("Loading…");

  try {
    const doc = await DocumentsService.get(jobId, { includeExtractedData: true });
    _setStatus(null);
    _renderResults(doc);
    _showDetail();
  } catch (e) {
    _setStatus(`Error: ${e.message}`, true);
  }
}

function _showDetail() {
  _root.querySelector(".filter-layout").classList.add("mobile-detail-active");
}

function _showList() {
  _root.querySelector(".filter-layout").classList.remove("mobile-detail-active");
}

function _setStatus(message, isError = false) {
  if (!message) {
    _statusEl.style.display = "none";
    return;
  }
  _statusEl.style.display = "";
  _statusEl.textContent = message;
  _statusEl.className = isError ? "extraction-test-error" : "extraction-test-processing";
}

function _renderResults(result) {
  const fileName = result.fileName ?? result.file_name ?? "Unknown file";
  const processingTime = result.totalProcessingTimeSeconds ?? result.total_processing_time_seconds;
  const timeStr = processingTime != null ? `${processingTime.toFixed(1)}s` : null;
  const createdAt = result.createdAt ?? result.created_at;
  const dateStr = createdAt ? new Date(createdAt).toLocaleString() : null;

  _resultHeaderEl.replaceChildren(
    h("span", { className: "extraction-result-filename" }, fileName),
    h(
      "div",
      { className: "extraction-result-meta" },
      ...(timeStr
        ? [h("span", { className: "extraction-result-time" }, `Elapsed: ${timeStr}`)]
        : []),
      ...(dateStr
        ? [h("span", { className: "extraction-result-date" }, `Extracted: ${dateStr}`)]
        : []),
    ),
  );

  const fields = result.extractedData?.fields ?? result.fields ?? {};
  // eslint-disable-next-line no-unsanitized/property -- renderExtractedData escapes all values
  _resultFieldsEl.innerHTML = renderExtractedData(fields, { revealed: true, maskable: false });
  if (!_resultFieldsEl.innerHTML) {
    _resultFieldsEl.innerHTML = '<p class="empty-state">No fields extracted.</p>';
  }
  _resultsEl.classList.remove("hidden");
}
