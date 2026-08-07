import { sortRows, bindSortHeaders } from "./helpers.js";

export class TableView {
  /**
   * @param {HTMLElement} table
   * @param {HTMLElement} tbody
   * @param {HTMLElement} emptyEl
   * @param {(row: any) => HTMLElement} renderRow
   */
  constructor(table, tbody, emptyEl, renderRow) {
    this._table = table;
    this._tbody = tbody;
    this._emptyEl = emptyEl;
    this._renderRow = renderRow;
    this._sortCol = null;
    this._sortDir = "asc";
    this._rows = [];
    this._sortUnsub = null;
  }

  bindSortHeaders(thead) {
    this._sortUnsub = bindSortHeaders(thead, (col, dir) => {
      this._sortCol = col;
      this._sortDir = dir;
      this._render(this._rows);
    });
    return this;
  }

  unbind() {
    if (this._sortUnsub) {
      this._sortUnsub();
      this._sortUnsub = null;
    }
  }

  showLoading() {
    this._tbody.innerHTML = "";
    this._table.classList.add("hidden");
    this._emptyEl.textContent = "Loading\u2026";
    this._emptyEl.classList.remove("hidden");
  }

  setRows(rows) {
    this._rows = rows;
    this._render(rows);
  }

  showError(message) {
    this._tbody.innerHTML = "";
    this._table.classList.add("hidden");
    this._emptyEl.textContent = message;
    this._emptyEl.classList.remove("hidden");
  }

  _render(rows) {
    const sorted = sortRows(rows, this._sortCol, this._sortDir);
    this._tbody.innerHTML = "";
    if (sorted.length === 0) {
      this._table.classList.add("hidden");
      this._emptyEl.classList.remove("hidden");
      return;
    }
    this._table.classList.remove("hidden");
    this._emptyEl.classList.add("hidden");
    for (const row of sorted) {
      this._tbody.appendChild(this._renderRow(row));
    }
  }
}
