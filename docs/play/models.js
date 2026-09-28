/** Stable visual variation, independent of authoritative terrain and resources. */
const palette = ["#86a789", "#ad9376", "#92a9bc", "#bd978e", "#c3b275"];
export function visualSeed(value) {
  let n = 2166136261;
  for (const c of String(value)) n = Math.imul(n ^ c.charCodeAt(0), 16777619);
  return n >>> 0;
}
const groundCache = new Map();
export function groundColor(kind, x, y, seed) {
  x = Math.floor(x);
  y = Math.floor(y);
  const key = `${seed}:${kind}:${x}:${y}`;
  if (groundCache.has(key)) return groundCache.get(key);
  const n = visualSeed(key),
    base = {
      meadow: [91, 114, 73],
      forest: [53, 80, 55],
      rock: [130, 133, 119],
      water: [54, 91, 103],
      unknown: [38, 59, 44],
    }[kind] || [38, 59, 44];
  const delta = kind === "unknown" ? 0 : (n % 13) - 6;
  const color = `rgb(${base.map((v) => v + delta).join(",")})`;
  if (groundCache.size > 8192) groundCache.clear();
  groundCache.set(key, color);
  return color;
}
const meshCache = new Map();
export function modelFor(item, seed = 0) {
  const key = `v1:${seed}:${item.id || `${item.kind}:${item.x}:${item.y}`}`;
  if (meshCache.has(key)) return meshCache.get(key);
  const boxes = [],
    n = visualSeed(key),
    box = (x, y, z, w, d, h, color) => boxes.push({ x, y, z, w, d, h, color });
  if (item.schematic) {
    const unit = item.kind === "workbench" ? 0.25 : 1;
    for (const [x, y, z, m] of item.schematic.cells)
      box(
        x * unit,
        y * unit,
        z * unit,
        unit,
        unit,
        unit,
        m === "stone" ? "#949d9a" : "#b69a6a",
      );
  } else if (item.kind === "tree") {
    const height = 1.3 + (n % 6) * 0.13,
      width = 0.65 + (n % 4) * 0.12;
    box(-0.09, -0.09, 0, 0.18, 0.18, height, "#68533c");
    const leaf = ["#567e4a", "#6f9258", "#779560"][n % 3];
    if (n % 2) {
      for (let i = 0; i < 3; i++) {
        const s = width * (1 - i * 0.23);
        box(-s / 2, -s / 2, height * 0.45 + i * 0.4, s, s, 0.55, leaf);
      }
    } else {
      box(-width / 2, -width / 2, height * 0.65, width, width, 0.65, leaf);
      box(
        -width * 0.35,
        -width * 0.35,
        height * 0.65 + 0.6,
        width * 0.7,
        width * 0.7,
        0.4,
        leaf,
      );
    }
  } else {
    const shirt = palette[n % palette.length],
      skin = ["#d3b18b", "#a87954", "#7c553f", "#c39977"][n % 4],
      h = 0.85 + (n % 5) * 0.035;
    box(-0.16, -0.12, 0.28, 0.32, 0.24, h * 0.48, shirt);
    box(-0.12, -0.12, 0.28 + h * 0.48, 0.24, 0.24, 0.25, skin);
    box(-0.13, -0.11, 0.28 + h * 0.48 + 0.21, 0.26, 0.25, 0.07, "#493c34");
    box(-0.15, -0.09, 0, 0.11, 0.18, 0.3, "#414d46");
    box(0.04, -0.09, 0, 0.11, 0.18, 0.3, "#414d46");
    box(-0.23, -0.1, 0.32, 0.07, 0.2, 0.32, shirt);
    box(0.16, -0.1, 0.32, 0.07, 0.2, 0.32, shirt);
  }
  if (meshCache.size > 2048) meshCache.clear();
  meshCache.set(key, boxes);
  return boxes;
}

/** Projects the same six-faced boxes into either camera; never invents world state. */
export function drawModel(ctx, boxes, origin, project) {
  const faces = [];
  const sides = [
    [0, 1, 2, 3],
    [4, 7, 6, 5],
    [0, 4, 5, 1],
    [1, 5, 6, 2],
    [2, 6, 7, 3],
    [3, 7, 4, 0],
  ];
  for (const b of boxes) {
    const x = origin.x + b.x,
      y = origin.y + b.y,
      z = b.z;
    const world = [
      [x, y, z],
      [x + b.w, y, z],
      [x + b.w, y + b.d, z],
      [x, y + b.d, z],
      [x, y, z + b.h],
      [x + b.w, y, z + b.h],
      [x + b.w, y + b.d, z + b.h],
      [x, y + b.d, z + b.h],
    ];
    sides.forEach((indices, i) => {
      let vertices = indices.map((j) => world[j]);
      if (project.near) {
        const near = project.near,
          clipped = [];
        for (let k = 0; k < vertices.length; k++) {
          const a = vertices[k],
            b = vertices[(k + 1) % vertices.length],
            pa = project(...a),
            pb = project(...b),
            aIn = pa.depth >= near,
            bIn = pb.depth >= near;
          if (aIn) clipped.push(a);
          if (aIn !== bIn) {
            const t = (near - pa.depth) / (pb.depth - pa.depth);
            clipped.push(a.map((v, j) => v + (b[j] - v) * t));
          }
        }
        vertices = clipped;
      }
      const p = vertices.map((v) => project(...v)).filter(Boolean);
      if (p.length < 3) return;
      faces.push({
        p,
        color: b.color,
        shade: [0.3, 0, 0.22, 0.1, 0.16, 0.25][i],
        depth: p.reduce((n, q) => n + q.depth, 0) / p.length,
      });
    });
  }
  faces.sort((a, b) => b.depth - a.depth);
  for (const f of faces) {
    ctx.beginPath();
    f.p.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
    ctx.closePath();
    ctx.fillStyle = f.color;
    ctx.fill();
    ctx.fillStyle = `rgba(0,0,0,${f.shade})`;
    ctx.fill();
    ctx.strokeStyle = "#14231b35";
    ctx.lineWidth = 0.5;
    ctx.stroke();
  }
}

export function previewProjection(
  design,
  width = 360,
  height = 230,
  padding = 16,
) {
  const unit = design.kind === "workbench" ? 0.25 : 1,
    w = design.width * unit,
    d = design.depth * unit,
    h = design.height * unit;
  const scale = Math.min(
    (width - padding * 2) / (w + d),
    (height - padding * 2) / (h + (w + d) * 0.4),
  );
  const centerV = (0.4 * (w + d) - h) / 2;
  return (x, y, z) => ({
    x: width / 2 + (x - y) * scale,
    y: height / 2 + (0.4 * (x + y) - z - centerV) * scale,
    depth: -x - y - z * 0.01,
  });
}
