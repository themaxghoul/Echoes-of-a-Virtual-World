# Trading design

## Player exchange

The bottom toolbar opens a trade dialog in Story, isometric, or first-person mode. Its participant list contains online settlers within the nearby interaction range plus Mira, Oren, and Sol. A player proposes one material and amount in exchange for another material and amount. Wood, planks, stone, food, and research are supported; experimental credits and real money are excluded.

An offer is durable and appears in both participants' offer lists. The recipient explicitly accepts or rejects it. Until acceptance, neither inventory changes. The Durable Object rechecks both balances and applies both transfers in a single SQLite transaction, then marks the offer accepted. Rejected offers move no materials. An offer cannot be accepted twice; if either balance has changed, it expires without a transfer. There is no escrow, so an offer can become unfulfillable while pending.

Only an online, nearby player may receive a new offer. The recipient identity comes from the authenticated server state, never from a client-supplied display name. Amounts are whole numbers capped at 100 per side.

## Samaritan delivery

The player can ask a Samaritan whether they currently need a material. Workers AI may return no request or one specific request for 1–5 units of wood, stone, or food, with a short reason tied to the agent's own goal and supplies. The result is validated against this fixed resource allowlist and recorded in Durable Object SQLite; dialogue text cannot create a request or transfer inventory. The shared AI allowance and a per-player daily request cap protect the free runtime.

If a specific open request exists, the player explicitly chooses Deliver. The server checks that it remains open and that the player has the exact amount, then atomically debits the player, credits the Samaritan's personal supplies, records the request as delivered, and appends the event to the Samaritan's persistent memory. Only one delivery can fulfill a request. A Samaritan can decline to request materials; invalid or unavailable model responses do not create a request.

These are in-game material interactions, not financial transactions. They do not issue credits, promise earnings, integrate Bitcoin, or imply real-world value.

## Holdings privacy

The inventory values are removed from the always-visible identity panel and shown
in a private modal opened from the Inventory toolbar control. That modal is gated
until all other menus and dialogs are closed. Snapshots sent to nearby participants
contain only player identity and position, not their material, research, credit, or
reputation balances. An authenticated settler still receives their own balances so
their client can display and use their inventory.
