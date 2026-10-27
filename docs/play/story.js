// Ported from Main726 VillageExplorer: locations, narrator, NPCs, history and XP.
// Story mode imports no graphics renderer; explicit world actions stay in the sidebar.
import { VILLAGE_LOCATIONS } from "./story-data.js";
export function mount(container, { api, feedback }) {
  document.body.classList.add("story-mode");
  container.innerHTML = `<div class="village-story">
    <nav class="village-places" aria-label="Village locations"><div class="eyebrow">EXPLORE THE VILLAGE</div><p id="story-progress">Loading your journey…</p><div id="story-locations"></div><p class="muted">All locations open</p><a href="?mode=isometric">Explore & build ↗</a><a href="?mode=firstperson">First person ↗</a></nav>
    <article class="village-conversation"><header><div class="eyebrow">THE ECHOES / STORY MODE</div><h1 id="story-title">The Hollow Square</h1><p id="story-atmosphere"></p><p id="story-souls"></p></header>
      <div id="story-transcript" role="log" aria-label="Story conversation" aria-live="polite"></div>
      <form id="story-form"><label>Speak with<select id="story-speaker"></select></label><div id="story-suggestions"></div><label>Your words or story action<textarea id="story-message" maxlength="1000" rows="3" required placeholder="Speak, observe, ask a question, or describe your next action…"></textarea></label><div class="story-send-row"><span id="story-status">Conversations are saved with your account.</span><button type="submit">Send to the Echoes</button></div></form>
    </article></div>`;
  const $ = (id) => container.querySelector("#" + id);
  let pendingSubmission;
  const retry = document.createElement("button");
  retry.type = "button";
  retry.textContent = "Retry pending action";
  retry.hidden = true;
  $("story-form").append(retry);
  retry.onclick = () => pendingSubmission && send(pendingSubmission.data);
  let state,
    busy = false,
    currentPlayer;
  function message(speaker, text, role) {
    const card = document.createElement("section"),
      label = document.createElement("strong"),
      body = document.createElement("p");
    card.className = "story-turn " + role;
    label.textContent = speaker;
    body.textContent = text;
    card.append(label, body);
    $("story-transcript").append(card);
  }
  function render() {
    const location = VILLAGE_LOCATIONS.find(
      (l) => l.id === state.profile.location,
    );
    $("story-title").textContent = location.name;
    $("story-atmosphere").textContent = location.atmosphere;
    $("story-souls").textContent = location.npcs.join(" · ");
    $("story-progress").textContent =
      `${state.milestone} · ${state.profile.xp} XP · ${state.profile.visits.length}/7 places`;
    $("story-locations").replaceChildren(
      ...VILLAGE_LOCATIONS.map((l) => {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = l.name;
        b.setAttribute("aria-current", String(l.id === location.id));
        b.onclick = () => send({ type: "visit", location: l.id });
        b.disabled = busy;
        return b;
      }),
    );
    const oldSpeaker = $("story-speaker").value;
    $("story-speaker").replaceChildren(
      ...["Narrator", ...location.npcs, "Mira", "Oren", "Sol"].map((name) => {
        const o = document.createElement("option");
        o.value = o.textContent = name;
        return o;
      }),
    );
    if ([...$("story-speaker").options].some((o) => o.value === oldSpeaker))
      $("story-speaker").value = oldSpeaker;
    $("story-suggestions").replaceChildren(
      ...location.available_actions.slice(0, 4).map((action) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "quiet";
        b.textContent = action.replaceAll("_", " ");
        b.onclick = () => {
          $("story-message").value =
            `I would like to ${action.replaceAll("_", " ")}. What do I notice, and who can help?`;
          $("story-message").focus();
        };
        return b;
      }),
    );
    $("story-transcript").replaceChildren();
    message(
      "Narrator",
      location.description + "\n\n" + location.atmosphere,
      "narrator",
    );
    for (const turn of state.history) {
      message(currentPlayer || "You", turn.text, "player");
      message(turn.speaker, turn.reply, "reply");
    }
    $("story-transcript").scrollTop = $("story-transcript").scrollHeight;
    $("story-status").textContent =
      state.history.at(-1)?.source === "contextual-fallback"
        ? "Contextual response · AI unavailable or daily allowance reached. History saved."
        : "Conversations are saved with your account.";
  }
  async function load() {
    state = await api("/api/story");
    render();
  }
  async function send(data) {
    if (busy) return;
    if (pendingSubmission && JSON.stringify(pendingSubmission.data) !== JSON.stringify(data)) {
      $("story-status").textContent = "Resolve the pending action with Retry before submitting another. Your draft is preserved.";
      return;
    }
    pendingSubmission ||= {data, request_id:crypto.randomUUID()};
    busy = true;
    $("story-form").querySelector('button[type="submit"]').disabled = true;
    $("story-status").textContent =
      data.type === "talk" ? "The Echoes are listening…" : "Travelling…";
    try {
      await api("/api/story/command", {
        ...data,
        request_id: pendingSubmission.request_id,
      });
      if (data.type === "talk" && $("story-message").value.trim() === data.text) $("story-message").value = "";
      busy = false;
      await load();
      pendingSubmission = null;
      retry.hidden = true;
    } catch (error) {
      $("story-status").textContent = error.message;
      feedback(error.message);
      retry.hidden = false;
    } finally {
      busy = false;
      $("story-form").querySelector('button[type="submit"]').disabled = false;
    }
  }
  $("story-form").onsubmit = (e) => {
    e.preventDefault();
    if (state)
      send({
        type: "talk",
        location: state.profile.location,
        speaker: $("story-speaker").value,
        text: $("story-message").value.trim(),
      });
  };
  $("story-message").onkeydown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      $("story-form").requestSubmit();
    }
  };
  load().catch((error) => {
    $("story-status").textContent =
      "Story service unavailable on this server: " + error.message;
  });
  return {
    update(snapshot) {
      currentPlayer = snapshot.self.name;
    },
  };
}
