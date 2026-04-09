# PlayPLTX Game & Analytics Framework (v1.1.0)

PlayPLTX is a browser game used for behavioral research and product analytics. This repository contains:

- the playable client (`index.html`)
- event contract and telemetry schema (`game-events.json`)
- economy tuning (`game-economy.json`)
- simulation tooling (`simulation/`)

This README explains gameplay configuration, analytics structure, and operational conventions.

## Repository Structure

- `index.html`  
  Main game client (UI, gameplay logic, persistence, analytics logging).
- `game-events.json`  
  Canonical analytics schema (event names, event params, super properties, current version).
- `game-economy.json`  
  Condition-based economy configuration (`condition_A` / `condition_B`).
- `simulation/generator.py`  
  Local synthetic data generator for JSONL output + optional BigQuery load.
- `simulation/data/`  
  Generated event files and persistent simulation user state.

## Versioning

- Active analytics/game config version: `1.1.0`.
- Version is defined in `game-events.json` and propagated to logged events as the top-level `version`.
- Any contract or behavior change should update:
  - `game-events.json`
  - relevant client logic in `index.html`
  - this README

## Analytics Contract

PlayPLTX uses an event-envelope model:

- top-level context (super properties)
- event identity (`eventName`)
- event-specific payload (`eventParams`)

### Key Super Properties

- identity/session: `userId`, `playerName`, `sessionId`
- ordering: `sessionIndex`, `eventIndex`
- context: `condition`, `platform`, `countryCode`, `version`
- progression/time: `currentVillage` (`currentLevel` alias), `timestamp`, `clientTimestampMs`

### Session Ordering Rules

- `sessionIndex` increments once per new `session_start` and persists in local storage.
- `eventIndex` resets at session start and increments for each event in the session.
- First event in a session (`session_start`) has `eventIndex = 1`.

## Event Families

- Session lifecycle: `session_start`, `session_end`
- Gameplay core: `spin`, `building_upgrade`, `energy_update`
- Progression/meta: `tutorial_progress`, `village_complete`
- PvP side flows: `attack_start`/`attack_end`, `raid_start`/`raid_end`

`village_complete` is the canonical progression milestone.

## Economy Configuration

Each condition block in `game-economy.json` defines:

- resources: `initialSpins`, `maxSpins`, `refillMinutes`
- rewards: `villageCompleteReward` (`coins`, `spins`)
- slot behavior: `slotWeights`
- payouts: `coin_single`, `bag_triple`, `raid_base`, `attack_hit`, `attack_blocked`, `spins_triple`
- building growth model: `baseCost`, `multiplier` per building

### Scaling

`villageScalingFactor` scales economy pressure/reward with village progression:

- coin-like rewards scale with village
- upgrade costs scale with village and per-building star depth
- spin count rewards remain unscaled

## UI & Mobile Notes (v1.1.0)

Mobile behavior (`max-width: 768px`) focuses on compact playability:

- sticky top HUD
- reduced artificial vertical gaps between world and slot area
- natural vertical scroll only where needed
- slot machine remains visible and SPIN button remains reachable above browser bars
- decorative village asset labels are hidden on mobile to reduce clutter

Desktop layout remains unchanged by these mobile-specific adjustments.

## Persistence Behavior

- Nickname persisted in `localStorage` (`playerName`)
- Session sequencing persisted in `localStorage` (`playpltxSessionIndex`)
- Gameplay state persisted by the client save mechanism and restored on load

## Local Development

- `?dev=true` enables development shortcuts (including coin cheat keybinds).
- To test analytics shape quickly, inspect payloads from `logEvent()` / Firestore write calls.

## Simulation Overview

`simulation/generator.py` can produce production-like telemetry:

- schema/economy resolution from repo or `PPLTX_PUBLIC_DIR`
- persistent synthetic users in `simulation/data/users_state.json`
- daily JSONL outputs: `simulation/data/events_YYYY-MM-DD.jsonl`
- optional BigQuery upload via `upload-bq` subcommand

## Query Starter

```sql
SELECT
  userId,
  condition,
  COUNTIF(eventName = 'spin') AS total_spins,
  MAX(currentVillage) AS max_village_reached
FROM `your_project.events`
GROUP BY userId, condition;
```

## Change Checklist

When updating gameplay, telemetry, or UX:

- update schema in `game-events.json` if needed
- align logger fields in `index.html`
- bump `currentAppVersion` when contract/behavior changes
- update this README
- regenerate simulation data if downstream consumers depend on new fields
