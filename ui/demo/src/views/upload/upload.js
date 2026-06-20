import * as Session from "../../../../shared/utils/session.js";
import * as Toast from "../../../../shared/utils/toast.js";
import * as Documents from "../../services/documents.js";
import { h } from "../../../../shared/utils/dom.js";
import { tpl } from "../../../../shared/utils/tpl.js";
import { formatDate, esc } from "../../../../shared/utils/helpers.js";
import {
  extractGeometry,
  renderBboxOverlay,
  renderExtractedData,
  markFieldsWithGeometry,
  renderPreview,
  linkFieldHighlighting,
} from "../../../../shared/components/document-viewer.js";
import html from "./upload.html";

const tmpl = tpl(html);

const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 120000;

let _root = null;
let _fileInput, _runBtn, _dropzone, _dropzoneIdle, _dropzoneSelected;
let _fileName, _fileClear, _elapsed, _results, _previewPanel, _detailPanel, _historyList;
let _selectedFile = null;
let _abortController = null;
let _startTime = null;
let _elapsedTimer = null;
let _onLogout = null;

export function onLogout(callback) {
  _onLogout = callback;
}

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  root.querySelector("#demo-user-email").textContent = Session.getEmail() || "";
  root.querySelector("#demo-logout-btn").addEventListener("click", () => {
    if (_onLogout) _onLogout();
  });

  _fileInput = root.querySelector("#demo-file-input");
  _runBtn = root.querySelector("#demo-run-btn");
  _dropzone = root.querySelector("#demo-dropzone");
  _dropzoneIdle = root.querySelector("#demo-dropzone-idle");
  _dropzoneSelected = root.querySelector("#demo-dropzone-selected");
  _fileName = root.querySelector("#demo-file-name");
  _fileClear = root.querySelector("#demo-file-clear");
  _elapsed = root.querySelector("#demo-elapsed");
  _results = root.querySelector("#demo-results");
  _previewPanel = root.querySelector("#demo-preview-panel");
  _detailPanel = root.querySelector("#demo-detail-panel");
  _historyList = root.querySelector("#demo-history-list");

  // Hover a field row -> highlight its bounding box in the preview.
  linkFieldHighlighting(_results, _previewPanel);

  _dropzone.addEventListener("click", (e) => {
    if (e.target === _fileClear || _fileClear.contains(e.target)) return;
    _fileInput.click();
  });

  _fileInput.addEventListener("change", () => {
    if (_fileInput.files[0]) setFile(_fileInput.files[0]);
  });

  _fileClear.addEventListener("click", (e) => {
    e.stopPropagation();
    clearFile();
  });

  _dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    _dropzone.classList.add("drag-over");
  });
  _dropzone.addEventListener("dragleave", () => _dropzone.classList.remove("drag-over"));
  _dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    _dropzone.classList.remove("drag-over");
    if (e.dataTransfer?.files[0]) setFile(e.dataTransfer.files[0]);
  });

  _runBtn.addEventListener("click", runExtraction);
  loadHistory();
}

export function unmount() {
  if (_abortController) _abortController.abort();
  if (_elapsedTimer) clearInterval(_elapsedTimer);
}

function setFile(file) {
  // Track the selected file directly rather than round-tripping through
  // _fileInput.files (which would require DataTransfer). The demo reads the
  // file in JS and uploads via fetch, so the native input never needs it.
  _selectedFile = file;
  _fileName.textContent = file.name;
  _dropzoneIdle.classList.add("hidden");
  _dropzoneSelected.classList.remove("hidden");
  _runBtn.disabled = false;
}

function clearFile() {
  _selectedFile = null;
  _fileInput.value = "";
  _dropzoneIdle.classList.remove("hidden");
  _dropzoneSelected.classList.add("hidden");
  _runBtn.disabled = true;
}

