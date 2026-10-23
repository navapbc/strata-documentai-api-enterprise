import { PRESENTATION_MODE_KEY } from "./session.js";

export const MASKED_VALUE = "••••••••";

export function isPresentationMode() {
  return sessionStorage.getItem(PRESENTATION_MODE_KEY) === "true";
}
