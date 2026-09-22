/** Free-tier authoritative world. No database reads in the movement/snapshot loop.
 * SQL is accessed only on startup, account operations, durable actions and batched saves.
 * One fixed Durable Object owns the world, making synchronous transactions serial.
 */
const encode = new TextEncoder();
const hex = (bytes) =>
  Array.from(new Uint8Array(bytes), (b) =>
    b.toString(16).padStart(2, "0"),
  ).join("");
const random = () => hex(crypto.getRandomValues(new Uint8Array(32)));
const digest = async (text) =>
  hex(await crypto.subtle.digest("SHA-256", encode.encode(text)));
async function passwordHash(password, salt) {
  const key = await crypto.subtle.importKey(
    "raw",
    encode.encode(password),
    "PBKDF2",
    false,
    ["deriveBits"],
  );
  return hex(
    await crypto.subtle.deriveBits(
      {
        name: "PBKDF2",
        salt: encode.encode(salt),
        iterations: 100000,
        hash: "SHA-256",
      },
      key,
      256,
    ),
  );
}
const NPCS = [
  {
    id: "mira",
    name: "Mira",
    role: "ecologist",
    home: [4, 4],
    goal: "compare soil moisture in forest and meadow",
    activities: [
      "cataloguing soil samples",
      "checking the woodland",
      "writing field notes",
    ],
  },
  {
    id: "oren",
    name: "Oren",
    role: "builder",
    home: [-5, 3],
    goal: "establish shelter and a shared research lab",
    activities: [
      "surveying shelter sites",
      "measuring stone",
      "planning a shared lab",
    ],
  },
  {
    id: "sol",
    name: "Sol",
    role: "mediator",
    home: [2, -5],
    goal: "negotiate peaceful knowledge-sharing agreements",
    activities: [
      "listening to settlers",
      "recording agreements",
      "visiting the commons",
    ],
  },
];

