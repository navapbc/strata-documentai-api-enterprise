export function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString();
}

export function esc(str) {
  const el = document.createElement("span");
  el.textContent = str || "";
  return el.innerHTML;
}
