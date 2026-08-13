/**
 * Simple autocomplete - plain input that filters a dropdown list.
 * @param {HTMLElement} container
 * @param {{ placeholder?: string, onSelect: (value: string) => void }} options
 * @returns {{ setItems(items: string[]): void, setValue(value: string): void, destroy(): void }}
 */
export function createCombobox(container, { placeholder = "Search…", onSelect }) {
  let _items = [];

  container.style.position = "relative";
  const wrap = document.createElement("div");
  wrap.className = "combobox-wrap";
  const inputEl = document.createElement("input");
  inputEl.type = "text";
  inputEl.className = "combobox-input";
  inputEl.placeholder = placeholder;
  inputEl.autocomplete = "off";
  const clearBtn = document.createElement("button");
  clearBtn.type = "button";
  clearBtn.className = "combobox-clear hidden";
  clearBtn.setAttribute("aria-label", "Clear");
  clearBtn.textContent = "✕";
  wrap.appendChild(inputEl);
  wrap.appendChild(clearBtn);
  const listEl = document.createElement("ul");
  listEl.className = "combobox-list hidden";
  container.appendChild(wrap);
  container.appendChild(listEl);

  const input = inputEl;
  const list = listEl;
  const clear = clearBtn;

  function updateClear() {
    clear.classList.toggle("hidden", !input.value);
  }

  function renderList(filter) {
    const q = filter.toLowerCase();
    const matches = q ? _items.filter((i) => i.toLowerCase().includes(q)) : _items;
    list.innerHTML = "";
    for (const item of matches) {
      const li = document.createElement("li");
      li.className = "combobox-option";
      li.textContent = item;
      li.addEventListener("mousedown", (e) => {
        e.preventDefault();
        input.value = item;
        close();
        onSelect(item);
      });
      list.appendChild(li);
    }
    list.classList.toggle("hidden", !matches.length);
  }

  function close() {
    list.classList.add("hidden");
  }

  input.addEventListener("input", () => {
    renderList(input.value);
    updateClear();
  });
  input.addEventListener("click", () => renderList(input.value));
  input.addEventListener("blur", () => close());

  clear.addEventListener("mousedown", (e) => {
    e.preventDefault();
    input.value = "";
    updateClear();
    close();
    onSelect("");
  });

  return {
    setItems(items) {
      _items = items;
    },
    setValue(value) {
      input.value = value || "";
      updateClear();
    },
    destroy() {
      container.innerHTML = "";
      container.style.position = "";
    },
  };
}
