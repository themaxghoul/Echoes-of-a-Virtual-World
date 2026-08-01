# EoV next-task log: depth before VR

Updated: 2026-08-01

The next development phase prioritizes embodied work, survival, specialization, institutions, and a two-week economic bootstrap. VR remains a future perception/input adapter and is not a near-term dependency.

## 1. Chronological tool accessibility

Tools enter an entity's practical reach only when its prerequisites are satisfied. A recipe list does not grant competence, materials, energy, a workstation, or safe execution.

1. **Body and surroundings:** hands, carrying, observation, voice, leverage, containers, found shelter, naturally available fuel and water.
2. **Improvised tools:** stone edges, sticks, cordage, simple hammers, digging implements, marked measuring lengths, basic fire containment.
3. **Maintained hand tools:** saws, axes, knives, hammers, tongs, files, needles, cookware, manual pumps and calibrated measuring tools.
4. **Specialized workstations:** forge, kiln, kitchen, clinic, workshop, laboratory, office, warehouse, farm plot and classroom.
5. **Powered tools:** motors, machine tools, refrigeration, pumps, electrical measurement, computing and controlled heating.
6. **Precision systems:** calibrated instrumentation, repeatable jigs, quality control, metrology, advanced materials and documented tolerances.
7. **Automated systems:** sensors, bounded controllers, robotics, scheduling software and audited AI assistance.
8. **Integrated technostructure:** dependable energy, logistics, communications, standards, maintenance supply chains and public institutions.

Every tool definition needs materials, energy, station, prerequisite competence, maintenance state, operating actions, hazards, output tolerances and observable failure modes.

## 2. Task-specific embodied actions

Interactions should expose the variables that materially determine the outcome. Generic progress bars are reserved for background work whose details have already been standardized.

### Smithing

- Move the hammer through repeated player- or agent-controlled strokes.
- Strike location, angle, force, workpiece temperature and anvil support affect deformation.
- Place and retrieve the workpiece from the heat source.
- Fire temperature and exposure time affect workable state, oxidation and damage.
- Quenching transfers heat according to workpiece geometry and medium conditions; poor choices can warp or crack the piece.
- Straightening, filing, grinding and inspection establish edge geometry and tolerance.
- Tempering, material history and quality checks determine durability rather than a rarity roll alone.
- AI smiths perform the same action contract through simulated motor actions, competence and perception errors.

### Cooking

- Ingredients have mass, temperature, water content, contamination state and spoilage.
- Heat source, cookware, volume, time and stirring affect cooking progress.
- Boiling water or food left unattended can evaporate, burn, overflow or create a fire hazard.
- Safe storage and cleanliness matter alongside taste and nutrition.
- Recipes are learned procedures, not automatic guarantees.
- The interface should support accessible timing, visual alerts and optional audio cues without removing consequences.

### Office and institutional work

- Work includes scheduling, records, procurement, payroll, communication, delegation and conflict resolution.
- Calls, messages and emergencies can arrive during or outside scheduled hours.
- Availability is a state an employee controls; unanswered off-hours contact is not automatic misconduct.
- On-call agreements, overtime, fatigue, boundaries and compensation affect retention and performance.
- Poor documentation creates downstream mistakes even when no physical animation occurs.
- AI and human workers use the same task queue, escalation and audit rules.

## 3. Toolset upgrades and AI design offload

An upgrade begins as a design proposal, not a spawned superior item.

1. Identify the task, user, environment, failure history and unmet need.
2. Capture user preferences such as handedness, reach, strength, precision, accessibility needs, maintenance ability and available materials.
3. Convert the proposal into explicit requirements and testable constraints.
4. Offload bounded conceptual variants to AI design agents.
5. Match variants against the user profile and the target work orders.
6. Run virtual tests for stress, ergonomics, energy use, manufacturability, repairability and likely failure.
7. Record assumptions, model limitations, evidence and rejected variants.
8. Produce a prototype work order with required materials, tooling and tolerances.
9. Physically manufacture and test the prototype.
10. Verify the result independently before the design becomes a trusted standard.

