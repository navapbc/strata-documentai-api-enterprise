// Shared synthetic W-2 fixture used by both the demo and admin video specs.
//
// The FIELDS array is the single source of truth: it drives the SVG preview
// image AND the normalised bounding boxes, so overlay rects always land exactly
// on the printed values.

export const W = 850;
export const H = 1100;

export const FIELDS = [
  { name: "employerName", label: "Employer", displayName: "Employer name",
    value: "Acme Manufacturing, Inc.", fieldType: "string", confidence: 0.985,
    x: 40, y: 150, w: 400, h: 78, vx: 54, vy: 200, vw: 300, vh: 30 },
  { name: "employeeName", label: "Employee", displayName: "Employee name",
    value: "Jordan A. Rivera", fieldType: "string", confidence: 0.972,
    x: 40, y: 250, w: 400, h: 78, vx: 54, vy: 300, vw: 220, vh: 30 },
  { name: "socialSecurityNumber", label: "Employee SSN", displayName: "SSN",
    value: "123-45-6789", fieldType: "string", confidence: 0.664,
    x: 40, y: 350, w: 400, h: 66, vx: 54, vy: 392, vw: 180, vh: 30 },
  { name: "wages", label: "1  Wages, tips, other comp.", displayName: "Wages (Box 1)",
    value: "$84,500.00", fieldType: "currency", confidence: 0.991,
    x: 460, y: 150, w: 350, h: 78, vx: 474, vy: 200, vw: 160, vh: 30 },
  { name: "federalIncomeTaxWithheld", label: "2  Federal income tax withheld",
    displayName: "Federal tax withheld",
    value: "$12,300.00", fieldType: "currency", confidence: 0.958,
    x: 460, y: 250, w: 350, h: 78, vx: 474, vy: 300, vw: 160, vh: 30 },
  { name: "taxYear", label: "Tax year", displayName: "Tax year",
    value: "2025", fieldType: "integer", confidence: 0.999,
    x: 460, y: 350, w: 350, h: 66, vx: 474, vy: 392, vw: 90, vh: 30 },
];

export const JOB_ID = "demo-w2-0001";

function documentSvg() {
  const cells = FIELDS.map(
    (f) => `
      <rect x="${f.x}" y="${f.y}" width="${f.w}" height="${f.h}"
            fill="#ffffff" stroke="#c7ccd4" stroke-width="1.5"/>
      <text x="${f.x + 14}" y="${f.y + 26}" font-family="Helvetica, Arial, sans-serif"
            font-size="13" fill="#6b7280">${f.label}</text>
      <text x="${f.vx}" y="${f.vy + 22}" font-family="Helvetica, Arial, sans-serif"
            font-size="24" font-weight="600" fill="#111827">${f.value}</text>`,
  ).join("");

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    <rect width="${W}" height="${H}" fill="#f3f4f6"/>
    <rect x="20" y="20" width="${W - 40}" height="${H - 40}" fill="#ffffff" stroke="#d1d5db" stroke-width="2"/>
    <text x="40" y="78" font-family="Helvetica, Arial, sans-serif" font-size="30" font-weight="700" fill="#111827">Form W-2</text>
    <text x="40" y="106" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="#6b7280">Wage and Tax Statement · 2025</text>
    ${cells}
    <text x="40" y="480" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#9ca3af">This information is being furnished to the Internal Revenue Service.</text>
  </svg>`;
}

export function previewDataUrl() {
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(documentSvg());
}

export function apiFields() {
  const out = {};
  for (const f of FIELDS) {
    out[f.name] = {
      value: f.value,
      confidence: f.confidence,
      fieldType: f.fieldType,
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
  fileName: "employee-w2-2025.png",
  contentType: "image/png",
  processStatus: "success",
  matchedBlueprint: "US Tax Form W-2",
  createdAt: "2026-07-16T15:55:00Z",
  fields: apiFields(),
};
