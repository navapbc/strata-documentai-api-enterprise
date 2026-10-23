import { PRIVACY_MODE_KEY } from "./session.js";

export function isPrivacyMode() {
  return sessionStorage.getItem(PRIVACY_MODE_KEY) === "true";
}