export class Kernel {
  constructor(storage) {
    this.storage = storage;
    for (const sql of [
      "CREATE TABLE IF NOT EXISTS world(id INTEGER PRIMARY KEY,seed INTEGER,radius INTEGER,members INTEGER)",
      "INSERT OR IGNORE INTO world VALUES(1,738291,512,0)",
      "CREATE TABLE IF NOT EXISTS players(id TEXT PRIMARY KEY,name TEXT UNIQUE COLLATE NOCASE,data TEXT)",
      "CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY,player TEXT,expires REAL)",
      "CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY,tx TEXT,account TEXT,amount INTEGER,reason TEXT,created REAL)",
      "CREATE INDEX IF NOT EXISTS ledger_account ON ledger(account)",
      "CREATE TABLE IF NOT EXISTS requests(player TEXT,key TEXT,payload TEXT,result TEXT,PRIMARY KEY(player,key))",
      "CREATE TABLE IF NOT EXISTS buildings(id TEXT PRIMARY KEY,data TEXT)",
      "CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,data TEXT)",
      "CREATE TABLE IF NOT EXISTS conversations(id INTEGER PRIMARY KEY,player TEXT,npc TEXT,text TEXT,reply TEXT)",
      "CREATE INDEX IF NOT EXISTS conversation_owner ON conversations(player,npc,id)",
      "CREATE TABLE IF NOT EXISTS ai_budget(day TEXT PRIMARY KEY,used INTEGER)",
    ])
      storage.exec(sql);
    this.players = new Map(
      storage.exec("SELECT data FROM players").map((r) => {
        const p = JSON.parse(r.data);
        return [p.id, p];
      }),
    );
    this.world = {
      ...storage.exec("SELECT seed,radius,members FROM world")[0],
    };
    this.buildings = storage
      .exec("SELECT data FROM buildings")
      .map((r) => JSON.parse(r.data));
    this.messages = storage
      .exec("SELECT id,data FROM messages ORDER BY id DESC LIMIT 40")
      .reverse()
      .map((r) => ({ ...JSON.parse(r.data), id: r.id }));
    this.sessions = new Map();
    this.inputs = new Map();
    this.online = new Set();
    this.dirty = new Set();
    this.sinceFlush = 0;
  }
  save(p) {
    this.storage.exec(
      "INSERT INTO players(id,name,data) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
      p.id,
      p.name,
      JSON.stringify(p),
    );
    this.dirty.delete(p.id);
  }
  atomic(fn) {
    const backup = {
      players: structuredClone(this.players),
      world: { ...this.world },
      buildings: structuredClone(this.buildings),
      messages: structuredClone(this.messages),
      dirty: new Set(this.dirty),
    };
    try {
      return this.storage.transactionSync(fn);
    } catch (e) {
      Object.assign(this, backup);
      throw e;
    }
  }
  async register(name, password) {
    if (typeof name !== "string" || !/^[A-Za-z0-9_-]{3,24}$/.test(name))
      throw Error("Use 3–24 letters, numbers, underscores or hyphens.");
    if (
      typeof password !== "string" ||
      password.length < 12 ||
      password.length > 128
    )
      throw Error("Use a password between 12 and 128 characters.");
    const salt = random(),
      hash = await passwordHash(password, salt);
    if (
      [...this.players.values()].some(
        (p) => p.name.toLowerCase() === name.toLowerCase(),
      )
    )
      throw Error("That name is already registered.");
    if (this.players.size >= 1000)
      throw Error(
        "This free alpha world has reached its 1000-account cap. Existing settlers can still log in.",
      );
    const p = {
      id: crypto.randomUUID(),
      name,
      salt,
      hash,
      joined: false,
      x: 0,
      y: 0,
      wood: 20,
      stone: 10,
      food: 5,
      research: 0,
      reputation: 0,
      credits: 0,
      lastGather: 0,
      lastResearch: 0,
      relations: [],
    };
    this.storage.exec(
      "INSERT INTO players VALUES(?,?,?)",
      p.id,
      name,
      JSON.stringify(p),
    );
    this.players.set(p.id, p);
    return this.session(p.id);
  }
  async login(name, password) {
    if (
      typeof name !== "string" ||
      typeof password !== "string" ||
      password.length > 128
    )
      throw Error("Invalid name or password.");
    const p = [...this.players.values()].find(
      (p) => p.name.toLowerCase() === name.toLowerCase(),
    );
    const candidate = await passwordHash(password, p?.salt || "0".repeat(64));
    // Hash strings have fixed length; compare every character without early exit.
    let mismatch = 0;
    for (let i = 0; i < 64; i++)
      mismatch |=
        candidate.charCodeAt(i) ^ (p?.hash || "0".repeat(64)).charCodeAt(i);
    if (!p || mismatch) throw Error("Invalid name or password.");
    return this.session(p.id);
  }
  async session(id) {
    const token = random(),
      hash = await digest(token),
      expires = Date.now() + 30 * 86400000;
    this.storage.exec("DELETE FROM sessions WHERE expires<?", Date.now());
    this.storage.exec("INSERT INTO sessions VALUES(?,?,?)", hash, id, expires);
    this.sessions.set(hash, { player: id, expires });
    return { token, player: this.player(id) };
  }
  async authenticate(token) {
    if (typeof token !== "string" || token.length > 128)
      throw Error("Session expired. Please log in.");
    const hash = await digest(token);
    let session = this.sessions.get(hash);
    if (!session) {
      session = this.storage.exec(
        "SELECT player,expires FROM sessions WHERE hash=?",
        hash,
      )[0];
      if (session) this.sessions.set(hash, session);
    }
    if (!session || session.expires < Date.now())
      throw Error("Session expired. Please log in.");
    return session.player;
  }
  async logout(token) {
    const hash = await digest(token);
    this.sessions.delete(hash);
    this.storage.exec("DELETE FROM sessions WHERE hash=?", hash);
  }
  player(id) {
    const p = this.players.get(id);
    if (!p) throw Error("Player not found.");
    const {
      salt,
      hash,
      joined,
      lastGather,
      lastResearch,
      relations,
      ...publicPlayer
    } = p;
    return { ...publicPlayer };
  }
  join(id) {
    const p = this.players.get(id);
    if (!p) throw Error("Player not found.");
    if (!p.joined)
      this.atomic(() => {
        p.joined = true;
        p.credits = 100;
        this.world.radius += 32;
        this.world.members++;
        this.storage.exec(
          "UPDATE world SET radius=?,members=?",
          this.world.radius,
          this.world.members,
        );
        this.post(
          "system:issuance",
          id,
          100,
          "Alpha starter credits; no cash value",
        );
        this.save(p);
      });
    return this.snapshot(id);
  }
  post(debit, credit, amount, reason) {
    const tx = crypto.randomUUID(),
      now = Date.now() / 1000;
    this.storage.exec(
      "INSERT INTO ledger(tx,account,amount,reason,created) VALUES(?,?,?,?,?),(?,?,?,?,?)",
      tx,
      debit,
      -amount,
      reason,
      now,
      tx,
      credit,
      amount,
      reason,
      now,
    );
  }
  terrain(x, y) {
    x = Math.floor(x);
    y = Math.floor(y);
    if (Math.abs(x) < 10 && Math.abs(y) < 10) return "meadow";
    let n =
      (Math.imul(Math.floor(x / 6), 374761393) ^
        Math.imul(Math.floor(y / 6), 668265263) ^
        this.world.seed) >>>
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
  chunk(cx, cy) {
    if (
      !Number.isSafeInteger(cx) ||
      !Number.isSafeInteger(cy) ||
      Math.abs(cx * 16) > this.world.radius + 16 ||
      Math.abs(cy * 16) > this.world.radius + 16
    )
      throw Error("This land is beyond the current frontier.");
    return {
      cx,
      cy,
      size: 16,
      tiles: Array.from({ length: 256 }, (_, i) =>
        this.terrain(cx * 16 + (i % 16), cy * 16 + Math.floor(i / 16)),
      ),
    };
  }
  passable(x, y) {
    return (
      Math.abs(x) < this.world.radius &&
      Math.abs(y) < this.world.radius &&
      this.terrain(x, y) !== "water" &&
      !this.buildings.some(
        (b) => b.x === Math.floor(x) && b.y === Math.floor(y),
      )
    );
  }
  step(dt) {
    dt = Math.max(0, Math.min(dt, 0.1));
    this.sinceFlush += dt;
    for (const [id, input] of this.inputs) {
      if (Date.now() - input.time > 300) continue;
      const p = this.players.get(id);
      if (!p) continue;
      const length = Math.max(1, Math.hypot(input.dx, input.dy)),
        speed = this.terrain(p.x, p.y) === "forest" ? 4 : 6;
      const x = p.x + (input.dx / length) * speed * dt,
        y = p.y + (input.dy / length) * speed * dt;
      const beforeX = p.x,
        beforeY = p.y;
      if (this.passable(x, p.y)) p.x = x;
      if (this.passable(p.x, y)) p.y = y;
      if (p.x !== beforeX || p.y !== beforeY) this.dirty.add(id);
    }
    if (this.sinceFlush >= 10) {
      this.flush();
      this.sinceFlush = 0;
    }
  }
  flush() {
    if (!this.dirty.size) return;
    const pending = new Set(this.dirty);
    try {
      this.storage.transactionSync(() => {
        for (const id of pending) this.save(this.players.get(id));
      });
    } catch (error) {
      // A rolled-back batch must retry every position, including earlier writes.
      for (const id of pending) this.dirty.add(id);
      throw error;
    }
  }
  disconnect(id) {
    this.inputs.delete(id);
    this.online.delete(id);
    if (this.dirty.has(id)) this.save(this.players.get(id));
  }
  npcs() {
    const phase = Date.now() / 35000;
    return NPCS.map((n, i) => ({
      ...n,
      x: n.home[0] + Math.sin(phase + i) * 2,
      y: n.home[1] + Math.cos(phase + i) * 2,
      activity:
        n.activities[Math.floor(Date.now() / 60000 + i) % n.activities.length],
    }));
  }
  snapshot(id) {
    const p = this.player(id);
    return {
      type: "snapshot",
      world: { ...this.world },
      self: p,
      players: [...this.online]
        .filter((q) => q !== id)
        .map((q) => this.player(q))
        .filter((q) => Math.hypot(q.x - p.x, q.y - p.y) < 80),
      npcs: this.npcs(),
      buildings: this.buildings.filter(
        (b) => Math.abs(b.x - p.x) < 80 && Math.abs(b.y - p.y) < 80,
      ),
      messages: this.messages,
    };
  }
  ledger(id) {
    return this.storage.exec(
      "SELECT tx,amount,reason,created FROM ledger WHERE account=? ORDER BY id DESC LIMIT 100",
      id,
    );
  }
  command(id, data) {
    if (
      !data ||
      typeof data !== "object" ||
      Array.isArray(data) ||
      !this.players.get(id)?.joined
    )
      throw Error("Join the world first.");
    if (data.type === "input") {
      if (
        ![data.dx, data.dy].every(
          (v) =>
            typeof v === "number" && Number.isFinite(v) && Math.abs(v) <= 1,
        )
      )
        throw Error("Invalid movement input.");
      this.inputs.set(id, { dx: data.dx, dy: data.dy, time: Date.now() });
      return { ok: true };
    }
    if (
      ![
        "gather",
        "build",
        "research",
        "transfer",
        "chat",
        "talk",
        "diplomacy",
        "home",
      ].includes(data.type)
    )
      throw Error("Unknown command.");
    if (
      typeof data.request_id !== "string" ||
      data.request_id.length < 1 ||
      data.request_id.length > 80
    )
      throw Error("A unique request_id is required.");
    const payload = JSON.stringify(
      Object.fromEntries(
        Object.entries(data).sort(([a], [b]) => a.localeCompare(b)),
      ),
    );
    const old = this.storage.exec(
      "SELECT payload,result FROM requests WHERE player=? AND key=?",
      id,
      data.request_id,
    )[0];
    if (old) {
      if (old.payload !== payload)
        throw Error("Request ID already used for a different action.");
      return JSON.parse(old.result);
    }
    return this.atomic(() => {
      const result = this.act(id, data);
      this.storage.exec(
        "INSERT INTO requests VALUES(?,?,?,?)",
        id,
        data.request_id,
        payload,
        JSON.stringify(result),
      );
      return result;
    });
  }
  act(id, data) {
    const p = this.players.get(id),
      kind = data.type;
    if (kind === "home") {
      p.x = 0;
      p.y = 0;
      this.inputs.delete(id);
      this.save(p);
      return {
        ok: true,
        reply:
          "Returned to the protected commons. Your settlement remains where you built it.",
      };
    }
    if (kind === "transfer") {
      const q = this.players.get(data.to),
        amount = data.amount;
      if (
        !Number.isSafeInteger(amount) ||
        amount < 1 ||
        amount > 1000000 ||
        !q?.joined ||
        q === p
      )
        throw Error("Transfer a positive whole number to another settler.");
      if (p.credits < amount) throw Error("Insufficient credits.");
      p.credits -= amount;
      q.credits += amount;
      this.post(id, q.id, amount, "Player transfer; no cash value");
      this.save(p);
      this.save(q);
      return { ok: true, reply: `Transferred ${amount} experimental credits.` };
    }
    if (kind === "gather") {
      if (Date.now() - p.lastGather < 3000)
        throw Error("Rest a moment: gathering takes three seconds.");
      const terrain = this.terrain(p.x, p.y),
        resource =
          terrain === "forest" ? "wood" : terrain === "rock" ? "stone" : "food";
      p[resource] += 2;
      p.lastGather = Date.now();
      this.save(p);
      return { ok: true, reply: `Gathered 2 ${resource} from ${terrain}.` };
    }
    if (kind === "build") {
      const costs = { camp: [8, 2], farm: [10, 4], lab: [16, 10] };
      if (!Object.hasOwn(costs, data.kind))
        throw Error("Choose camp, farm or lab.");
      const [wood, stone] = costs[data.kind],
        x = Math.floor(p.x) + 1,
        y = Math.floor(p.y);
      if (p.wood < wood || p.stone < stone)
        throw Error(`A ${data.kind} needs ${wood} wood and ${stone} stone.`);
      if (Math.abs(x) < 10 && Math.abs(y) < 10)
        throw Error(
          "The commons is protected. Build at least 10 tiles from its center.",
        );
      if (
        !this.passable(x, y) ||
        [...this.online].some((id) => {
          const q = this.players.get(id);
          return Math.floor(q.x) === x && Math.floor(q.y) === y;
        })
      )
        throw Error(
          "The tile east of you is occupied or blocked. Find a clear site.",
        );
      if (this.buildings.length >= 10000)
        throw Error("The alpha world has reached its construction cap.");
      const b = { id: crypto.randomUUID(), owner: id, kind: data.kind, x, y };
      p.wood -= wood;
      p.stone -= stone;
      this.storage.exec(
        "INSERT INTO buildings VALUES(?,?)",
        b.id,
        JSON.stringify(b),
      );
      this.buildings.push(b);
      this.save(p);
      return { ok: true, reply: `Built a ${data.kind} at ${x}, ${y}.` };
    }
    if (kind === "research") {
      if (Date.now() - p.lastResearch < 10000)
        throw Error("Record your previous sample first; wait ten seconds.");
      if (p.food < 1)
        throw Error("Gather food before another field experiment.");
      const terrain = this.terrain(p.x, p.y),
        moisture = { meadow: 45, forest: 70, rock: 15, water: 100 }[terrain];
      p.food--;
      p.research++;
      p.credits += 2;
      p.lastResearch = Date.now();
      this.post("system:research", id, 2, "Field research reward");
      this.save(p);
      return {
        ok: true,
        reply: `Soil sample: ${terrain}, modeled moisture ${moisture}%. Compare forest and exposed rock. +1 research, +2 alpha credits. This is a simplified model, not measured science.`,
      };
    }
    const npc = this.npcs().find((n) => n.id === data.npc);
    if (kind === "diplomacy") {
      if (!npc) throw Error("Choose a Samaritan.");
      if (p.relations.includes(npc.id))
        return {
          ok: true,
          reply: `Your cooperation agreement with ${npc.name} is already recorded.`,
        };
      p.relations.push(npc.id);
      p.reputation++;
      this.save(p);
      return {
        ok: true,
        reply: `${npc.name} agrees to peaceful knowledge sharing. +1 reputation. No resources or authority were transferred.`,
      };
    }
    if (
      typeof data.text !== "string" ||
      !data.text.trim() ||
      data.text.trim().length > 1000
    )
      throw Error("Write a message between 1 and 1000 characters.");
    const text = data.text.trim();
    if (kind === "chat") {
      const msg = {
        sender: id,
        name: p.name,
        text,
        created: Date.now() / 1000,
      };
      const row = this.storage.exec(
        "INSERT INTO messages(data) VALUES(?) RETURNING id",
        JSON.stringify(msg),
      )[0];
      this.messages.push({ ...msg, id: row.id });
      this.messages = this.messages.slice(-40);
      return { ok: true, reply: "Message sent to world chat." };
    }
    if (!npc) throw Error("Choose a Samaritan.");
    const history = this.storage.exec(
      "SELECT text,reply FROM conversations WHERE player=? AND npc=? ORDER BY id DESC LIMIT 6",
      id,
      npc.id,
    );
    const reply = respond(npc, p, text, history);
    const row = this.storage.exec(
      "INSERT INTO conversations(player,npc,text,reply) VALUES(?,?,?,?) RETURNING id",
      id,
      npc.id,
      text,
      reply,
    )[0];
    return {
      ok: true,
      reply,
      npc: npc.name,
      remembered: history.length,
      dialogue: "contextual-rules",
      conversation_id: row.id,
    };
  }
}

function respond(n, p, text, history) {
  const words = text.toLowerCase(),
    prefix = `${p.name}, `;
  if (/help you|need|your goal|working on/.test(words))
    return (
      prefix +
      `my goal is to ${n.goal}. I am ${n.activity}. ` +
      {
        mira: "You can help by sampling soil in a meadow and a forest. Use Research at each site and tell me what changed.",
        oren: `You have ${p.wood} wood and ${p.stone} stone. A camp needs 8 wood and 2 stone. Look beyond the commons for clear ground.`,
        sol: "Ask neighbors what they need. Propose cooperation when you intend to record an agreement; conversation alone does not sign one.",
      }[n.id]
    );
  if (/remember|earlier|last time/.test(words))
    return (
      prefix +
      (history.length
        ? `last time you told me: “${history[0].text.slice(0, 180)}”. My current goal is still to ${n.goal}.`
        : "this is our first recorded conversation. What would you like us to work on?")
    );
  if (/how are|hello|^hi\b|friend|feeling/.test(words))
    return (
      prefix +
      `I am curious about what we can learn together. I have been ${n.activity}. ` +
      (history.length
        ? "I remember our earlier conversation. "
        : "It is good to meet you. ") +
      "What brought you to this world?"
    );
  if (/peace|trade|diplom|cooperat|alliance/.test(words))
    return (
      prefix +
      "I favor peaceful knowledge sharing while everyone keeps their own choices. Use Propose cooperation to record those limited terms. This conversation transfers no property, credits, or control."
    );
  if (/soil|forest|science|experiment|moisture/.test(words))
    return (
      prefix +
      `you have recorded ${p.research} field samples. Compare the same quantity across different terrain while keeping other conditions fixed. Our moisture values are a simplified simulation, not real measurements. What did your comparison show?`
    );
  if (/help|how do|where|stuck/.test(words))
    return (
      prefix +
      `I can offer guidance while I ${n.goal}. Forests provide wood, rock provides stone, and meadows provide food. Gather, then build a camp beyond the commons. Soil sampling uses one food. What are you trying to build?`
    );
  return (
    prefix +
    `you said “${text.slice(0, 180)}”. As a ${n.role}, I connect that to my aim to ${n.goal}. ` +
    (history.length ? "I am keeping our earlier conversation in mind. " : "") +
    "Are you asking for practical help, proposing cooperation, or sharing how you feel?"
  );
}
