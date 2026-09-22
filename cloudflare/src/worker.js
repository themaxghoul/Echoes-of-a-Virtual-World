import { DurableObject } from "cloudflare:workers";
import { Kernel } from "./kernel.js";
import { generateDialogue } from "./dialogue.js";
import { Story } from "./story.js";

const json = (value, status = 200) =>
  Response.json(value, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
async function readJson(request) {
  if (!request.body) throw Error("A JSON body is required.");
  const reader = request.body.getReader(),
    parts = [];
  let length = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    length += value.length;
    if (length > 8192) {
      await reader.cancel();
      throw Error("Request too large.");
    }
    parts.push(value);
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const part of parts) {
    bytes.set(part, offset);
    offset += part.length;
  }
  return JSON.parse(new TextDecoder().decode(bytes));
}

export class World extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.game = new Kernel({
      exec: (sql, ...args) => ctx.storage.sql.exec(sql, ...args).toArray(),
      transactionSync: (fn) => ctx.storage.transactionSync(fn),
    });
    this.clients = new Map();
    this.story = new Story(this.game);
    this.limits = new Map();
    this.timer = null;
    this.previous = 0;
    this.ticks = 0;
    this.pendingTalk = new Map();
  }
  rate(key, count, period) {
    const now = Date.now();
    let bucket = this.limits.get(key) || { start: now, count: 0 };
    if (now - bucket.start >= period) bucket = { start: now, count: 0 };
    if (++bucket.count > count)
      throw Error("Too many requests. Please wait a moment.");
    this.limits.set(key, bucket);
    if (this.limits.size > 10000)
      for (const [key, value] of this.limits)
        if (now - value.start > 3600000) this.limits.delete(key);
  }
  startTick() {
    if (this.timer) return;
    this.previous = Date.now();
    this.timer = setInterval(() => {
      try {
        const now = Date.now();
        this.game.step((now - this.previous) / 1000);
        this.previous = now;
        if (++this.ticks % 2 === 0)
          for (const [ws, info] of this.clients) {
            if (!info.id) continue;
            try {
              ws.send(JSON.stringify(this.game.snapshot(info.id)));
            } catch {
              this.remove(ws);
            }
          }
      } catch (error) {
        console.error(
          JSON.stringify({
            event: "world_tick_failed",
            message: error.message,
          }),
        );
        for (const ws of this.clients.keys()) {
          try {
            ws.close(1011, "World update failed; reconnect shortly.");
          } catch {}
          this.remove(ws);
        }
      }
    }, 50);
  }
  remove(ws) {
    const info = this.clients.get(ws);
    if (!info) return;
    clearTimeout(info.timeout);
    this.clients.delete(ws);
    if (info.id && ![...this.clients.values()].some((c) => c.id === info.id))
      this.game.disconnect(info.id);
    if (!this.clients.size && this.timer) {
      clearInterval(this.timer);
      this.timer = null;
      this.game.flush();
    }
  }
  async fetch(request) {
    const url = new URL(request.url),
      path = url.pathname;
    if (path === "/ws") return this.upgrade(request);
    if (path === "/health")
      return json({
        status: "ok",
        protocol: 1,
        economy: "experimental-no-cash-value",
        dialogue: this.env.AI
          ? "workers-ai-with-contextual-fallback"
          : "contextual-rules",
        online: this.game.online.size,
        hosting: "cloudflare-free",
        capacity: 16,
      });
    try {
      const ip = request.headers.get("CF-Connecting-IP") || "local";
      if (path === "/api/session" && request.method === "POST") {
        this.rate("register:" + ip, 5, 3600000);
        const body = await readJson(request);
        const result = await this.game.register(body.name, body.password);
        this.game.join(result.player.id);
        return json(result);
      }
      if (path === "/api/login" && request.method === "POST") {
        this.rate("login:" + ip, 20, 60000);
        const body = await readJson(request);
        return json(await this.game.login(body.name, body.password));
      }
      const token = request.headers
        .get("Authorization")
        ?.replace(/^Bearer /, "");
      let id;
      try {
        id = await this.game.authenticate(token);
      } catch {
        return json({ detail: "Session expired. Please log in." }, 401);
      }
      if (path === "/api/logout" && request.method === "POST") {
        await this.game.logout(token);
        for (const [ws, info] of this.clients)
          if (info.id === id) {
            ws.close(1008, "Logged out");
            this.remove(ws);
          }
        return json({ ok: true });
      }
      if (path === "/api/world" && request.method === "GET") {
        this.rate("world:" + id, 30, 10000);
        return json(this.game.join(id));
      }
      if (path === "/api/chunk" && request.method === "GET") {
        this.rate("chunk:" + id, 120, 1000);
        return json(
          this.game.chunk(
            Number(url.searchParams.get("cx")),
            Number(url.searchParams.get("cy")),
          ),
        );
      }
      if (path === "/api/ledger" && request.method === "GET") {
        this.rate("ledger:" + id, 10, 10000);
        return json(this.game.ledger(id));
      }
      if (path === "/api/story" && request.method === "GET") {
        this.rate("story-read:" + id, 20, 10000);
        return json(this.story.state(id));
      }
      if (path === "/api/story/command" && request.method === "POST") {
        this.rate("story-write:" + id, 10, 10000);
        const data = await readJson(request);
        const ai = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)
          ? null
          : this.env.AI;
        return json(await this.story.command(id, data, ai));
      }
      if (path === "/api/command" && request.method === "POST") {
        this.rate("command:" + id, 30, 10000);
        const data = await readJson(request);
        return json(
          await this.command(
            id,
            data,
            !["localhost", "127.0.0.1"].includes(url.hostname),
          ),
        );
      }
      return json({ detail: "Not found." }, 404);
    } catch (error) {
      return json(
        { detail: error.message },
        error.message.startsWith("Too many") ? 429 : 400,
      );
    }
  }
  async command(id, data, allowAI = false) {
    const existed = data?.request_id
      ? this.game.storage.exec(
          "SELECT 1 FROM requests WHERE player=? AND key=?",
          id,
          data.request_id,
        ).length > 0
      : false;
    const result = this.game.command(id, data),
      key = id + ":" + data?.request_id;
    if (this.pendingTalk.has(key)) return this.pendingTalk.get(key);
    if (existed || data?.type !== "talk" || !allowAI || !this.env.AI)
      return result;
    // Deliberately conservative application cap within the provider's free allocation.
    const day = new Date().toISOString().slice(0, 10);
    const used =
      this.game.storage.exec("SELECT used FROM ai_budget WHERE day=?", day)[0]
        ?.used || 0;
    if (used >= 50) return result;
    this.game.storage.exec(
      "INSERT INTO ai_budget VALUES(?,1) ON CONFLICT(day) DO UPDATE SET used=used+1",
      day,
    );
    const npc = this.game.npcs().find((n) => n.id === data.npc),
      history = this.game.storage.exec(
        "SELECT text,reply FROM conversations WHERE player=? AND npc=? AND id<? ORDER BY id DESC LIMIT 3",
        id,
        data.npc,
        result.conversation_id,
      );
    const task = (async () => {
      let timeout;
      try {
        const reply = await Promise.race([
          generateDialogue(
            this.env.AI,
            npc,
            this.game.player(id),
            data.text,
            history,
          ),
          new Promise((_, reject) => {
            timeout = setTimeout(() => reject(Error("Dialogue timeout")), 8000);
          }),
        ]);
        const enriched = { ...result, reply, dialogue: "workers-ai" };
        this.game.storage.transactionSync(() => {
          this.game.storage.exec(
            "UPDATE conversations SET reply=? WHERE id=? AND player=?",
            reply,
            result.conversation_id,
            id,
          );
          this.game.storage.exec(
            "UPDATE requests SET result=? WHERE player=? AND key=?",
            JSON.stringify(enriched),
            id,
            data.request_id,
          );
        });
        return enriched;
      } catch {
        return result;
      } finally {
        clearTimeout(timeout);
        this.pendingTalk.delete(key);
      }
    })();
    this.pendingTalk.set(key, task);
    return task;
  }
  upgrade(request) {
    if (request.headers.get("Upgrade")?.toLowerCase() !== "websocket")
      return json({ detail: "WebSocket upgrade required." }, 426);
    if (this.clients.size >= 20)
      return json({ detail: "Alpha server is full. Try again shortly." }, 503);
    const pair = new WebSocketPair(),
      [client, server] = Object.values(pair);
    server.accept();
    const info = { id: null, authenticating: false, lastCheck: 0 };
    this.clients.set(server, info);
    info.timeout = setTimeout(() => {
      if (!info.id) {
        server.close(1008, "Authentication required");
        this.remove(server);
      }
    }, 5000);
    server.addEventListener("message", (event) => {
      this.ctx.waitUntil(this.message(server, event.data));
    });
    server.addEventListener("close", () => this.remove(server));
    server.addEventListener("error", () => this.remove(server));
    return new Response(null, { status: 101, webSocket: client });
  }
  async message(ws, raw) {
    const info = this.clients.get(ws);
    if (!info) return;
    try {
      if (typeof raw !== "string" || raw.length > 4096) {
        ws.close(1009, "Message too large");
        this.remove(ws);
        return;
      }
      const data = JSON.parse(raw);
      if (!info.id) {
        if (info.authenticating) return;
        info.authenticating = true;
        const id = await this.game.authenticate(data?.token);
        if (!this.clients.has(ws)) return;
        if (
          (!this.game.online.has(id) && this.game.online.size >= 16) ||
          [...this.clients.values()].filter((c) => c.id === id).length >= 3
        ) {
          ws.close(1013, "Alpha capacity reached");
          this.remove(ws);
          return;
        }
        info.id = id;
        info.token = data.token;
        info.lastCheck = Date.now();
        clearTimeout(info.timeout);
        this.game.join(id);
        this.game.online.add(id);
        ws.send(JSON.stringify(this.game.snapshot(id)));
        this.startTick();
        return;
      }
      if (Date.now() - info.lastCheck > 30000) {
        await this.game.authenticate(info.token);
        info.lastCheck = Date.now();
      }
      if (!this.clients.has(ws)) return;
      const moving = data?.type === "input";
      this.rate(
        (moving ? "input:" : "command:") + info.id,
        moving ? 60 : 30,
        moving ? 1000 : 10000,
      );
      const result = this.game.command(info.id, data);
      if (!moving) ws.send(JSON.stringify({ type: "result", ...result }));
    } catch (error) {
      if (!info.id || error.message.startsWith("Session")) {
        ws.close(1008, "Authentication failed");
        this.remove(ws);
      } else
        try {
          ws.send(JSON.stringify({ type: "error", message: error.message }));
        } catch {
          this.remove(ws);
        }
    }
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url),
      origin = request.headers.get("Origin");
    if (
      url.protocol !== "https:" &&
      !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)
    ) {
      url.protocol = "https:";
      return Response.redirect(url.toString(), 308);
    }
    const allowed = (env.EOV_ORIGINS || "").split(",").concat(url.origin);
    if (origin && !allowed.includes(origin))
      return json({ detail: "Origin is not allowed." }, 403);
    const cors = {
      "Access-Control-Allow-Origin": origin || url.origin,
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Authorization, Content-Type",
      Vary: "Origin",
    };
    if (request.method === "OPTIONS")
      return new Response(null, { status: 204, headers: cors });
    if (
      !url.pathname.startsWith("/api/") &&
      !["/health", "/ws"].includes(url.pathname)
    )
      return env.ASSETS.fetch(request);
    // One coordination atom: this alpha's shared world. Never use client-chosen names here.
    const response = await env.WORLD.getByName("eov-shared-alpha-v1").fetch(
      request,
    );
    if (response.status === 101) return response;
    const result = new Response(response.body, response);
    for (const [key, value] of Object.entries(cors))
      result.headers.set(key, value);
    return result;
  },
};
