let currentFrame: number | null = null;
let removeInterrupts: (() => void) | null = null;

/** A predictable vertical-only scroll for iPhone Safari and desktop browsers. */
export function smoothScrollTo(target: Element | null) {
  if (!target) return;
  if (currentFrame !== null) cancelAnimationFrame(currentFrame);
  removeInterrupts?.();
  currentFrame = null;

  const margin = Number.parseFloat(getComputedStyle(target).scrollMarginTop) || 16;
  const start = window.scrollY;
  const max = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
  const end = Math.min(max, Math.max(0, start + target.getBoundingClientRect().top - margin));
  const distance = end - start;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || Math.abs(distance) < 2) {
    window.scrollTo(0, end);
    return;
  }

  const duration = Math.min(650, Math.max(300, Math.abs(distance) * 0.55));
  const began = performance.now();
  const stop = () => {
    if (currentFrame !== null) cancelAnimationFrame(currentFrame);
    currentFrame = null;
    removeInterrupts?.();
    removeInterrupts = null;
  };
  window.addEventListener('touchstart', stop, { passive: true });
  window.addEventListener('wheel', stop, { passive: true });
  removeInterrupts = () => {
    window.removeEventListener('touchstart', stop);
    window.removeEventListener('wheel', stop);
  };
  const frame = (now: number) => {
    const progress = Math.min(1, (now - began) / duration);
    const eased = 1 - (1 - progress) ** 3;
    window.scrollTo(0, start + distance * eased);
    if (progress < 1) currentFrame = requestAnimationFrame(frame);
    else stop();
  };
  currentFrame = requestAnimationFrame(frame);
}
