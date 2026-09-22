import { colors, canvasLoop, interpolate } from "./graphics.js";
export function mount(container, { tile }) {
  let state,
    camera,
    people = new Map();
  canvasLoop(container, (ctx, w, h, dt) => {
    ctx.fillStyle = "#182b1f";
    ctx.fillRect(0, 0, w, h);
    if (!state) return;
    camera = interpolate(camera, state.self, dt);
    const sx = 30,
      sy = 15,
      project = (x, y) => ({
        x: w / 2 + (x - camera.x - y + camera.y) * sx,
        y: h / 2 + (x - camera.x + y - camera.y) * sy,
      });
    const diamond = (x, y, color) => {
      const p = project(x, y);
      if (p.x < -70 || p.x > w + 70 || p.y < -90 || p.y > h + 70) return;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      ctx.lineTo(p.x + sx, p.y + sy);
      ctx.lineTo(p.x, p.y + sy * 2);
      ctx.lineTo(p.x - sx, p.y + sy);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = "#13271919";
      ctx.stroke();
    };
    const range = Math.min(40, Math.ceil(w / 60 + h / 30));
    for (let y = Math.floor(camera.y) - range; y <= camera.y + range; y++)
      for (let x = Math.floor(camera.x) - range; x <= camera.x + range; x++) {
        const terrain = tile(x, y);
        diamond(
          x,
          y,
          Math.abs(x) >= state.world.radius || Math.abs(y) >= state.world.radius
            ? "#162019"
            : colors[terrain],
        );
      }
    const objects = [];
    for (let y = Math.floor(camera.y) - 22; y < camera.y + 22; y++)
      for (let x = Math.floor(camera.x) - 22; x < camera.x + 22; x++) {
        if (tile(x, y) === "forest" && (x * 17 + y * 13) % 5 === 0)
          objects.push({ x: x + 0.5, y: y + 0.5, kind: "tree" });
      }
    objects.push(
      ...state.buildings,
      ...state.npcs.map((n) => ({ ...n, kind: "npc" })),
      ...state.players.map((p) => ({ ...p, kind: "player" })),
      { ...state.self, kind: "self" },
    );
    objects.sort((a, b) => a.x + a.y - b.x - b.y);
    for (const item of objects) {
      let world = item;
      if (["self", "player", "npc"].includes(item.kind)) {
        world = interpolate(people.get(item.id), item, dt);
        people.set(item.id, world);
      }
      const p = project(world.x, world.y);
      if (p.x < -90 || p.x > w + 90 || p.y < -90 || p.y > h + 120) continue;
      if (item.kind === "tree") {
        ctx.fillStyle = "#203828";
        ctx.fillRect(p.x - 3, p.y - 24, 6, 28);
        ctx.fillStyle = "#83a069";
        ctx.beginPath();
        ctx.moveTo(p.x, p.y - 55);
        ctx.lineTo(p.x + 15, p.y - 12);
        ctx.lineTo(p.x - 15, p.y - 12);
        ctx.fill();
        continue;
      }
      if (["camp", "farm", "lab"].includes(item.kind)) {
        ctx.fillStyle =
          item.kind === "lab"
            ? "#b5c1bd"
            : item.kind === "farm"
              ? "#bba365"
              : "#b99b79";
        ctx.fillRect(p.x - 15, p.y - 22, 30, 27);
        ctx.fillStyle = item.kind === "lab" ? "#728f9a" : "#685446";
        ctx.beginPath();
        ctx.moveTo(p.x - 20, p.y - 22);
        ctx.lineTo(p.x, p.y - 39);
        ctx.lineTo(p.x + 20, p.y - 22);
        ctx.fill();
        ctx.fillStyle = "#344235";
        ctx.fillRect(p.x - 4, p.y - 9, 8, 14);
      } else {
        ctx.fillStyle = "#10231966";
        ctx.beginPath();
        ctx.ellipse(p.x, p.y + 3, 10, 5, 0, 0, 7);
        ctx.fill();
        ctx.fillStyle =
          item.kind === "self"
            ? "#e4eea7"
            : item.kind === "npc"
              ? "#e8b780"
              : "#a3c9d2";
        ctx.fillRect(p.x - 5, p.y - 18, 10, 18);
        ctx.beginPath();
        ctx.arc(p.x, p.y - 24, 6, 0, 7);
        ctx.fill();
      }
      ctx.textAlign = "center";
      ctx.font = "10px sans-serif";
      ctx.fillStyle = "#f2f2df";
      ctx.shadowColor = "#102018";
      ctx.shadowBlur = 4;
      ctx.fillText(item.name || item.kind, p.x, p.y - 44);
      ctx.shadowBlur = 0;
    }
    if (people.size > 200) people = new Map();
  });
  // Screen-aligned movement transformed into world axes; normalized server-side.
  return {
    update(s) {
      state = s;
    },
    direction(x, y) {
      return { dx: (x + y) / Math.SQRT2, dy: (y - x) / Math.SQRT2 };
    },
  };
}
