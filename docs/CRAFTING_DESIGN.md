# Procedural models and workbench construction

User choice: procedural shapes and AI-assisted schematics on the existing free runtime.

Wood is processed into planks (one wood yields two planks). Players design a
workbench from a 2–4 by 2–4 by 2–4 block grid. A functional bench must retain a
complete plank top and four supported corner legs; supports may be plank or stone.
Other blocks can be edited freely. Bench blocks are quarter-tile size. Structure
blocks are one tile. The simplified support rule checks connected geometry rooted
at ground level; it is not an engineering or load-bearing calculation.

A bench can be crafted without another bench. Construction of structures requires
an owned bench within four tiles. Saved schematics are account-owned and persist
separately from frequent world snapshots. Building consumes one plank or stone per
block. Placement is east of the player and validates the entire rectangular
footprint, existing buildings, players, water, frontier and protected commons.
Alpha constructions occupy a solid footprint; traversable interiors come later.

AI maps a description to bounded template parameters using the existing Workers AI
model and shared daily allowance. Generated drafts are persisted before inference
as procedural fallbacks, so retries and restarts cannot repeatedly consume AI.
AI failure, invalid output or quota exhaustion retains the editable fallback.
Players explicitly save and construct drafts; AI cannot execute game commands.

Both graphics modes consume the same immutable generated block geometry. Shared
seeded visual descriptors vary tree shapes, character appearance and ground colors
without rerolling the canonical terrain, changing movement or downloading models.
Story mode can use the same workshop without importing world renderers.

Free alpha limits: 20 saved schematics per account; 64 blocks per schematic;
10 design requests per account per UTC day (counted even when AI is unavailable), also within the existing shared
50-call AI allowance. Existing accounts default to zero planks; no data reset.