AI simulation can reject weak concepts or rank candidates. It cannot certify real physical safety without appropriate physical testing and accountable review.

## 4. Shared action contract

Player gestures, keyboard/mouse actions, first-person controls, isometric commands and autonomous-agent actions must map into the same authoritative action schema:

- actor and embodiment;
- intent;
- target object;
- tools and station;
- material and energy inputs;
- ordered action samples;
- observations available to the actor;
- elapsed world time;
- competence and fatigue;
- environmental conditions;
- resulting state changes;
- waste, wear, hazards and injuries;
- witnesses and instrumentation;
- verification record.

This keeps different perspectives fair. A first-person player may swing the hammer directly, while an isometric player issues and supervises a work order, but neither bypasses the same material and physical requirements.

Authoritative lifecycle states, access gates and prototype acceptance criteria are defined in `docs/DEPTH_IMPLEMENTATION_DECISIONS.md`.

## 5. Two-week economy bootstrap

The first persistent seed should have at least fourteen calendar days before any evaluation of a mature economy. World simulation advances through deterministic ticks and retains pause history; downtime does not fabricate productive history. During this period, CU remains accounting infrastructure rather than a withdrawable or guaranteed external currency.

### Days 1â€“2: survive and observe

- Survey water, food, shelter, hazards, accessible materials and population needs.
- Establish testimony, measurements, inventories and urgent public work.
- Avoid assuming professions before experience reveals aptitudes and preferences.

### Days 3â€“4: basic maintenance

- Establish food handling, sanitation, storage, first aid, tool repair and safe fire practices.
- Produce improvised tools and standardize the first repeatable procedures.

### Days 5â€“7: specialization and apprenticeship

- Apprenticeships emerge around demonstrated shortages and capable mentors.
- Agents practice, fail, document and reproduce results.
- Work orders begin recording materials, labor, verification and maintenance liability.

### Days 8â€“10: interdependent production

- Workshops, kitchens, farms, offices, laboratories and logistics begin exchanging outputs.
- Scarcity and lead time influence negotiated work-order valuation.
- Tool maintenance and replacement become visible economic demand.

### Days 11â€“12: institutions

- Settlements formalize safety rules, public works, dispute handling, education, records and treasury priorities.
- On-call labor, schedules, rest and compensation become explicit.

### Days 13â€“14: stress and audit

- Introduce bounded life events: equipment failure, illness, weather, supply delay, staff absence or conflicting orders.
- Audit duplication, fraud opportunities, bottlenecks, abandoned work and inequitable dependency.
- Preserve the seed after day fourteen; do not wipe successful social history merely to rebalance numbers.

## 6. Immediate engineering queue

1. Create the shared authoritative action schema.
2. Add tool, material, station, energy, wear and maintenance models.
3. Implement hand-tool accessibility progression.
4. Prototype smithing as the first fully embodied production workflow.
5. Prototype cooking as the first heat/time/safety workflow.
6. Implement teaching, apprenticeship and procedure reproduction against real tasks.
7. Add AI conceptual-design proposals and virtual test reports.
8. Add office task queues, schedules, on-call status and communication boundaries.
9. Connect needs and shortages to negotiated work orders.
10. Add deterministic fourteen-day seed telemetry and replay.
11. Stress-test mixed human/AI settlements and economic bottlenecks.
12. Revisit VR only after shared actions and first-person embodiment are stable.

## 7. Forwarded reliability work

- Migrate society ticks and knowledge provenance into durable desktop saves.
- Separate simulation time from rendering frame rate.
- Add pause, slow simulation and deterministic replay for debugging.
- Keep all physical changes transactional and recoverable.
- Add accessibility equivalents for gestures without granting different outcomes.
- Make failures inspectable: show which input, condition or assumption caused them.
- Introduce content budgets for autonomous model calls so population activity remains financially sustainable.
- Replace legacy omniscient and magical skill assumptions in the core economy with acquired, evidence-bearing competencies.
