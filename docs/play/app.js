import { snapshotFresh } from "./connection.js";
import { ChunkRetry } from "./chunk-retry.js";
const chunkRetry = new ChunkRetry();
const $ = (id) => document.getElementById(id);
const mode = new URLSearchParams(location.search).get("mode");
const modes = {
  story: "Story & conversation",
  isometric: "2.5D isometric world",
  firstperson: "First-person explorer",
};
const storage = {
  get(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {}
  },
  remove(key) {
    try {
      localStorage.removeItem(key);
    } catch {}
  },
};
let server = "",
  token = "",
  socket,
  reconnect,
  snapshot,
  view,
  keys = new Set(),
  pad = { x: 0, y: 0 },
  seenMessages = new Set(),
  connected = false,
  lastRecipients = "",
  lastSnapshot = 0;
const chunks = new Map(),
  pendingChunks = new Set();
const isLocal = ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
const feedback = (text) => {
  $("feedback").textContent = text;
};

function validatedServer(value) {
  if (!value) return "";
  const url = new URL(value);
  if (
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    (url.protocol !== "https:" &&
      !(
        url.protocol === "http:" &&
        ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)
      ))
  )
    throw new Error("Use HTTPS for a public server, or HTTP on localhost.");
  return url.href.replace(/\/$/, "");
}

