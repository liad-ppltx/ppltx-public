Here is a comprehensive **README.md** file in English, structured professionally for your GitHub repository or project documentation.

---

# PlayPLTX Analytics & Research Framework (v1.0.6)

## 📝 Project Overview

**PlayPLTX** is a web-based game environment designed specifically for behavioral research and A/B testing. The system is engineered to collect high-fidelity interaction data, economic balance metrics, and player decision-making patterns under different assigned study conditions. Data is captured in real-time via **Firebase Firestore** and streamed to **Google BigQuery** for advanced statistical analysis.

---

## 🏗️ Data Architecture

The logging system follows an **"Event Envelope"** pattern. Every user action is recorded as an "Event," which is automatically enriched with "Super Properties" that define the user's global context.

### 1. Super Properties (Global Context)

These fields are present at the top level of every database document. they allow for immediate segmentation in BigQuery without complex table joins.

| Property | Type | Source / Description |
| --- | --- | --- |
| **`userId`** | String | Persistent unique identifier for the participant. |
| **`sessionId`** | String | Unique ID for the current session (resets on page refresh). |
| **`condition`** | String | Assigned A/B group (e.g., **A** or **B**). |
| **`version`** | String | App version, controlled dynamically via `game-events.json`. |
| **`platform`** | Enum | Device classification: `Mobile`, `Tablet`, or `Desktop`. |
| **`countryCode`** | String | User's country code based on IP-to-Geo lookup. |
| **`currentLevel`** | Integer | Same value as **`currentVillage`** — both come from `gameState.villageId`. |
| **`currentVillage`** | Integer | The active village index the player is currently in. |
| **`timestamp`** | ISO-8601 | Server-side write time. |
| **`clientTimestampMs`** | Integer | Client-side Unix timestamp (used for precise latency/duration math). |

---

## 🪙 Economy scaling (v1.0.6+)

Per-condition config in `game-economy.json` includes **`villageScalingFactor`** (default **1.5**). For the current village index \(v =\) `gameState.villageId` (1-based):

**Scale multiplier**

\[
\text{scale}(v) = \text{villageScalingFactor}^{\,v - 1}
\]

**Coin payouts** (slot coin/bag results, attack/raid coin rewards from payout tables, village completion coin bonus, and raid dig loot tiers) are multiplied by \(\text{scale}(v)\) after reading base values from config.

**Building upgrade costs** use the same multiplier on each building’s **base** coin cost: effective cost is \(\text{baseCost} \times \text{scale}(v) \times \text{multiplier}^{\text{stars}}\) (stars are per-building star count, unchanged).

Spin count rewards (e.g. triple-spins) are **not** scaled by this factor.

---

## 🧪 Local dev: money cheat

With **`?dev=true`** in the page URL, press **`M`** to add **10,000,000** coins, refresh the HUD, and persist state. The shortcut is ignored while focus is in an `INPUT`, `TEXTAREA`, or content-editable field.

---

## 📅 Event Catalog

Each event contains an `eventParams` object which holds data specific to that particular action.

### Session Management

* **`session_start`**: Fired upon game load and user consent.
* *Params:* `initialSpins`, `initialCoins`, `consent`.


* **`session_end`**: **(Best Effort)** Fired when the tab is closed or the user navigates away.
* *Params:* `totalSessionTime` (seconds), `finalLevel`, `finalCoins`.



### Core Gameplay Loop

* **`spin`**: Records every slot machine interaction.
* *Params:* `spinIndex`, `energyAfter`, `symbols` (array of results), `payoutCoins`, `actionTriggered` (raid/attack/shield), `reactionTimeMs`.


* **`building_upgrade`**: Records a star being added to a village building.
* *Params:* `building` (Castle/Cannon/Statue/Farm/Boat), `status` (success/max), `cost`, `levelAfter`.



### Social Interaction (PvP)

* **`attack_start` / `attack_end**`: Tracks the process of attacking a rival island.
* *End Params:* `result` (hit/blocked), `reward`, `buildingName`.


* **`raid_start` / `raid_end**`: Tracks the coin-stealing (digging) mini-game.
* *End Params:* `totalStolen`, `perfectRaid` (boolean); raid start also logs `raidStealCap` (scaled steal ceiling for the current village).



### Progression & Meta

* **`village_complete`**: **Sole progression milestone** when all 25 stars in the current village are collected. The client then advances `gameState.villageId` (and Firestore `currentLevel` / `currentVillage` track that same number). Params include **`villageId`** (completed village), **`totalSpins`**, and **`timeSpent`** (seconds in that village) for research analysis.
* **`energy_update`**: Tracks changes in spin inventory (refills or depletions).

Legacy **`player_level_up`** was removed in v1.0.6; downstream jobs should use **`village_complete`** only.

---

## 🔬 Research Methodology & Optimization

### Session Duration Calculation

To maintain a "lean" pipeline and reduce Firestore write costs, periodic **Heartbeats have been removed**.

* **Methodology:** Session duration is calculated in **BigQuery** by subtracting the `timestamp` of the first event (`session_start`) from the `timestamp` of the last recorded event for a specific `sessionId`.
* **Benefit:** This ensures we only measure "Active Time," excluding periods where a user might have left the tab open without interacting.

### Building ID Canonicalization

To ensure data consistency across all study arms, building names in the `building_upgrade` event are strictly mapped to: **Castle, Cannon, Statue, Farm, and Boat**. Legacy IDs (like "Wall") have been deprecated to maintain a clean data schema.

### Version Control

The application version is managed centrally in `game-events.json`. Updating the `currentAppVersion` field in this JSON automatically updates the `version` super property across all subsequent logs, allowing for seamless longitudinal analysis across different game builds.

---

## 🚀 How to Use This Data

Data is synced from Firestore to BigQuery every 24 hours (or in real-time depending on your sync settings). Use the following SQL pattern to begin analysis:

```sql
SELECT 
  userId, 
  condition, 
  COUNTIF(eventName = 'spin') as total_spins,
  MAX(currentLevel) as max_level_reached
FROM `your_project.events`
GROUP BY userId, condition

```

---
