Here is a comprehensive **README.md** file in English, structured professionally for your GitHub repository or project documentation.

---

# PlayPLTX Analytics & Research Framework (v1.0.4)

## 📝 Project Overview

**PlayPLTX** is a web-based game environment designed specifically for behavioral research and A/B testing. The system is engineered to collect high-fidelity interaction data, economic balance metrics, and player decision-making patterns under different experimental conditions. Data is captured in real-time via **Firebase Firestore** and streamed to **Google BigQuery** for advanced statistical analysis.

---

## 🏗️ Data Architecture

The logging system follows an **"Event Envelope"** pattern. Every user action is recorded as an "Event," which is automatically enriched with "Super Properties" that define the user's global context.

### 1. Super Properties (Global Context)

These fields are present at the top level of every database document. they allow for immediate segmentation in BigQuery without complex table joins.

| Property | Type | Source / Description |
| --- | --- | --- |
| **`userId`** | String | Persistent unique identifier for the participant. |
| **`sessionId`** | String | Unique ID for the current session (resets on page refresh). |
| **`condition`** | String | Experimental group (e.g., **A** or **B**). |
| **`version`** | String | App version, controlled dynamically via `game-events.json`. |
| **`platform`** | Enum | Device classification: `Mobile`, `Tablet`, or `Desktop`. |
| **`countryCode`** | String | User's country code based on IP-to-Geo lookup. |
| **`currentLevel`** | Integer | The player's level at the moment of the event. |
| **`currentVillage`** | Integer | The active village ID the player is currently in. |
| **`timestamp`** | ISO-8601 | Server-side write time. |
| **`clientTimestampMs`** | Integer | Client-side Unix timestamp (used for precise latency/duration math). |

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
* *End Params:* `totalStolen`, `perfectRaid` (boolean).



### Progression & Meta

* **`player_level_up`**: Fired when a village is completed (25 stars); `newLevel` is the next village number (aligned with `village_complete`).
* **`village_complete`**: Fired when all 25 stars in a village are collected. Includes `timeSpent` and `totalSpins`.
* **`energy_update`**: Tracks changes in spin inventory (refills or depletions).

---

## 🔬 Research Methodology & Optimization

### Session Duration Calculation

To maintain a "lean" pipeline and reduce Firestore write costs, periodic **Heartbeats have been removed**.

* **Methodology:** Session duration is calculated in **BigQuery** by subtracting the `timestamp` of the first event (`session_start`) from the `timestamp` of the last recorded event for a specific `sessionId`.
* **Benefit:** This ensures we only measure "Active Time," excluding periods where a user might have left the tab open without interacting.

### Building ID Canonicalization

To ensure data consistency across all experimental groups, building names in the `building_upgrade` event are strictly mapped to: **Castle, Cannon, Statue, Farm, and Boat**. Legacy IDs (like "Wall") have been deprecated to maintain a clean data schema.

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
