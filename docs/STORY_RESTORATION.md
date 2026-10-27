# Main726 story restoration — 2026-09-22

Source: Main726 commit `a1eecd907de8a9b52827c6dd37e074fbeb4353e9`.

The owner asked to retain the new first-person and isometric clients, restore the original story/conversation foundation, and preserve existing autonomy rather than hard-code another replacement.

## Source mapping

- `frontend/src/pages/VillageExplorer.jsx`: location sidebar, central narrative conversation, NPC selection, all places open, history and milestone progression. Adapted into `docs/play/story.js` and story-scoped CSS.
- `backend/server.py` / `VILLAGE_LOCATIONS`, `NPC_DATA`: seven locations and eight full character profiles extracted verbatim into `docs/play/story-data.js`. The Hooded Stranger appears in source locations but has no full NPC_DATA profile; the small traveler profile is explicitly an adaptation.
- `backend/server.py` / `story_chat`, `get_npc_system_prompt`: narrator style, distinctive NPC voices, location context and conversation continuity adapted into `cloudflare/src/story.js`. Uses Workers AI instead of paid Emergent/GPT access.
- `backend/ai_autonomy_router.py`: retained; originally identical between main and Main726. The 2026-09-23 update fixes only its broken Emergent SDK conversation call (key selection, UserMessage, awaited text response). Its personality, free-will, relationship and AI-to-AI mechanisms are not replaced. The source combines model dialogue with weighted action rules, not an unconstrained self-running intelligence.

## Working free-runtime adaptation

Authenticated `/api/story` returns the player's current scene, milestone and last 60 saved turns for that location. `/api/story/command` accepts replay-keyed visit/talk actions. New locations award 20 narrative XP; conversations award 10. XP is not currency. History and progression survive reconnects and server eviction, are scoped to the authenticated account, and can resume on another device. Model context includes previous dialogue and actual shared resources, coordinates and nearby construction.

Story scene travel does not teleport the physical avatar, grow the world or spend resources. Use the existing sidebar and graphical modes for explicit world actions and diplomacy. First-person and isometric rendering is preserved. Conversation is model-generated when available, with a labelled contextual fallback. The free daily AI cap is shared with Samaritan chat.

## Deliberate boundaries and unfinished integration

This restores the core narrative experience, not every Main726 page or backend router. The old MongoDB conversation database is not migrated; paid GPT credentials are not copied. Live outer-world news, the old quest/economy/marketplace screens, global dataspace publication and the legacy background autonomy service are not deployed on the free Worker. Original source remains in Git for subsequent integration.

The 2026-09-23 free-runtime adaptation removes ambient activity rotation for Mira, Oren and Sol. Stored perceptions and memories feed bounded model decisions; validated consequences commit with an activity journal. It preserves the original design's distinction between personality, remembered context and actions but does not deploy the Python/MongoDB runtime or reproduce every legacy capability. The eight original village profiles remain narrative characters. See PERSISTENT_WORLD_PLAN.md and HANDOFF.md for scheduling, limits and source boundaries.

## Verification

Three added Node tests cover all seven locations, persisted scene history, identity isolation, replay protection, unchanged world/resources, narrator/NPC prompts, remembered context and exhausted AI quota. Browser inspection exercised Oracle travel, targeted dialogue and saved progression. Review found uncertain-retry duplication and draft loss; the client now reuses the pending key and preserves text edited while awaiting a response.
