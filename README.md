# ppltx-public
Public repository for ppltx community

# PlayPLTX Analytics Framework (v1.0.3)

## Overview
This project implements a robust, research-oriented analytics pipeline using Firebase Firestore and BigQuery. The goal is to track player behavior across different experimental conditions (A/B testing) with high precision.

## Data Architecture
The logging system uses a **"Super Property Envelope"** pattern. Every event is enriched with global user context before being persisted.

### Super Properties (Global Context)
- **User Identity:** `userId`, `sessionId`
- **Experimental Context:** `condition` (A/B Group)
- **Environment:** `platform` (Desktop/Mobile), `countryCode`, `version`
- **Game State:** `currentLevel`, `currentVillage`

## Core Events
| Event | Trigger | Key Payload |
| :--- | :--- | :--- |
| `session_start` | App Load + Consent | `initialSpins`, `condition` |
| `spin` | Slot machine stop | `symbols`, `payoutCoins`, `action` |
| `building_upgrade` | Star added to building | `building`, `status`, `cost` |
| `attack_end` | Hammer mini-game finish | `result` (hit/blocked), `reward` |
| `raid_end` | Pig mini-game finish | `totalStolen`, `perfectRaid` |
| `session_heartbeat` | Every 60s of activity | `sessionDurationSec` |

## Research Considerations
- **Session Tracking:** We use a combination of heartbeats and visibility listeners to accurately measure Time on Site, even if a user closes the tab unexpectedly.
- **Event Renaming:** Legacy events like `slot_action` and `building_action` have been renamed to `spin` and `building_upgrade` for semantic clarity in SQL queries.
- **Data Integrity:** The `audit_stress_test` event is used by the internal QA harness to verify that all required super-properties are present.

## Configuration
Version control is managed via `game-events.json`. To update the app version across all logs, change the `currentAppVersion` field in the JSON file.