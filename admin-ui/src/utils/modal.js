/**
 * Modal utilities - focus trap and ESC-to-close.
 * Usage: openModal(el, onClose) / closeModal(el)
 */

let _activeModal = null;
let _previousFocus = null;
let _onClose = null;
let _keyHandler = null;
let _focusTrapHandler = null;

export function openModal(modal, onClose) {
  _previousFocus = document.activeElement;
  _activeModal = modal;
  _onClose = onClose;

  modal.classList.remove("hidden");

  // Focus first focusable element
  const focusable = getFocusable(modal);
  if (focusable.length) focusable[0].focus();

  // ESC to close
  _keyHandler = (e) => {
    if (e.key === "Escape") {
      e.preventDefault();
      closeModal(modal);
    }
    // Tab trap
    if (e.key === "Tab") {
      const els = getFocusable(modal);
      if (els.length === 0) return;
      const first = els[0];
      const last = els[els.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  };
  document.addEventListener("keydown", _keyHandler);
}

export function closeModal(modal) {
  modal.classList.add("hidden");

  if (_keyHandler) {
    document.removeEventListener("keydown", _keyHandler);
    _keyHandler = null;
  }

  if (_onClose) {
    _onClose();
    _onClose = null;
  }

  if (_previousFocus && _previousFocus.focus) {
    _previousFocus.focus();
  }

  _activeModal = null;
  _previousFocus = null;
}

function getFocusable(container) {
  return [
    ...container.querySelectorAll(
      'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
    ),
  ].filter((el) => !el.closest(".hidden"));
}
