import { adminClient } from "../../../shared/services/http.js";
import { STORAGE_KEY } from "../../../shared/utils/session.js";

export async function list({ limit, cursor } = {}) {
  const params = new URLSearchParams();
  if (limit) {
    params.set("limit", String(limit));
  }
  if (cursor) {
    params.set("cursor", cursor);
  }
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/demo/documents${qs}`);
}

export async function get(
  jobId,
  { includeExtractedData = false, includeBoundingBox = false } = {},
) {
  const params = new URLSearchParams();
  if (includeExtractedData) {
    params.set("include_extracted_data", "true");
  }
  if (includeBoundingBox) {
    params.set("include_bounding_box", "true");
  }
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/demo/documents/${encodeURIComponent(jobId)}${qs}`);
}

export async function getPreviewUrl(jobId) {
  return adminClient.request("GET", `/v1/demo/documents/${encodeURIComponent(jobId)}/preview`);
}

export async function upload(file, signal) {
  const baseUrl = adminClient.getBaseUrl();
  const session = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "{}");
  const token = session.idToken || "";

  // Non-native types (HEIC, WebP, TIFF, etc.) need server-side conversion —
  // fall back to the direct upload endpoint which handles that.
  // TODO: once the processor converts after upload, presigned can accept
  // REQUIRES_CONVERSION types too. Then drop NATIVE_TYPES and uploadDirect,
  // and always use presign (keep a list only for the picker's `accept`).
  const NATIVE_TYPES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
  ];
  if (!file.type || !NATIVE_TYPES.includes(file.type)) {
    return uploadDirect(baseUrl, token, file);
  }

  const MAX_SIZE_BYTES = 524_288_000; // 500 MB — matches BDA_MAX_DOCUMENT_FILE_SIZE_BYTES
  if (file.size > MAX_SIZE_BYTES) {
    const mb = (MAX_SIZE_BYTES / 1024 / 1024).toFixed(0);
    throw new Error(`File too large. Maximum size is ${mb} MB.`);
  }

  // Step 1: get a presigned POST URL from the API
  const presignForm = new FormData();
  presignForm.append("filename", file.name);
  presignForm.append("content_type", file.type);
  const presignRes = await fetch(`${baseUrl}/v1/demo/documents/presigned-url`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: presignForm,
    signal,
  });
  if (!presignRes.ok) {
    const body = await presignRes.json().catch(() => ({ detail: presignRes.statusText }));
    throw new Error(body.detail || "Failed to initiate upload");
  }
  const { uploadUrl, fields, jobId } = await presignRes.json();

  // Step 2: POST directly to S3 — bypasses API Gateway size limits
  const s3Form = new FormData();
  for (const [k, v] of Object.entries(fields)) {
    s3Form.append(k, v);
  }
  s3Form.append("file", file);

  const s3Res = await fetch(uploadUrl, { method: "POST", body: s3Form, signal });
  if (!s3Res.ok) {
    throw new Error(`Upload to storage failed (${s3Res.status})`);
  }

  return { jobId };
}

async function uploadDirect(baseUrl, token, file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${baseUrl}/v1/demo/documents`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || "Upload failed");
  }
  return res.json();
}
