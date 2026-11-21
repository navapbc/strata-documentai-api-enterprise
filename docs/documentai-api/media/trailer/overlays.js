// Template filling for overlays.html (loaded by it, used by render_overlays.mjs).
// Render template `id` into the stage.
//   content: { selector: value }. A string or array of lines (joined with <br>);
//            *word* becomes bold. Or { svg } for trusted markup such as an icon.
//            The key "" fills the template's root element itself.
//   options: { classes: [...], style: { "--var": value } } applied to the root
//   element. `style` sets CSS custom properties, such as --chip-index.
function fillTemplate(id, content = {}, options = {}) {
  const stage = document.getElementById("stage");
  stage.replaceChildren(document.getElementById(id).content.cloneNode(true));
  const root = stage.firstElementChild;
  for (const [selector, value] of Object.entries(content)) {
    const el = selector ? root.querySelector(selector) : root;
    if (value && value.svg !== undefined) {
      el.innerHTML = value.svg;
      continue;
    }
    el.replaceChildren();
    [].concat(value).forEach((line, i) => {
      if (i) el.append(document.createElement("br"));
      for (const part of line.split(/(\*[^*]+\*)/)) {
        if (/^\*[^*]+\*$/.test(part)) {
          const b = document.createElement("b");
          b.textContent = part.slice(1, -1);
          el.append(b);
        } else if (part) {
          el.append(part);
        }
      }
    });
  }
  root.classList.add(...(options.classes ?? []));
  for (const [name, value] of Object.entries(options.style ?? {})) {
    root.style.setProperty(name, value);
  }
}