async function api(path, data, auth = true) {
  if (!server)
    throw new Error(
      "The public server is not configured yet. See hosting status above.",
    );
  const response = await fetch(server + path, {
    method: data === undefined ? "GET" : "POST",
    headers: {
      ...(data === undefined ? {} : { "Content-Type": "application/json" }),
      ...(auth && token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: data === undefined ? undefined : JSON.stringify(data),
    signal: AbortSignal.timeout(15000),
  });
  const result = await response.json();
  if (!response.ok) {
    const error = new Error(
      typeof result.detail === "string"
        ? result.detail
        : `Request failed (${response.status}). Check your input.`,
    );
    error.retryAt = result.retryAt;
    throw error;
  }
  return result;
}

function addDialogue(name, text) {
  const p = document.createElement("p"),
    strong = document.createElement("strong");
  strong.textContent = name;
  p.append(strong, document.createTextNode(text));
  $("dialogue").append(p);
  while ($("dialogue").children.length > 100) $("dialogue").firstChild.remove();
  $("dialogue").scrollTop = $("dialogue").scrollHeight;
}

async function action(data) {
  if (!connected) {
    feedback("Disconnected. Actions are paused until the server reconnects.");
    return null;
  }
  try {
    const result = await api("/api/command", {
      ...data,
      request_id: crypto.randomUUID(),
    });
    feedback(result.reply || "Done.");
    return result;
  } catch (error) {
    feedback(error.message);
    return null;
  }
}

function tile(x, y) {
  const cx = Math.floor(x / 16),
    cy = Math.floor(y / 16),
    chunk = chunks.get(`${cx},${cy}`);
  if (!chunk) return "unknown";
  return chunk.tiles[
    (((Math.floor(y) % 16) + 16) % 16) * 16 + (((Math.floor(x) % 16) + 16) % 16)
  ];
}

async function loadChunks(p) {
  const cx = Math.floor(p.x / 16),
    cy = Math.floor(p.y / 16);
  for (let y = cy - 1; y <= cy + 1; y++)
    for (let x = cx - 1; x <= cx + 1; x++) {
      const key = `${x},${y}`;
      if (chunks.has(key) || pendingChunks.has(key) || !chunkRetry.ready(key))
        continue;
      pendingChunks.add(key);
      api(`/api/chunk?cx=${x}&cy=${y}`)
        .then((chunk) => {
          chunks.set(key, chunk);
          chunkRetry.succeeded(key);
        })
        .catch((error) => {
          chunkRetry.failed(key, error);
          feedback(error.message);
        })
        .finally(() => pendingChunks.delete(key));
    }
  // Nearby cache stays bounded during long journeys.
  for (const [key, chunk] of chunks)
    if (Math.abs(chunk.cx - cx) > 4 || Math.abs(chunk.cy - cy) > 4)
      chunks.delete(key);
}

function display(state) {
  if (state.notice && state.notice !== snapshot?.notice) feedback(state.notice);
  snapshot = state;
  $("player-name").textContent = state.self.name;
  $("coords").textContent =
    `${state.self.x.toFixed(1)}, ${state.self.y.toFixed(1)} · ${state.world.members} settlers · ${state.world.radius * 2}² tiles`;
  const inventory = [
    ["Wood", state.self.wood],
    ["Stone", state.self.stone],
    ["Food", state.self.food],
    ["Research", state.self.research],
    ["Credits", state.self.credits],
    ["Reputation", state.self.reputation],
  ];
  $("inventory").replaceChildren(
    ...inventory.map(([label, value]) => {
      const s = document.createElement("span");
      s.textContent = `${label} · ${value}`;
      return s;
    }),
  );
  const recipients = JSON.stringify(
    state.players.map((p) => ({ id: p.id, name: p.name })),
  );
  if (recipients !== lastRecipients) {
    lastRecipients = recipients;
    const selected = $("recipient").value;
    $("recipient").replaceChildren(
      ...state.players.map((p) => {
        const o = document.createElement("option");
        o.value = p.id;
        o.textContent = p.name;
        return o;
      }),
    );
    if (state.players.some((p) => p.id === selected))
      $("recipient").value = selected;
  }
  for (const msg of state.messages)
    if (!seenMessages.has(msg.id)) {
      seenMessages.add(msg.id);
      addDialogue(`${msg.name} · world`, msg.text);
    }
  if (seenMessages.size > 1000)
    seenMessages = new Set(state.messages.map((m) => m.id));
  loadChunks(state.self);
  view?.update(state);
}

function connect() {
  clearTimeout(reconnect);
  lastSnapshot = 0;
  socket = new WebSocket(server.replace(/^http/, "ws") + "/ws");
  socket.onopen = () => socket.send(JSON.stringify({ token }));
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "snapshot") {
      lastSnapshot = performance.now();
      connected = true;
      $("connection").textContent = "● Connected to shared world";
      display(data);
    } else if (data.type === "error") feedback(data.message);
    else if (data.reply) feedback(data.reply);
  };
  socket.onclose = (event) => {
    connected = false;
    keys.clear();
    pad = { x: 0, y: 0 };
    $("connection").textContent = "○ Disconnected · actions paused";
    if (event.code === 1008) {
      storage.remove(`eov:token:${server}`);
      $("entry-error").textContent =
        "Session expired or server access denied. Please log in again.";
      $("entry").hidden = false;
      $("session").hidden = true;
      return;
    }
    feedback(
      event.code === 1013
        ? "World server is full. Retrying shortly."
        : "Connection lost. Your saved world stays on the server. Reconnecting…",
    );
    reconnect = setTimeout(connect, 3000 + Math.random() * 2000);
  };
  socket.onerror = () => {
    $("connection").textContent = "○ Cannot reach world server";
  };
}

async function start() {
  const initial = await api("/api/world");
  $("entry").hidden = true;
  $("session").hidden = false;
  $("mode-label").textContent = modes[mode];
  const module = await import(`./${mode}.js`);
  view = module.mount($("scene"), { tile, feedback, action, api });
  $("controls-help").textContent =
    mode === "firstperson"
      ? "WASD to walk · ← → to turn · drag to look · E gather"
      : mode === "isometric"
        ? "WASD / arrows to walk · E gather · R sample soil"
        : "Choose a village scene and speak with its inhabitants";
  display(initial);
  connect();
}

