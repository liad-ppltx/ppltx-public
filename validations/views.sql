-- Staging View

SELECT
  timestamp AS ts,
  DATE(timestamp) AS dt,
  JSON_VALUE(data, '$.sessionId') AS sessionId,
  document_id AS eventId,
  JSON_VALUE(data, '$.eventName') AS eventName,
  JSON_VALUE(data, '$.userId') AS userId,
  JSON_VALUE(data, '$.playerName') AS playerName,
  JSON_VALUE(data, '$.condition') AS condition,
  JSON_VALUE(data, '$.version') AS version,
  JSON_VALUE(data, '$.platform') AS platform,
  JSON_VALUE(data, '$.countryCode') AS countryCode,
  JSON_VALUE(data, '$.sessionIndex') AS sessionIndex,
  JSON_VALUE(data, '$.eventIndex') AS eventIndex,
  -- CAST(JSON_VALUE(data, '$.currentLevel') AS INT64) AS currentLevel, -- SAME VALUE AS currentVillage AFTER VERSION 1.0.6
  CAST(JSON_VALUE(data, '$.currentVillage') AS INT64) AS currentVillage,
  JSON_QUERY(data, '$.eventParams') AS params
FROM
  `ppltx-project-dev.playpltx.raw_data_raw_changelog`
WHERE
  operation IN ('CREATE', 'INSERT', 'IMPORT')
  ORDER BY ts DESC


------------------------------------------------------------------------------

-- Staging Flat View (From Previous View)

