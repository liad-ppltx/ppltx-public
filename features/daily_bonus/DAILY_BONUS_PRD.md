# PRD: Daily Bonus Feature (PlayPltx)

## 1. Problem Statement
Players lack a compelling reason to return to the game once their initial session ends. Currently, there is no recurring incentive to re-engage with the game, resulting in lower Day-N retention rates.

## 2. Goals & Objectives
* **Improve Retention:** Increase D1–D7 retention by establishing a daily habit.
* **Increase DAU:** Encourage a "daily login" loop.
* **Success Metrics (KPIs):**
    * Increase in Average Daily Active Users (DAU).
    * Higher average login frequency per user.

## 3. User Flow
1. **Login:** Upon game load and successful consent, the system checks the `last_daily_bonus_claim` date.
2. **Trigger:** If the bonus has not been claimed today, a "Daily Bonus" modal is injected into the UI.
3. **Claim:** The player clicks the "Claim" button.
4. **Reward:** The reward (Spins/Coins) is added to the user's balance.
5. **Update:** `last_daily_bonus_claim` is updated in `localStorage`.
6. **Dismiss:** The modal closes, and the player continues to the main game loop.

## 4. Functional Requirements
* **Progression Logic:** The reward value should scale based on the `day_streak` (e.g., Day 1: 10 Spins, Day 7: 100 Spins).
* **Reset Logic:** If a user misses a day, the streak resets to Day 1.
* **Action Gating:** The Daily Bonus modal must be a "blocker." No game functions (Slot machine, Shop) should be interactive until the bonus is claimed or dismissed.
* **AB Testing:** Support different reward types or button color schemes for Condition A vs. Condition B.

## 5. Analytics & Event Parity
All events must be captured for both the Game and the Simulator:
* `daily_bonus_opened`: Triggered when the modal appears.
* `daily_bonus_claimed`: 
    * Properties: `day_streak` (INT), `reward_amount` (INT), `reward_type` (STRING), `condition` (STRING).
* `daily_bonus_skipped`: Triggered if the user dismisses without claiming.

## 6. UI/UX Specifications
* **Modal Design:** Consistent with existing Shop/Tutorial UI (Dark overlay, branded gold buttons).
* **Animations:** A "Treasure Chest" or "Gift" opening animation upon clicking "Claim".
* **Responsive:** Must be restricted to the desktop "Safe Zone" and centered.
* **Accessibility:** The button should have clear hover states (consistent with the AB testing logic).

## 7. Technical Logic (Pseudo-Code)
```javascript
function checkDailyBonus() {
    const lastClaim = localStorage.getItem('last_daily_bonus_date');
    const today = new Date().toDateString();
    
    if (lastClaim !== today) {
        showDailyBonusModal();
    }
}

function claimBonus(streak) {
    const reward = calculateReward(streak);
    updateBalance(reward);
    localStorage.setItem('last_daily_bonus_date', new Date().toDateString());
    logAnalytics('daily_bonus_claimed', { streak, reward });
}
```

## 8. Simulator Parity (`subpltx/jobs/playpltx_sim`)
* The simulator must perform an automated "daily check" per virtual day.
* It must simulate claim probabilities (e.g., 90% claim rate) to measure the long-term impact of the bonus on the player's balance and village progress.
* Events emitted by the simulator must match the game's event schema exactly.