async function authenticate(create) {
  $("entry-error").textContent = "";
  if (!$("auth").reportValidity()) return;
  $("join").disabled = $("login").disabled = true;
  try {
    const result = await api(
      create ? "/api/session" : "/api/login",
      { name: $("name").value, password: $("password").value },
      false,
    );
    token = result.token;
    storage.set(`eov:token:${server}`, token);
    $("password").value = "";
    await start();
  } catch (error) {
    $("entry-error").textContent = error.message;
  } finally {
    $("join").disabled = $("login").disabled = false;
  }
}

let lastInputAt = 0;
let wasMoving = false;
function inputTick() {
  if (!connected || socket?.readyState !== WebSocket.OPEN) return;
  let x = pad.x + (keys.has("d") ? 1 : 0) - (keys.has("a") ? 1 : 0),
    y =
      pad.y +
      (keys.has("s") || keys.has("arrowdown") ? 1 : 0) -
      (keys.has("w") || keys.has("arrowup") ? 1 : 0);
  if (mode !== "firstperson")
    x += (keys.has("arrowright") ? 1 : 0) - (keys.has("arrowleft") ? 1 : 0);
  else
    view?.turn(
      ((keys.has("arrowright") ? 1 : 0) - (keys.has("arrowleft") ? 1 : 0)) *
        0.085,
    );
  x = Math.max(-1, Math.min(1, x));
  y = Math.max(-1, Math.min(1, y));
  const direction = view?.direction ? view.direction(x, y) : { dx: x, dy: y };
  const length = Math.max(1, Math.hypot(direction.dx, direction.dy));
  direction.dx /= length;
  direction.dy /= length;
  const moving = !!(direction.dx || direction.dy);
  const now = performance.now();
  // Keep active movement below the server's 300ms expiry. Idle clients only
  // heartbeat every 30 seconds to conserve the shared free request allowance.
  if (
    moving ? now - lastInputAt < 150 : !wasMoving && now - lastInputAt < 30000
  )
    return;
  socket.send(JSON.stringify({ type: "input", ...direction }));
  lastInputAt = now;
  wasMoving = moving;
}