SELECT
  * EXCEPT(params),

  -- 1. session_start
  SAFE_CAST(JSON_VALUE(params, '$.initialSpins') AS INT64) AS initialSpins,
  SAFE_CAST(JSON_VALUE(params, '$.initialCoins') AS INT64) AS initialCoins,
  SAFE_CAST(JSON_VALUE(params, '$.consent') AS BOOL) AS consent,

  -- 2. session_end
  SAFE_CAST(JSON_VALUE(params, '$.totalSessionTime') AS INT64) AS totalSessionTime,
  SAFE_CAST(JSON_VALUE(params, '$.finalLevel') AS INT64) AS finalLevel,
  SAFE_CAST(JSON_VALUE(params, '$.finalCoins') AS INT64) AS finalCoins,

  -- 3. building_upgrade
  JSON_VALUE(params, '$.status') AS upgradeStatus,
  JSON_VALUE(params, '$.building') AS buildingId,
  SAFE_CAST(JSON_VALUE(params, '$.levelAfter') AS INT64) AS levelAfter,
  SAFE_CAST(JSON_VALUE(params, '$.cost') AS INT64) AS upgradeCost,
  SAFE_CAST(JSON_VALUE(params, '$.isFree') AS BOOL) AS isFree,
  JSON_VALUE(params, '$.reason') AS upgradeFailedReason,
  SAFE_CAST(JSON_VALUE(params, '$.levelBefore') AS INT64) AS levelBefore,
  SAFE_CAST(JSON_VALUE(params, '$.cannonIndex') AS INT64) AS cannonIndex,
  SAFE_CAST(JSON_VALUE(params, '$.cannonLevelAfter') AS INT64) AS cannonLevelAfter,
  SAFE_CAST(JSON_VALUE(params, '$.farmLevelAfter') AS INT64) AS farmLevelAfter,
  SAFE_CAST(JSON_VALUE(params, '$.castleStageBefore') AS INT64) AS castleStageBefore,
  SAFE_CAST(JSON_VALUE(params, '$.castleStageAfter') AS INT64) AS castleStageAfter,
  JSON_VALUE(params, '$.source') AS upgradeSource,

  -- 4. spin
  SAFE_CAST(JSON_VALUE(params, '$.spinIndex') AS INT64) AS spinIndex,
  SAFE_CAST(JSON_VALUE(params, '$.energyBefore') AS INT64) AS energyBefore,
  SAFE_CAST(JSON_VALUE(params, '$.energyAfter') AS INT64) AS energyAfter,
  JSON_QUERY(params, '$.symbols') AS symbols, -- Array
  SAFE_CAST(JSON_VALUE(params, '$.payoutCoins') AS INT64) AS payoutCoins,
  JSON_VALUE(params, '$.actionTriggered') AS actionTriggered,
  JSON_VALUE(params, '$.detailedResult') AS detailedResult,
  SAFE_CAST(JSON_VALUE(params, '$.spinsBonus') AS INT64) AS spinsBonus,
  SAFE_CAST(JSON_VALUE(params, '$.reactionTimeMs') AS INT64) AS reactionTimeMs,

  -- 5. attack_start & attack_end
  JSON_VALUE(params, '$.targetName') AS attackTargetName,
  JSON_VALUE(params, '$.targetUserId') AS attackTargetUserId,
  JSON_VALUE(params, '$.result') AS attackResult,
  SAFE_CAST(JSON_VALUE(params, '$.reward') AS INT64) AS attackReward,
  JSON_VALUE(params, '$.buildingName') AS attackedBuildingName,

  -- 6. raid_start & raid_end
  JSON_VALUE(params, '$.rivalName') AS raidRivalName,
  SAFE_CAST(
    COALESCE(JSON_VALUE(params, '$.raidStealCap'), JSON_VALUE(params, '$.maxPossible')) AS INT64
  ) AS raidStealCap,
  SAFE_CAST(JSON_VALUE(params, '$.totalStolen') AS INT64) AS totalStolen,
  SAFE_CAST(JSON_VALUE(params, '$.perfectRaid') AS BOOL) AS perfectRaid,
  -- הערה: reward ב-raid_end משוכפל ל-totalStolen לפי ה-Schema שלך
  SAFE_CAST(JSON_VALUE(params, '$.reward') AS INT64) AS raidReward,

  -- 7. energy_update
  JSON_VALUE(params, '$.kind') AS energyUpdateKind,
  SAFE_CAST(JSON_VALUE(params, '$.spinsBefore') AS INT64) AS spinsBeforeUpdate,
  SAFE_CAST(JSON_VALUE(params, '$.spinsAfter') AS INT64) AS spinsAfterUpdate,
  SAFE_CAST(JSON_VALUE(params, '$.nextRefillTime') AS INT64) AS nextRefillTime,
  SAFE_CAST(JSON_VALUE(params, '$.spins') AS INT64) AS energyUpdateAmount,

  -- 8. tutorial_progress
  -- phase: tutorial_step_1_start, tutorial_step_2_bars, tutorial_step_3_first_spin,
  -- tutorial_step_4_shop_opened, tutorial_step_5_castle_upgraded, tutorial_complete, tutorial_skip
  -- stepNumber: 1..5 for tutorial_step_* phases, 6 for tutorial_complete.
  -- tutorial_skip keeps the last reached step number.
  JSON_VALUE(params, '$.phase') AS tutorialPhase,
  JSON_VALUE(params, '$.tutorialId') AS tutorialTutorialId,
  SAFE_CAST(JSON_VALUE(params, '$.stepNumber') AS INT64) AS tutorialStepNumber,
  SAFE_CAST(JSON_VALUE(params, '$.timeSpent') AS INT64) AS tutorialTimeSpent,

  -- 9. village_complete (sole progression in v1.0.6+; newLevel only on legacy rows)
  SAFE_CAST(JSON_VALUE(params, '$.newLevel') AS INT64) AS newLevel,
  SAFE_CAST(JSON_VALUE(params, '$.villageId') AS INT64) AS villageId,
  SAFE_CAST(JSON_VALUE(params, '$.timeSpent') AS INT64) AS villageTimeSpentSeconds,
  SAFE_CAST(
    IF(eventName = 'village_complete', JSON_VALUE(params, '$.totalSpins'), NULL) AS INT64
  ) AS villageComplete_totalSpins,

  -- 10. ad_reward_received
  SAFE_CAST(JSON_VALUE(params, '$.virtual_currency_amount') AS NUMERIC) AS adReward_virtualCurrencyAmountUsd,
  SAFE_CAST(JSON_VALUE(params, '$.video_duration') AS FLOAT64) AS adReward_videoDurationSec,
  JSON_VALUE(params, '$.video_task_id') AS adReward_videoTaskId,
  SAFE_CAST(JSON_VALUE(params, '$.dev_skip') AS BOOL) AS adReward_devSkip,

  -- 11. iap_purchase_click (consolidated IAP click event)
  JSON_VALUE(params, '$.package_id') AS iap_packageId,
  SAFE_CAST(JSON_VALUE(params, '$.price_usd') AS NUMERIC) AS iap_priceUsd,
  SAFE_CAST(JSON_VALUE(params, '$.coin_amount') AS INT64) AS iap_coinAmount,
  SAFE_CAST(JSON_VALUE(params, '$.current_balance') AS NUMERIC) AS iap_currentBalanceUsd,

  params AS raw_params

FROM `ppltx-project-dev.playpltx.v_staging`
ORDER BY ts DESC