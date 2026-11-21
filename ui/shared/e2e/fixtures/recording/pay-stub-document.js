// Synthetic pay stub fixture for the trailer specs.
//
// Mirrors the shape of w2-document.js: FIELDS is the single source of truth and
// drives both the SVG preview image and the normalised bounding boxes, so the
// overlay rects land exactly on the printed values. All names and amounts are
// invented. The employee ID is deliberately low-confidence so the results table
// shows a flagged (red) field for the demo.

export const JOB_ID = "demo-paystub-0001";

export const W = 850;
export const H = 1100;

export const FIELDS = [
  {
    name: "employerName",
    label: "Employer",
    displayName: "Employer name",
    value: "Riverbend Logistics LLC",
    fieldType: "string",
    confidence: 0.981,
    x: 40,
    y: 150,
    w: 400,
    h: 78,
    vx: 54,
    vy: 200,
    vw: 300,
    vh: 30,
  },
  {
    name: "employeeName",
    label: "Employee",
    displayName: "Employee name",
    value: "Jordan A. Rivera",
    fieldType: "string",
    confidence: 0.974,
    x: 40,
    y: 250,
    w: 400,
    h: 78,
    vx: 54,
    vy: 300,
    vw: 220,
    vh: 30,
  },
  {
    name: "employeeId",
    label: "Employee ID",
    displayName: "Employee ID",
    value: "EMP-20417",
    fieldType: "string",
    confidence: 0.62,
    x: 40,
    y: 350,
    w: 400,
    h: 66,
    vx: 54,
    vy: 392,
    vw: 150,
    vh: 30,
  },
  {
    name: "payPeriod",
    label: "Pay period",
    displayName: "Pay period",
    value: "11/01/2026 - 11/15/2026",
    fieldType: "string",
    confidence: 0.963,
    x: 460,
    y: 150,
    w: 350,
    h: 78,
    vx: 474,
    vy: 200,
    vw: 290,
    vh: 30,
  },
  {
    name: "grossPay",
    label: "Gross pay",
    displayName: "Gross pay",
    value: "$3,250.00",
    fieldType: "currency",
    confidence: 0.992,
    x: 460,
    y: 250,
    w: 350,
    h: 78,
    vx: 474,
    vy: 300,
    vw: 140,
    vh: 30,
  },
  {
    name: "netPay",
    label: "Net pay",
    displayName: "Net pay",
    value: "$2,418.37",
    fieldType: "currency",
    confidence: 0.987,
    x: 460,
    y: 350,
    w: 350,
    h: 66,
    vx: 474,
    vy: 392,
    vw: 140,
    vh: 30,
  },
];

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
    <text x="40" y="78" font-family="Helvetica, Arial, sans-serif" font-size="30" font-weight="700" fill="#111827">Earnings Statement</text>
    <text x="40" y="106" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="#6b7280">Pay stub · Synthetic sample</text>
    ${cells}
    <text x="40" y="480" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#9ca3af">Synthetic document for demonstration. No real person or employer.</text>
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
  fileName: "pay-stub-nov-2026.png",
  contentType: "image/png",
  processStatus: "success",
  matchedBlueprint: "Pay Stub",
  createdAt: "2026-11-20T15:55:00Z",
  fields: apiFields(),
};