if (modes[mode]) {
  $("landing").hidden = true;
  $("game").hidden = false;
  $("entry-title").textContent = modes[mode];
  try {
    const config = await fetch("./config.json").then((r) => r.json());
    server = validatedServer(
      storage.get("eov:server") ||
        (isLocal ? location.origin : config.serverUrl || ""),
    );
    $("server-url").value = server;
    if (server) {
      const health = await api("/health", undefined, false);
      $("server-status").textContent =
        `World server ready · ${health.online} online · Expect bugs — alpha`;
    } else $("server-status").textContent = config.notice;
    token = storage.get(`eov:token:${server}`) || "";
    if (token)
      try {
        await start();
      } catch (error) {
        $("entry-error").textContent = error.message;
      }
  } catch (error) {
    $("server-status").textContent =
      `World server unavailable: ${error.message}. You can configure another server below.`;
  }
  $("auth").onsubmit = (e) => {
    e.preventDefault();
    authenticate(true);
  };
  $("login").onclick = () => authenticate(false);
  $("server-form").onsubmit = (e) => {
    e.preventDefault();
    try {
      const next = validatedServer($("server-url").value);
      storage.set("eov:server", next);
      location.reload();
    } catch (error) {
      $("entry-error").textContent = error.message;
    }
  };
  $("logout").onclick = async () => {
    try {
      await api("/api/logout", {});
    } catch {}
    storage.remove(`eov:token:${server}`);
    clearTimeout(reconnect);
    if (socket) {
      socket.onclose = null;
      socket.close();
    }
    location.reload();
  };
  document.querySelectorAll("[data-action]").forEach(
    (button) =>
      (button.onclick = () =>
        action({
          type: button.dataset.action,
          ...(button.dataset.kind ? { kind: button.dataset.kind } : {}),
        })),
  );
  $("chat").onsubmit = async (e) => {
    e.preventDefault();
    const text = $("message").value,
      npc = $("npc").value;
    const result = await action({
      type: npc === "world" ? "chat" : "talk",
      text,
      npc,
    });
    if (result) {
      $("message").value = "";
      if (npc !== "world") {
        addDialogue(snapshot.self.name, text);
        addDialogue(result.npc || npc, result.reply);
      }
    }
  };
  $("cooperate").onclick = () => {
    if ($("npc").value === "world") {
      feedback("Choose a Samaritan before proposing cooperation.");
      return;
    }
    action({ type: "diplomacy", npc: $("npc").value });
  };
  $("ledger").onclick = async () => {
    try {
      const rows = await api("/api/ledger");
      $("ledger-rows").replaceChildren(
        ...rows.map((row) => {
          const p = document.createElement("p");
          p.textContent = `${row.amount > 0 ? "+" : ""}${row.amount} · ${row.reason}`;
          return p;
        }),
      );
    } catch (error) {
      feedback(error.message);
    }
  };
  $("agent-journal").onclick = async () => {
    try {
      const data = await api("/api/agents");
      const lines = data.journal.length
        ? data.journal.map(
            (row) =>
              `${new Date(row.created).toLocaleString()} · ${row.agent} · ${row.status}: ${row.intention} ${row.consequence}`,
          )
        : ["No independent decisions recorded yet."];
      lines.push(
        data.nextCycle
          ? `Next scheduled decision: ${new Date(data.nextCycle).toLocaleString()}`
          : "Background reasoning is not scheduled on this server.",
      );
      $("agent-journal-rows").replaceChildren(
        ...lines.map((text) => {
          const p = document.createElement("p");
          p.textContent = text;
          return p;
        }),
      );
    } catch (error) {
      feedback(error.message);
    }
  };
  $("transfer").onsubmit = (e) => {
    e.preventDefault();
    action({
      type: "transfer",
      to: $("recipient").value,
      amount: Number($("amount").value),
    });
  };
  window.addEventListener("keydown", (e) => {
    if (typeof e.key !== "string" || mode === "story") return;
    if (
      ["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(
        document.activeElement.tagName,
      )
    )
      return;
    const key = e.key.toLowerCase();
    if (
      [
        "w",
        "a",
        "s",
        "d",
        "arrowup",
        "arrowdown",
        "arrowleft",
        "arrowright",
      ].includes(key)
    ) {
      e.preventDefault();
      keys.add(key);
    }
    if (!e.repeat && key === "e") action({ type: "gather" });
    if (!e.repeat && key === "r") action({ type: "research" });
  });
  window.addEventListener("keyup", (e) => keys.delete(e.key?.toLowerCase()));
  const stop = () => {
    keys.clear();
    pad = { x: 0, y: 0 };
  };
  window.addEventListener("blur", stop);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
  });
  document.querySelectorAll("[data-dx]").forEach((button) => {
    let started = 0;
    button.onpointerdown = (e) => {
      e.preventDefault();
      button.setPointerCapture(e.pointerId);
      started = performance.now();
      pad = { x: Number(button.dataset.dx), y: Number(button.dataset.dy) };
      inputTick();
    };
    button.onpointerup = () => {
      setTimeout(
        () => {
          pad = { x: 0, y: 0 };
        },
        Math.max(0, 120 - (performance.now() - started)),
      );
    };
    button.onpointercancel = () => {
      pad = { x: 0, y: 0 };
    };
  });
  setInterval(inputTick, 50);
  setInterval(() => {
    if (connected && !snapshotFresh(lastSnapshot, performance.now())) {
      connected = false;
      keys.clear();
      pad = { x: 0, y: 0 };
      $("connection").textContent =
        "○ Server stopped responding · actions paused";
      feedback("No world updates for five seconds. Reconnecting…");
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
      reconnect = setTimeout(connect, 1000);
    }
  }, 1000);
}
