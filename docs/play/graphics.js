export const colors = {
  meadow: "#57724a",
  forest: "#344f37",
  rock: "#858678",
  water: "#365c66",
  unknown: "#263b2c",
};
export function canvasLoop(container, draw) {
  const canvas = document.createElement("canvas");
  canvas.tabIndex = 0;
  canvas.setAttribute(
    "aria-label",
    "Game world; keyboard and direction-button movement supported",
  );
  container.replaceChildren(canvas);
  const ctx = canvas.getContext("2d");
  let width = 0,
    height = 0,
    last = performance.now();
  function frame(now) {
    const rect = container.getBoundingClientRect();
    if (width !== rect.width || height !== rect.height) {
      width = rect.width;
      height = rect.height;
      const dpr = Math.min(devicePixelRatio || 1, 2);
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    draw(ctx, width, height, Math.min((now - last) / 1000, 0.05));
    last = now;
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  return canvas;
}
export function interpolate(current, target, dt) {
  if (!current) return { ...target };
  const blend = 1 - Math.exp(-18 * dt);
  return {
    x: current.x + (target.x - current.x) * blend,
    y: current.y + (target.y - current.y) * blend,
  };
}
