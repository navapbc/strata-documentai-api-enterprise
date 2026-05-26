import { adminClient } from "./http.js";

const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 120000; // 2 minutes max

export async function run(file, tenantId, category, documentType, signal) {
  // Start the test
  const formData = new FormData();
  formData.append("file", file);
  if (tenantId) formData.append("tenant_id", tenantId);
  formData.append("document_category", category);
  if (documentType) formData.append("document_type", documentType);

  const baseUrl = adminClient.getBaseUrl();
  const session = JSON.parse(sessionStorage.getItem("docai_console_session") || "{}");
  const token = session.idToken || "";

  const startRes = await fetch(`${baseUrl}/v1/admin/blueprints/test`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
    signal,
  });

  if (!startRes.ok) {
    const body = await startRes.json().catch(() => ({ detail: startRes.statusText }));
    throw new Error(body.detail || "Failed to start test");
  }

  const { testId } = await startRes.json();

  // Poll for results with timeout
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");

    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));

    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");

    const pollRes = await fetch(`${baseUrl}/v1/admin/blueprints/test/${testId}`, {
      headers: { Authorization: `Bearer ${token}` },
      signal,
    });

    if (!pollRes.ok) {
      throw new Error("Failed to check test status");
    }

    const result = await pollRes.json();

    if (result.status === "COMPLETED") return result;
    if (result.status === "FAILED") throw new Error(result.error || "Extraction failed");
    // Otherwise keep polling (PROCESSING)
  }

  throw new Error("Test timed out - BDA processing took too long");
}
