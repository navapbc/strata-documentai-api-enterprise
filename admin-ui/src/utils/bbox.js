/**
 * Bounding box geometry utilities.
 * Pure functions for IoU computation and overlapping box merging.
 */

/**
 * Compute Intersection over Union for two boxes.
 * Each box: { left, top, width, height }
 */
export function computeIoU(a, b) {
  const ax2 = a.left + a.width,
    ay2 = a.top + a.height;
  const bx2 = b.left + b.width,
    by2 = b.top + b.height;
  const ix1 = Math.max(a.left, b.left),
    iy1 = Math.max(a.top, b.top);
  const ix2 = Math.min(ax2, bx2),
    iy2 = Math.min(ay2, by2);
  if (ix2 <= ix1 || iy2 <= iy1) return 0;
  const intersection = (ix2 - ix1) * (iy2 - iy1);
  const areaA = a.width * a.height;
  const areaB = b.width * b.height;
  return intersection / (areaA + areaB - intersection);
}

/**
 * Merge overlapping boxes (IoU > 0.5) into union rects.
 * Input: [{ left, top, width, height, fieldName, fieldType }]
 * Output: [{ left, top, width, height, fields: [{ fieldName, fieldType }] }]
 */
export function mergeOverlappingBoxes(boxes) {
  const groups = boxes.map((b) => ({
    left: b.left,
    top: b.top,
    width: b.width,
    height: b.height,
    fields: [{ fieldName: b.fieldName, fieldType: b.fieldType }],
  }));

  let merged = true;
  while (merged) {
    merged = false;
    for (let i = 0; i < groups.length; i++) {
      for (let j = i + 1; j < groups.length; j++) {
        if (computeIoU(groups[i], groups[j]) > 0.5) {
          const a = groups[i],
            b = groups[j];
          const x1 = Math.min(a.left, b.left);
          const y1 = Math.min(a.top, b.top);
          const x2 = Math.max(a.left + a.width, b.left + b.width);
          const y2 = Math.max(a.top + a.height, b.top + b.height);
          groups[i] = {
            left: x1,
            top: y1,
            width: x2 - x1,
            height: y2 - y1,
            fields: [...a.fields, ...b.fields],
          };
          groups.splice(j, 1);
          merged = true;
          break;
        }
      }
      if (merged) break;
    }
  }
  return groups;
}
