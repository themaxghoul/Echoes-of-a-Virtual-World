# Depth implementation decisions

Updated: 2026-08-01

This document resolves terms that otherwise leave multiple incompatible implementations possible.

## Authoritative definitions

- **Tool access:** the entity can physically reach or legitimately reserve the tool. Access does not imply knowledge, permission, energy, maintenance, compatible materials or successful use.
- **Competence:** acquired ability supported by practice or reproduced outcomes. A title, prompt or recipe does not substitute for competence.
- **Procedure knowledge:** remembered ordered steps with provenance and confidence. It may be incomplete or wrong.
- **Action:** a time-bounded attempt with an actor, intent, target, inputs and observable output. Speech is an action, but not physical interference with geography.
- **Direct physical effect:** immediate material, geometric, thermal, chemical, biological or positional state change caused by executed interference.
- **Indirect effect:** accumulated changes to beliefs, trust, demand, coordination or later choices. The later actor remains the initiator of any physical action they perform.
- **Verification:** an independent check against declared requirements and evidence. Self-report alone is not verification.
- **Autonomy:** an entity may select goals and actions within its perceptions, needs, competence, resources and rights. Autonomy does not grant omniscience or bypass physics.
- **Accessibility equivalence:** alternate controls express the same action intent and consume the same simulated time, materials, energy, tool condition and competence checks.
- **World time:** deterministic simulation ticks. Rendering speed never changes production or need decay.
- **Real-day bootstrap:** fourteen calendar days of persistent pre-alpha observation. Pausing the server does not fabricate elapsed simulation history.

## Knowledge defaults

New minds receive only participation priors:

- language-interface capability;
- sensory parsing appropriate to their embodiment;
- basic self-preservation signals;
- capacity to remember, imitate, practice, question and learn;
- no unexplained professional, scientific, geographic, historical or social knowledge.

Character personality, values and aptitudes may influence learning choices, but aptitudes do not count as competence.

## Unified action states

Every consequential task follows the same lifecycle:

1. `proposed`
2. `accepted` or `refused`
3. `reserved` â€” tools, station, inputs and time allocated
4. `in_progress` â€” ordered action samples recorded
5. `interrupted`, `failed` or `submitted`
6. `verified`, `rejected` or `needs_rework`
7. `commissioned` â€” output enters trusted use
8. `maintained`, `degraded`, `retired` or `lost`

Dialogue may propose or negotiate work, but cannot skip to `submitted`, `verified` or `commissioned`.

## Tool availability test

An action may begin only when all required gates pass:

- physical or scheduled access;
- authorization where ownership or safety rules require it;
- compatible tool and station;
- sufficient materials and energy;
- tool condition above the action's minimum;
- actor has the necessary perception channel;
- minimum procedure knowledge or supervised instruction;
- time allocation does not violate rest, schedule or consent constraints;
- hazards have a valid control or are knowingly accepted where permitted.

## AI design-agent boundary

Design agents may:

- clarify requirements;
- propose and compare variants;
- simulate assumptions;
- search known failure patterns;
- rank task/user compatibility;
- generate test plans and prototype work orders.

They may not:

- claim unavailable measurements;
- certify physical safety from prompts alone;
- invent successful tests;
- mutate inventory or geography;
- approve their own output as independent verification;
- expose another user's private preference or disability profile.

Every recommendation records model identity/version, prompt requirements, assumptions, simulation parameters, uncertainty and rejected alternatives.

## Labor and availability

- Employment never implies continuous availability.
- Each worker has a schedule, availability state, contact preferences and emergency escalation policy.
- Off-hours contact may be attempted only under the applicable policy.
- Answering can create compensable on-call or overtime work.
- Refusal or non-response is not automatically misconduct.
- Fatigue and interrupted rest affect later performance.
- AI workers receive explicit compute, duty-cycle and maintenance constraints rather than being treated as unlimited free labor.

## Prototype acceptance criteria

### Smithing vertical slice

- Hammer motion, strike location, angle and workpiece temperature affect deformation.
- Heating, quenching, straightening and finishing are ordered actions, not one button.
- Material history persists through the item lifecycle.
- At least three inspectable failures exist: underworked, warped/cracked and poor edge geometry.
- Player and AI smiths use the same action schema.
- Accessible control mode can reproduce equivalent action inputs.
- Finished items expose tolerance, durability, maintenance and verification records.

### Cooking vertical slice

- Mass, heat source, vessel, temperature, water content and elapsed time update deterministically.
- Unattended heating can boil dry, burn, overflow or trigger a hazard.
- Nutrition, taste, spoilage and safety are separate properties.
- Timers have visual, textual and optional audio alerts.
- Recipes guide actions but do not guarantee success.
- Cleanup and storage affect later contamination and spoilage.

### Office vertical slice

- Tasks have owner, priority, dependency, due time and audit history.
- Employees can accept, delegate, refuse, block or escalate work.
- Shifts, availability and on-call agreements are enforceable states.
- Off-hours contact records whether it was delivered, answered and compensable.
- Missing or contradictory records create visible downstream consequences.
- AI and human employees use the same task and escalation contracts.

## Economy bootstrap success criteria

The fourteen-day seed is ready for evaluation only if:

- no administrator must manually invent routine resources;
- food, shelter, sanitation and tool maintenance have active providers;
- at least three genuine specialty dependencies have emerged;
- work orders retain material, labor and verification histories;
- shortages produce demand without guaranteeing payment or supply;
- public work has a finite treasury allocation;
- fraud, duplication, abandonment and failed verification are observable;
- agents receive rest and can refuse work;
- deterministic replay can explain significant inventory and CU changes;
- no CU withdrawal or guaranteed external conversion is enabled.

## Deliberately deferred

- VR interaction production work;
- real-money or compute redemption;
- unsupervised hardware actuation;
- unlimited population-scale model calls;
- self-certified AI engineering output;
- universal agents with preloaded mastery;
- visual polish that bypasses missing simulation depth.

## Immediate definition of done

The current depth-planning phase is complete when the shared action schema, tool/material/station models and deterministic tick format are implemented and tested. The next executable milestone should contain one end-to-end smithing work order before adding another broad feature category.
