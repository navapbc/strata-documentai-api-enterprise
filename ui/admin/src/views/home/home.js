import * as Session from "../../utils/session.js";
import * as Icons from "../../utils/icons.js";
import { tpl } from "../../utils/tpl.js";
import NAV_SECTIONS from "../../config/nav.js";
import html from "./home.html";

const tmpl = tpl(html);

export function mount(root) {
  root.replaceChildren(tmpl());
  root.classList.add("main-content--home");
  document.querySelector(".content-header")?.classList.add("hidden");

  const session = Session.get();
  const emailEl = root.querySelector("#home-email");
  if (emailEl) emailEl.textContent = session?.email || "";

  const isSuper = Session.isSuperAdmin();
  const grid = root.querySelector("#home-grid");

  NAV_SECTIONS.forEach(({ label, icon, description, items }) => {
    const card = document.createElement("div");
    card.className = "home-card";

    const iconEl = document.createElement("span");
    iconEl.className = "home-card-icon";
    // eslint-disable-next-line no-unsanitized/property -- icon is always a hardcoded trusted constant from the Icons module
    if (Icons[icon]) iconEl.innerHTML = Icons[icon];

    const h3 = document.createElement("h3");
    h3.textContent = label;

    const p = document.createElement("p");
    p.textContent = description;

    const links = document.createElement("div");
    links.className = "home-card-links";
    items.forEach(({ view, label: linkLabel, superAdmin }) => {
      const a = document.createElement("a");
      a.className = "home-card-link" + (superAdmin ? " super-admin-only" : "");
      a.href = `#${view}`;
      a.textContent = linkLabel;
      if (superAdmin && !isSuper) {
        a.classList.add("hidden");
      }
      links.appendChild(a);
    });

    card.append(iconEl, h3, p, links);
    grid.appendChild(card);
  });
}

export function unmount(root) {
  root.replaceChildren();
  root.classList.remove("main-content--home");
  document.querySelector(".content-header")?.classList.remove("hidden");
}
