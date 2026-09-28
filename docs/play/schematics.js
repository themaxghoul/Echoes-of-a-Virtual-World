/** Shared, versioned construction rules. Model output never supplies costs. */
export function validateSchematic(input) {
  if (!input || !["workbench", "structure"].includes(input.kind))
    throw Error("Choose workbench or structure.");
  const { kind, width, depth, height } = input;
  if (
    ![width, depth, height].every(
      (n) => Number.isInteger(n) && n >= 2 && n <= 4,
    )
  )
    throw Error("Dimensions must be whole numbers from 2 to 4.");
  if (
    typeof input.name !== "string" ||
    !input.name.trim() ||
    input.name.length > 60
  )
    throw Error("Name your design (1–60 characters).");
  if (
    !Array.isArray(input.cells) ||
    !input.cells.length ||
    input.cells.length > 64
  )
    throw Error("Use 1–64 material blocks.");
  const occupied = new Map(),
    cost = { planks: 0, stone: 0 };
  const cells = input.cells.map((c) => {
    if (!Array.isArray(c) || c.length !== 4)
      throw Error("Invalid material block.");
    const [x, y, z, material] = c;
    if (
      ![x, y, z].every(Number.isInteger) ||
      x < 0 ||
      x >= width ||
      y < 0 ||
      y >= depth ||
      z < 0 ||
      z >= height ||
      !["planks", "stone"].includes(material)
    )
      throw Error("Block outside grid or unknown material.");
    const key = [x, y, z].join(",");
    if (occupied.has(key)) throw Error("Duplicate material block.");
    occupied.set(key, material);
    cost[material]++;
    return [...c];
  });
  const ground = cells.filter((c) => c[2] === 0);
  if (!ground.length) throw Error("Construction must touch the ground.");
  const reached = new Set([ground[0].slice(0, 3).join(",")]),
    queue = [ground[0]];
  for (let i = 0; i < queue.length; i++) {
    const [x, y, z] = queue[i];
    for (const [dx, dy, dz] of [
      [1, 0, 0],
      [-1, 0, 0],
      [0, 1, 0],
      [0, -1, 0],
      [0, 0, 1],
      [0, 0, -1],
    ]) {
      const p = [x + dx, y + dy, z + dz],
        key = p.join(",");
      if (occupied.has(key) && !reached.has(key)) {
        reached.add(key);
        queue.push(p);
      }
    }
  }
  if (reached.size !== cells.length)
    throw Error("Every block must connect to the grounded construction.");
  if (kind === "workbench") {
    for (let x = 0; x < width; x++)
      for (let y = 0; y < depth; y++)
        if (occupied.get([x, y, height - 1].join(",")) !== "planks")
          throw Error("A workbench needs a complete plank work surface.");
    for (const x of [0, width - 1])
      for (const y of [0, depth - 1])
        for (let z = 0; z < height - 1; z++)
          if (!occupied.has([x, y, z].join(",")))
            throw Error(
              "Support all four workbench corners down to the ground.",
            );
  }
  return {
    version: 1,
    kind,
    name: input.name.trim(),
    width,
    depth,
    height,
    cells,
    cost,
  };
}

export function template({
  kind = "workbench",
  width = 3,
  depth = 2,
  height = 2,
  material = "planks",
  roof = "flat",
  name,
} = {}) {
  if (
    !["planks", "stone"].includes(material) ||
    !["flat", "open"].includes(roof)
  )
    throw Error("Unknown template material or roof.");
  if (
    ![width, depth, height].every(
      (n) => Number.isInteger(n) && n >= 2 && n <= 4,
    )
  )
    throw Error("Dimensions must be whole numbers from 2 to 4.");
  const cells = [];
  for (let z = 0; z < height; z++)
    for (let y = 0; y < depth; y++)
      for (let x = 0; x < width; x++) {
        if (kind === "workbench") {
          if (z === height - 1) cells.push([x, y, z, "planks"]);
          else if ((x === 0 || x === width - 1) && (y === 0 || y === depth - 1))
            cells.push([x, y, z, material]);
        } else if (
          z === 0 ||
          (z === height - 1 && roof === "flat") ||
          x === 0 ||
          x === width - 1 ||
          y === 0 ||
          y === depth - 1
        )
          cells.push([x, y, z, material]);
      }
  return validateSchematic({
    kind,
    width,
    depth,
    height,
    name:
      name ||
      (kind === "workbench" ? "Joiner’s workbench" : "Frontier shelter"),
    cells,
  });
}

export function footprint(design) {
  return design.kind === "workbench"
    ? { width: 1, depth: 1 }
    : { width: design.width, depth: design.depth };
}
