import * as Session from "../../utils/session.js";
import * as Icons from "../../utils/icons.js";
import { tpl } from "../../utils/tpl.js";
import html from "./home.html";

const tmpl = tpl(html);

export function mount(root) {
  root.replaceChildren(tmpl());
  root.classList.add("main-content--home");
  document.querySelector(".content-header")?.classList.add("hidden");

  const session = Session.get();
  const emailEl = root.querySelector("#home-email");
  if (emailEl) emailEl.textContent = session?.email || "";

  root.querySelectorAll("[data-icon]").forEach((el) => {
    const icon = Icons[el.dataset.icon];
    // eslint-disable-next-line no-unsanitized/method -- icon is always a hardcoded trusted constant from the Icons module
    if (icon) el.insertAdjacentHTML("afterbegin", icon);
  });

  const isSuper = Session.isSuperAdmin();
  root.querySelectorAll(".super-admin-only").forEach((el) => {
    el.classList.toggle("hidden", !isSuper);
  });
}

export function unmount(root) {
  root.replaceChildren();
  root.classList.remove("main-content--home");
  document.querySelector(".content-header")?.classList.remove("hidden");
}
