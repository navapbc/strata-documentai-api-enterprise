/**
 * Elapsed-time ticker.
 *
 * Usage:
 *   const timer = createElapsedTimer((s) => (el.textContent = `Processing… ${s}s`));
 *   timer.start();
 *   // later:
 *   timer.stop();
 */
export function createElapsedTimer(onTick) {
  let startTime = null;
  let intervalId = null;

  function tick() {
    if (startTime === null) return;
    onTick(Math.floor((Date.now() - startTime) / 1000));
  }

  return {
    start() {
      startTime = Date.now();
      intervalId = setInterval(tick, 1000);
      tick();
    },
    stop() {
      clearInterval(intervalId);
      intervalId = null;
      startTime = null;
    },
  };
}
