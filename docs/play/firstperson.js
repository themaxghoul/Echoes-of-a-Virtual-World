import { colors, canvasLoop, interpolate } from "./graphics.js";
export function mount(container, { tile }) {
  let state,
    camera,
    angle = -Math.PI / 2,
    dragX = null;
  const canvas = canvasLoop(container, (ctx, w, h, dt) => {
    const horizon = h * 0.45;
    const sky = ctx.createLinearGradient(0, 0, 0, horizon);
    sky.addColorStop(0, "#45665f");
    sky.addColorStop(1, "#bdc6a4");
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, w, horizon);
    ctx.fillStyle = "#41583a";
    ctx.fillRect(0, horizon, w, h - horizon);
    if (!state) return;
    camera = interpolate(camera, state.self, dt);
    // Perspective floor samples the exact same server-provided terrain chunks as isometric mode.
    const fov = Math.PI / 2.7,
      projection = w / (2 * Math.tan(fov / 2));
    for (let y = Math.floor(horizon) + 4; y < h; y += 6) {
      const depth = Math.min(45, (projection * 0.55) / (y - horizon));
      for (let x = 0; x < w; x += 8) {
        const side = (x - w / 2) / projection;
        const wx =
            camera.x + Math.cos(angle) * depth - Math.sin(angle) * side * depth,
          wy =
            camera.y + Math.sin(angle) * depth + Math.cos(angle) * side * depth;
        ctx.fillStyle =
          Math.abs(wx) >= state.world.radius ||
          Math.abs(wy) >= state.world.radius
            ? "#152118"
            : colors[tile(wx, wy)];
        ctx.fillRect(x, y, 8, 6);
      }
    }
    const items = [
      ...state.buildings,
      ...state.npcs.map((n) => ({ ...n, kind: "npc" })),
      ...state.players.map((p) => ({ ...p, kind: "player" })),
    ];
    for (let y = Math.floor(camera.y) - 22; y < camera.y + 22; y++)
      for (let x = Math.floor(camera.x) - 22; x < camera.x + 22; x++)
        if (tile(x, y) === "forest" && (x * 17 + y * 13) % 5 === 0)
          items.push({ x: x + 0.5, y: y + 0.5, kind: "tree" });
    items.sort(
      (a, b) =>
        Math.hypot(b.x - camera.x, b.y - camera.y) -
        Math.hypot(a.x - camera.x, a.y - camera.y),
    );
    for (const item of items) {
      const dx = item.x - camera.x,
        dy = item.y - camera.y,
        depth = dx * Math.cos(angle) + dy * Math.sin(angle),
        side = -dx * Math.sin(angle) + dy * Math.cos(angle);
      if (depth < 0.35 || depth > 45) continue;
      const x = w / 2 + (side / depth) * projection,
        size = Math.min(h * 2, projection / depth),
        ground = horizon + size * 0.55;
      if (x < -size || x > w + size) continue;
      if (item.kind === "tree") {
        ctx.fillStyle = "#3b4130";
        ctx.fillRect(
          x - size * 0.06,
          ground - size * 0.9,
          size * 0.12,
          size * 0.9,
        );
        ctx.fillStyle = "#426e45";
        ctx.beginPath();
        ctx.moveTo(x, ground - size * 1.8);
        ctx.lineTo(x + size * 0.5, ground - size * 0.35);
        ctx.lineTo(x - size * 0.5, ground - size * 0.35);
        ctx.fill();
      } else if (["camp", "lab", "farm"].includes(item.kind)) {
        ctx.fillStyle = item.kind === "lab" ? "#acbcb5" : "#b39773";
        ctx.fillRect(x - size * 0.45, ground - size, size * 0.9, size);
        ctx.fillStyle = "#695744";
        ctx.beginPath();
        ctx.moveTo(x - size * 0.55, ground - size);
        ctx.lineTo(x, ground - size * 1.4);
        ctx.lineTo(x + size * 0.55, ground - size);
        ctx.fill();
        ctx.fillStyle = "#304232";
        ctx.fillRect(
          x - size * 0.1,
          ground - size * 0.5,
          size * 0.2,
          size * 0.5,
        );
      } else {
        ctx.fillStyle = item.kind === "npc" ? "#e6b27b" : "#aac9d2";
        ctx.fillRect(
          x - size * 0.14,
          ground - size * 0.7,
          size * 0.28,
          size * 0.7,
        );
        ctx.beginPath();
        ctx.arc(x, ground - size * 0.85, size * 0.13, 0, 7);
        ctx.fill();
      }
      if (item.name && depth < 16) {
        ctx.fillStyle = "#fff6dc";
        ctx.font = "12px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(item.name, x, ground - size * 1.1);
      }
    }
    ctx.strokeStyle = "#edf1d3aa";
    ctx.beginPath();
    ctx.moveTo(w / 2 - 6, h / 2);
    ctx.lineTo(w / 2 + 6, h / 2);
    ctx.moveTo(w / 2, h / 2 - 6);
    ctx.lineTo(w / 2, h / 2 + 6);
    ctx.stroke();
  });
  canvas.onpointerdown = (e) => {
    dragX = e.clientX;
    canvas.setPointerCapture(e.pointerId);
  };
  canvas.onpointermove = (e) => {
    if (dragX !== null) {
      angle += (e.clientX - dragX) * 0.006;
      dragX = e.clientX;
    }
  };
  canvas.onpointerup = canvas.onpointercancel = () => {
    dragX = null;
  };
  return {
    update(s) {
      state = s;
    },
    turn(delta) {
      angle += delta;
    },
    direction(x, y) {
      return {
        dx: Math.max(
          -1,
          Math.min(1, -y * Math.cos(angle) - x * Math.sin(angle)),
        ),
        dy: Math.max(
          -1,
          Math.min(1, -y * Math.sin(angle) + x * Math.cos(angle)),
        ),
      };
    },
  };
}
