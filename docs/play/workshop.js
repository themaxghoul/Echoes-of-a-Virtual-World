import { template, validateSchematic, footprint } from "./schematics.js";
import { drawModel, modelFor, previewProjection } from "./models.js";

export function mountWorkshop({ api, action: sendAction, getState }) {
  let pendingAction = null;
  async function action(data) {
    const signature = JSON.stringify(data);
    if (pendingAction?.signature !== signature)
      pendingAction = { signature, id: crypto.randomUUID() };
    const result = await sendAction({ ...data, request_id: pendingAction.id });
    pendingAction = null;
    return result;
  }
  const dialog = document.createElement("dialog");
  dialog.className = "workshop";
  dialog.setAttribute("aria-labelledby", "workshop-title");
  dialog.innerHTML = `<header><div><span class="eyebrow">DESIGN · CRAFT · CONSTRUCT</span><h2 id="workshop-title">The workbench</h2></div><button id="workshop-close" class="secondary">Close</button></header>
  <p>Process wood into planks. Design a bench, then build structures beside it. Every material block has a cost.</p>
  <div id="workshop-inventory" class="small"></div>
  <div class="workshop-columns"><section>
    <form id="plank-form"><label>Wood to process (1 wood → 2 planks)<input id="plank-amount" type="number" min="1" max="50" value="5" required></label><button>Make planks</button></form>
    <label>Design type<select id="design-kind"><option value="workbench">Workbench</option><option value="structure">Structure</option></select></label>
    <label>Name<input id="design-name" maxlength="60" required></label>
    <div class="dimension-fields"><label>Width<input id="design-width" type="number" min="2" max="4" value="3"></label><label>Depth<input id="design-depth" type="number" min="2" max="4" value="2"></label><label>Height<input id="design-height" type="number" min="2" max="4" value="2"></label></div>
    <button id="design-template" class="secondary">Start new template</button>
    <form id="design-generate"><label>Describe your design<textarea id="design-prompt" maxlength="500" rows="3" required placeholder="A broad wooden workbench with stone legs…"></textarea></label><button>Suggest with AI</button></form>
    <p class="small">AI chooses a small template; you edit its blocks. Free allowance is shared with conversations. Manual design always works.</p>
  </section><section>
    <canvas id="design-preview" width="360" height="230" aria-label="Isometric schematic preview"></canvas>
    <div class="dimension-fields"><label>Layer<select id="design-layer"></select></label><label>Paint material<select id="design-material"><option value="planks">Wood planks</option><option value="stone">Stone</option><option value="erase">Erase</option></select></label></div>
    <div id="design-grid" aria-label="Editable schematic layer"></div>
    <p id="design-cost" class="small" aria-live="polite"></p>
    <p class="small">Click a cell to paint it. Benches need a full plank top and four corner legs. Structure blocks must connect to the ground. This alpha uses simplified support rules and solid building footprints.</p>
    <button id="design-save">Save schematic</button>
    <label>Saved schematics<select id="saved-designs"><option value="">Choose a saved design</option></select></label>
    <button id="design-load" class="secondary">Load for editing</button>
    <button id="design-build">Construct saved design east of me</button>
    <p class="small">Structures require your own workbench within 4 tiles. Placement must clear other players, buildings, water and the protected commons.</p>
  </section></div><p id="workshop-status" role="status" aria-live="polite">Create a design or choose a saved schematic.</p>`;
  document.body.append(dialog);
  const $ = (id) => dialog.querySelector("#" + id);
  let draft = template(),
    saved = [],
    busy = false,
    pendingGeneration = null;
  const status = (text) => ($("workshop-status").textContent = text);
  function draw() {
    $("design-name").value = draft.name;
    const layer = Number($("design-layer").value) || 0,
      grid = $("design-grid");
    grid.replaceChildren();
    grid.style.gridTemplateColumns = `repeat(${draft.width},1fr)`;
    for (let y = 0; y < draft.depth; y++)
      for (let x = 0; x < draft.width; x++) {
        const cell = draft.cells.find(
            (c) => c[0] === x && c[1] === y && c[2] === layer,
          ),
          button = document.createElement("button");
        button.type = "button";
        button.className = "material-cell " + (cell?.[3] || "empty");
        button.textContent =
          cell?.[3] === "planks" ? "P" : cell?.[3] === "stone" ? "S" : "·";
        button.setAttribute(
          "aria-label",
          `Column ${x + 1}, row ${y + 1}, layer ${layer + 1}: ${cell?.[3] || "empty"}`,
        );
        button.onclick = () => {
          draft.cells = draft.cells.filter(
            (c) => !(c[0] === x && c[1] === y && c[2] === layer),
          );
          if ($("design-material").value !== "erase")
            draft.cells.push([x, y, layer, $("design-material").value]);
          draw();
          grid.children[y * draft.width + x].focus();
        };
        grid.append(button);
      }
    let valid = true;
    try {
      const d = validateSchematic(draft),
        f = footprint(d);
      $("design-cost").textContent =
        `${d.cost.planks} planks · ${d.cost.stone} stone · ${f.width} × ${f.depth} tile footprint. Valid ${d.kind}.`;
    } catch (e) {
      valid = false;
      $("design-cost").textContent = e.message;
    }
    $("design-save").disabled = busy || !valid;
    const ctx = $("design-preview").getContext("2d");
    ctx.clearRect(0, 0, 360, 230);
    // Unique draft identity avoids reusing a cached mesh after a material edit.
    const boxes = modelFor({
      id: JSON.stringify(draft),
      kind: draft.kind,
      schematic: draft,
    });
    drawModel(ctx, boxes, { x: 0, y: 0 }, previewProjection(draft));
  }
  function load(d) {
    draft = structuredClone(d);
    $("design-kind").value = d.kind;
    for (const k of ["width", "depth", "height"]) $("design-" + k).value = d[k];
    $("design-layer").replaceChildren(
      ...Array.from(
        { length: d.height },
        (_, i) =>
          new Option(
            i === 0
              ? "1 · ground"
              : `${i + 1}${i === d.height - 1 ? " · top" : ""}`,
            i,
          ),
      ),
    );
    draw();
  }
  async function refresh(selected = $("saved-designs").value) {
    saved = await api("/api/schematics");
    $("saved-designs").replaceChildren(
      new Option("Choose a saved design", ""),
      ...saved.map(
        (s) =>
          new Option(`${s.name} · ${s.cost.planks}P / ${s.cost.stone}S`, s.id),
      ),
    );
    $("saved-designs").value = selected;
  }
  async function run(fn) {
    if (busy) return;
    busy = true;
    dialog.setAttribute("aria-busy", "true");
    for (const b of dialog.querySelectorAll("button, input, select, textarea"))
      if (b.id !== "workshop-close") b.disabled = true;
    try {
      await fn();
    } catch (e) {
      status(e.message);
    } finally {
      busy = false;
      dialog.removeAttribute("aria-busy");
      for (const b of dialog.querySelectorAll(
        "button, input, select, textarea",
      ))
        b.disabled = false;
      draw();
      update(getState());
    }
  }
  $("workshop-close").onclick = () => dialog.close();
  $("design-layer").onchange = draw;
  $("design-name").oninput = () => {
    draft.name = $("design-name").value;
    try {
      validateSchematic(draft);
      $("design-save").disabled = busy;
    } catch {
      $("design-save").disabled = true;
    }
  };
  $("design-template").onclick = () => {
    try {
      load(
        template({
          kind: $("design-kind").value,
          ...Object.fromEntries(
            ["width", "depth", "height"].map((k) => [
              k,
              Number($("design-" + k).value),
            ]),
          ),
        }),
      );
      status("New template. Edit any layer before saving.");
    } catch (e) {
      status(e.message);
    }
  };
  $("plank-form").onsubmit = (e) => {
    e.preventDefault();
    run(async () => {
      const r = await action({
        type: "craft_planks",
        amount: Number($("plank-amount").value),
      });
      status(r?.reply || "Action failed; see the game status.");
    });
  };
  $("design-generate").onsubmit = (e) => {
    e.preventDefault();
    run(async () => {
      const data = {
        kind: $("design-kind").value,
        prompt: $("design-prompt").value,
      };
      const signature = JSON.stringify(data);
      if (pendingGeneration?.signature !== signature)
        pendingGeneration = { signature, id: crypto.randomUUID() };
      status("Generating a draft…");
      const r = await api("/api/schematics/generate", {
        ...data,
        request_id: pendingGeneration.id,
      });
      load(r.schematic);
      status(r.notice);
      pendingGeneration = null;
    });
  };
  $("design-save").onclick = () =>
    run(async () => {
      const r = await action({
        type: "save_schematic",
        schematic: validateSchematic(draft),
      });
      if (r) {
        await refresh(r.schematic.id);
        status(r.reply);
      } else status("Save failed; see the game status.");
    });
  $("design-load").onclick = () => {
    const d = saved.find((s) => s.id === $("saved-designs").value);
    if (d) {
      load(d);
      status("Loaded a copy. Save edits as a new schematic.");
    } else status("Choose a saved schematic first.");
  };
  $("design-build").onclick = () =>
    run(async () => {
      const id = $("saved-designs").value;
      if (!id) throw Error("Save or select a schematic first.");
      const r = await action({ type: "construct", schematic_id: id });
      status(r?.reply || "Construction failed; see the game status.");
    });
  function update(s) {
    if (s && dialog.open)
      $("workshop-inventory").textContent =
        `Available: ${s.self.wood} wood · ${s.self.planks || 0} planks · ${s.self.stone} stone`;
  }
  load(draft);
  return {
    update,
    async open() {
      dialog.showModal();
      update(getState());
      try {
        await refresh();
      } catch (e) {
        status(e.message);
      }
    },
  };
}
