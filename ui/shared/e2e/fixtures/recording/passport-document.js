// Synthetic US passport fixture used by the extraction test runner video spec.
//
// FIELDS is the single source of truth: it drives the SVG preview image so
// the rendered document looks realistic without containing real PII.

export const W = 850;
export const H = 600;

export const JOB_ID = "b1686d79-41a9-41f6-af39-28e1d3488baf";
export const TENANT_ID = "acme-corp";

export const FIELDS = [
  {
    name: "given_name",
    displayName: "Given Name",
    value: "ALEX",
    confidence: 0.98,
    x: 40,
    y: 160,
    w: 360,
    h: 60,
    vx: 54,
    vy: 196,
    vw: 200,
    vh: 26,
  },
  {
    name: "last_name",
    displayName: "Last Name",
    value: "RIVERA",
    confidence: 0.98,
    x: 420,
    y: 160,
    w: 360,
    h: 60,
    vx: 434,
    vy: 196,
    vw: 200,
    vh: 26,
  },
  {
    name: "date_of_birth",
    displayName: "Date of Birth",
    value: "1963-08-09",
    confidence: 0.98,
    x: 40,
    y: 240,
    w: 360,
    h: 60,
    vx: 54,
    vy: 276,
    vw: 180,
    vh: 26,
  },
  {
    name: "place_of_birth",
    displayName: "Place of Birth",
    value: "NEW JERSEY U.S.A.",
    confidence: 0.95,
    x: 420,
    y: 240,
    w: 360,
    h: 60,
    vx: 434,
    vy: 276,
    vw: 260,
    vh: 26,
  },
  {
    name: "date_of_issue",
    displayName: "Date of Issue",
    value: "2007-05-09",
    confidence: 0.91,
    x: 40,
    y: 320,
    w: 360,
    h: 60,
    vx: 54,
    vy: 356,
    vw: 180,
    vh: 26,
  },
  {
    name: "expiration_date",
    displayName: "Expiration Date",
    value: "2017-05-08",
    confidence: 0.98,
    x: 420,
    y: 320,
    w: 360,
    h: 60,
    vx: 434,
    vy: 356,
    vw: 180,
    vh: 26,
  },
  {
    name: "document_number",
    displayName: "Document Number",
    value: "000000003",
    confidence: 0.96,
    x: 40,
    y: 400,
    w: 360,
    h: 60,
    vx: 54,
    vy: 436,
    vw: 160,
    vh: 26,
  },
  {
    name: "passport_type",
    displayName: "Passport Type",
    value: "P",
    confidence: 0.98,
    x: 420,
    y: 400,
    w: 180,
    h: 60,
    vx: 434,
    vy: 436,
    vw: 40,
    vh: 26,
  },
  {
    name: "sex",
    displayName: "Sex",
    value: "F",
    confidence: 1.0,
    x: 620,
    y: 400,
    w: 160,
    h: 60,
    vx: 634,
    vy: 436,
    vw: 30,
    vh: 26,
  },
];

function documentSvg() {
  const cells = FIELDS.map(
    (f) => `
      <rect x="${f.x}" y="${f.y}" width="${f.w}" height="${f.h}"
            fill="#ffffff" stroke="#c7ccd4" stroke-width="1.5"/>
      <text x="${f.x + 14}" y="${f.y + 22}" font-family="Helvetica, Arial, sans-serif"
            font-size="11" fill="#6b7280">${f.displayName}</text>
      <text x="${f.vx}" y="${f.vy + 20}" font-family="Helvetica, Arial, sans-serif"
            font-size="20" font-weight="600" fill="#111827">${f.value}</text>`,
  ).join("");

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    <rect width="${W}" height="${H}" fill="#e8edf5"/>
    <rect x="20" y="20" width="${W - 40}" height="${H - 40}" fill="#ffffff" stroke="#d1d5db" stroke-width="2"/>
    <rect x="20" y="20" width="${W - 40}" height="110" fill="#1e3a5f"/>
    <text x="40" y="68" font-family="Helvetica, Arial, sans-serif" font-size="28" font-weight="700" fill="#ffffff">UNITED STATES OF AMERICA</text>
    <text x="40" y="100" font-family="Helvetica, Arial, sans-serif" font-size="18" fill="#a8c0e0">PASSPORT</text>
    ${cells}
    <rect x="40" y="490" width="${W - 80}" height="50" fill="#f3f4f6" rx="2"/>
    <text x="54" y="520" font-family="Courier New, monospace" font-size="13" fill="#374151">P&lt;USARIVERA&lt;&lt;ALEX&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</text>
  </svg>`;
}

export function previewDataUrl() {
  return (
    "data:image/svg+xml;charset=utf-8," + encodeURIComponent(documentSvg())
  );
}

export function apiFields() {
  const out = {};
  for (const f of FIELDS) {
    out[f.name] = {
      value: f.value,
      confidence: f.confidence,
      displayName: f.displayName,
      geometry: [
        {
          page: 1,
          boundingBox: {
            left: f.vx / W,
            top: f.vy / H,
            width: f.vw / W,
            height: f.vh / H,
          },
        },
      ],
    };
  }
  return out;
}

export const COMPLETED_DOC = {
  jobId: JOB_ID,
  fileName: "us-passport.jpg",
  contentType: "image/jpeg",
  processStatus: "success",
  matchedDocumentClass: "US-passports",
  createdAt: "2026-10-21T19:16:50.115856+00:00",
  totalProcessingTimeSeconds: 13.88,
  fields: apiFields(),
};