async function loadHistory() {
  if (!_historyList) return;
  _historyList.replaceChildren(h("li", { className: "empty-state" }, "Loading documents…"));
  try {
    const resp = await Documents.list({ isDemo: true, limit: 20 });
    const docs = resp.documents || [];
    _historyList.replaceChildren();
    if (!docs.length) {
      _historyList.appendChild(h("li", { className: "empty-state" }, "No documents yet"));
      return;
    }
    for (const doc of docs) {
      const li = h(
        "li",
        { className: "demo-history-item" },
        h("span", { className: "demo-history-name" }, doc.fileName || doc.jobId?.slice(0, 8)),
        h(
          "span",
          { className: "demo-history-meta" },
          `${doc.processStatus} · ${formatDate(doc.createdAt)}`,
        ),
      );
      li.addEventListener("click", () => loadDocument(doc.jobId));
      _historyList.appendChild(li);
    }
  } catch {
    // History is optional - clear the loading placeholder and stay quiet.
    _historyList.replaceChildren();
  }
}

async function runExtraction() {
  const file = _selectedFile;
  if (!file) return;

  _runBtn.disabled = true;
  _elapsed.classList.remove("hidden");
  _results.classList.add("hidden");
  _startTime = Date.now();
  _abortController = new AbortController();
  _elapsedTimer = setInterval(updateElapsed, 1000);
  updateElapsed();

  try {
    const { jobId } = await Documents.upload(file);
    const result = await pollForCompletion(jobId);
    renderResults(result);
    loadPreview(result);
    loadHistory();
  } catch (e) {
    if (e.name !== "AbortError") {
      Toast.show(`Extraction failed: ${e.message}`);
    }
  } finally {
    clearInterval(_elapsedTimer);
    _elapsedTimer = null;
    _elapsed.classList.add("hidden");
    _runBtn.disabled = !_selectedFile;
    _abortController = null;
  }
}

async function pollForCompletion(jobId) {
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  const PENDING = new Set([
    "not_started",
    "started",
    "pending_image_optimization",
    "pending_upload",
  ]);

  while (Date.now() < deadline) {
    if (_abortController?.signal.aborted) throw new DOMException("Aborted", "AbortError");
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    if (_abortController?.signal.aborted) throw new DOMException("Aborted", "AbortError");

    const doc = await Documents.get(jobId, {
      includeExtractedData: true,
      includeBoundingBox: true,
    });
    if (!PENDING.has(doc.processStatus)) return doc;
  }

  throw new Error("Timed out waiting for results");
}

async function loadDocument(jobId) {
  _results.classList.add("hidden");
  _previewPanel.innerHTML = '<p class="empty-state">Loading…</p>';
  try {
    const doc = await Documents.get(jobId, {
      includeExtractedData: true,
      includeBoundingBox: true,
    });
    renderResults(doc);
    loadPreview(doc);
  } catch (e) {
    Toast.show(`Failed to load document: ${e.message}`);
  }
}

function updateElapsed() {
  if (!_startTime) return;
  _elapsed.textContent = `Processing… ${Math.floor((Date.now() - _startTime) / 1000)}s`;
}

let _resizeObserver = null;

function renderResults(doc) {
  _results.classList.remove("hidden");

  const tableHtml = renderExtractedData(doc.fields, { maskable: false });
  const body = tableHtml || '<p class="empty-state">No fields extracted</p>';
  const header = doc.matchedBlueprint
    ? `<p class="demo-matched">Blueprint: ${esc(doc.matchedBlueprint)}</p>`
    : "";
  // eslint-disable-next-line no-unsanitized/property -- values escaped in renderExtractedData/esc
  _results.innerHTML = header + body;
}

async function loadPreview(doc) {
  _previewPanel.replaceChildren();
  if (_resizeObserver) {
    _resizeObserver.disconnect();
    _resizeObserver = null;
  }

  let previewUrl = null;
  try {
    const resp = await Documents.getPreviewUrl(doc.jobId);
    previewUrl = resp.url;
  } catch {
    // no preview available
  }

  if (!previewUrl) {
    _previewPanel.innerHTML = '<p class="empty-state">No preview available</p>';
    return;
  }

  renderPreview(_previewPanel, {
    url: previewUrl,
    contentType: doc.contentType,
    watermarkEmail: Session.getEmail() || "",
  });

  const geo = extractGeometry(doc.fields || {});
  if (geo) {
    _resizeObserver = renderBboxOverlay(_previewPanel, geo);
  }
  markFieldsWithGeometry(_results, geo);
}
