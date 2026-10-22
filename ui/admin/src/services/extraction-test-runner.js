import { adminClient } from "./http.js";

const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 120000; // 2 minutes max

export async function run(file, tenantId, signal) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("tenant_id", tenantId);

  const baseUrl = adminClient.getBaseUrl();
  const session = JSON.parse(sessionStorage.getItem("docai_console_session") || "{}");
  const token = session.idToken || "";

  const startRes = await fetch(`${baseUrl}/v1/admin/extraction-test`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
    signal,
  });

  if (!startRes.ok) {
    const body = await startRes.json().catch(() => ({ detail: startRes.statusText }));
    throw new Error(body.detail || "Failed to start test");
  }

  const { jobId } = await startRes.json();

  // Poll for results with timeout
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (signal?.aborted) {
      throw new DOMException("Aborted", "AbortError");
    }

    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));

    if (signal?.aborted) {
      throw new DOMException("Aborted", "AbortError");
    }

    const pollRes = await fetch(
      `${baseUrl}/v1/admin/extraction-test/${jobId}?include_extracted_data=true`,
      {
        headers: { Authorization: `Bearer ${token}` },
        signal,
      },
    );

    if (!pollRes.ok) {
      throw new Error("Failed to check test status");
    }

    const result = await pollRes.json();

    if (result.isCompleted) {
      if (result.isFailed) {
        throw new Error(result.message || "Extraction failed");
      }
      return result;
    }
    // Otherwise keep polling
  }

  throw new Error("Still processing — check Recent Test Runs for the result");
}
