/** Possibility -> instantiation -> persistence. No provider may reroll saved land. */
export class GenerationLimit extends Error {}
export function deriveSeed(parent, kind, identity) {
  // Stable UTF-8 FNV-1a 64-bit derivation; never use runtime-random hash functions.
  let hash = 14695981039346656037n;
  for (const byte of new TextEncoder().encode(
    JSON.stringify([parent, kind, identity]),
  ))
    hash = BigInt.asUintN(64, (hash ^ BigInt(byte)) * 1099511628211n);
  return hash.toString(16).padStart(16, "0");
}

export function terrainV1(worldSeed, x, y) {
  x = Math.floor(x);
  y = Math.floor(y);
  if (Math.abs(x) < 10 && Math.abs(y) < 10) return "meadow";
  let n =
    (Math.imul(Math.floor(x / 6), 374761393) ^
      Math.imul(Math.floor(y / 6), 668265263) ^
      worldSeed) >>>
    0;
  n = Math.imul(n ^ (n >>> 13), 1274126177) >>> 0;
  n = (n ^ (n >>> 16)) >>> 0;
  const value = n % 100;
  return value < 9
    ? "water"
    : value < 17
      ? "rock"
      : value < 47
        ? "forest"
        : "meadow";
}

export class ClassicalGenerator {
  generatePossibility(context, constraints, seed) {
    if (context.kind !== "parcel" || constraints.size !== 16)
      throw Error("Unsupported possibility context.");
    return {
      provider: "classical",
      version: "terrain-v1",
      seed,
      tiles: Array.from({ length: 256 }, (_, i) =>
        terrainV1(
          context.worldSeed,
          context.cx * 16 + (i % 16),
          context.cy * 16 + Math.floor(i / 16),
        ),
      ),
    };
  }
}

export class Possibilities {
  constructor(storage, worldSeed, generator = new ClassicalGenerator()) {
    this.storage = storage;
    this.worldSeed = worldSeed;
    this.generator = generator;
    this.cache = new Map();
    storage.exec(
      "CREATE TABLE IF NOT EXISTS world_chunks(key TEXT PRIMARY KEY,data TEXT)",
    );
    storage.exec(
      "CREATE TABLE IF NOT EXISTS world_nodes(key TEXT PRIMARY KEY,parent TEXT,kind TEXT,seed TEXT)",
    );
    storage.exec(
      "CREATE TABLE IF NOT EXISTS generation_budget(day TEXT PRIMARY KEY,used INTEGER)",
    );
  }
  path(cx, cy) {
    const parts = [
      ["world", String(this.worldSeed)],
      ["region", `${Math.floor(cx / 8)},${Math.floor(cy / 8)}`],
      ["settlement", `${Math.floor(cx / 2)},${Math.floor(cy / 2)}`],
      ["parcel", `${cx},${cy}`],
    ];
    let parent = "eov-seeds-v1",
      key = "";
    return parts.map(([kind, identity]) => {
      const seed = deriveSeed(parent, kind, identity),
        parentKey = key;
      key += `/${kind}:${identity}`;
      parent = seed;
      return { key, parent: parentKey, kind, seed };
    });
  }
  persistNode(node) {
    this.storage.exec(
      "INSERT OR IGNORE INTO world_nodes VALUES(?,?,?,?)",
      node.key,
      node.parent,
      node.kind,
      node.seed,
    );
  }
  child(parent, kind, identity) {
    if (!["structure", "room", "object"].includes(kind))
      throw Error("Invalid descendant kind.");
    const node = {
      key: `${parent.key}/${kind}:${identity}`,
      parent: parent.key,
      kind,
      seed: deriveSeed(parent.seed, kind, identity),
    };
    this.persistNode(node);
    return node;
  }
  chunk(cx, cy) {
    const key = `${cx},${cy}`;
    if (this.cache.has(key)) return this.cache.get(key);
    const saved = this.storage.exec(
      "SELECT data FROM world_chunks WHERE key=?",
      key,
    )[0];
    let chunk;
    if (saved) chunk = JSON.parse(saved.data);
    else {
      const day = new Date().toISOString().slice(0, 10);
      if (
        (this.storage.exec(
          "SELECT used FROM generation_budget WHERE day=?",
          day,
        )[0]?.used || 0) >= 1000
      )
        throw new GenerationLimit(
          "Today's shared terrain generation allowance is exhausted. Existing land remains available.",
        );
      this.storage.exec(
        "INSERT INTO generation_budget VALUES(?,1) ON CONFLICT(day) DO UPDATE SET used=used+1",
        day,
      );
      const path = this.path(cx, cy),
        seed = path.at(-1).seed;
      const possibility = this.generator.generatePossibility(
        { kind: "parcel", worldSeed: this.worldSeed, cx, cy },
        { size: 16 },
        seed,
      );
      if (
        !Array.isArray(possibility.tiles) ||
        possibility.tiles.length !== 256 ||
        possibility.tiles.some(
          (t) => !["water", "rock", "forest", "meadow"].includes(t),
        )
      )
        throw Error("Generator returned invalid terrain.");
      chunk = { ...possibility, cx, cy, size: 16, seed, path };
      // Caller owns the transaction, so building + seed records commit together.
      for (const node of path) this.persistNode(node);
      this.storage.exec(
        "INSERT INTO world_chunks VALUES(?,?)",
        key,
        JSON.stringify(chunk),
      );
    }
    this.cache.set(key, chunk);
    if (this.cache.size > 512)
      this.cache.delete(this.cache.keys().next().value);
    return chunk;
  }
  terrain(x, y) {
    x = Math.floor(x);
    y = Math.floor(y);
    const cx = Math.floor(x / 16),
      cy = Math.floor(y / 16);
    return this.chunk(cx, cy).tiles[(y - cy * 16) * 16 + x - cx * 16];
  }
}
