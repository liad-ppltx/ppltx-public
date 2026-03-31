SELECT
  eventName,
  COUNT(*) AS total_occurrences,

  -- ספירת פרמטרים של Session
  COUNT(JSON_VALUE(params, '$.initialSpins')) AS has_initialSpins,
  COUNT(JSON_VALUE(params, '$.initialCoins')) AS has_initialCoins,
  COUNT(JSON_VALUE(params, '$.consent')) AS has_consent,
  COUNT(JSON_VALUE(params, '$.totalSessionTime')) AS has_totalSessionTime,

  -- ספירת פרמטרים של Spin
  COUNT(JSON_VALUE(params, '$.spinIndex')) AS has_spinIndex,
  COUNT(JSON_VALUE(params, '$.payoutCoins')) AS has_payoutCoins,
  COUNT(JSON_VALUE(params, '$.actionTriggered')) AS has_actionTriggered,
  COUNT(JSON_VALUE(params, '$.reactionTimeMs')) AS has_reactionTimeMs,

  -- ספירת פרמטרים של Upgrades
  COUNT(JSON_VALUE(params, '$.building')) AS has_building,
  COUNT(JSON_VALUE(params, '$.status')) AS has_upgradeStatus,
  COUNT(JSON_VALUE(params, '$.cost')) AS has_upgradeCost,

  -- ספירת פרמטרים של Attack/Raid
  COUNT(JSON_VALUE(params, '$.targetName')) AS has_attackTarget,
  COUNT(JSON_VALUE(params, '$.result')) AS has_attackResult,
  COUNT(JSON_VALUE(params, '$.totalStolen')) AS has_totalStolen,
  COUNT(JSON_VALUE(params, '$.perfectRaid')) AS has_perfectRaid,

  -- ספירת פרמטרים של התקדמות
  COUNT(JSON_VALUE(params, '$.newLevel')) AS has_newLevel,
  COUNT(JSON_VALUE(params, '$.villageId')) AS has_villageId,
  COUNT(JSON_VALUE(params, '$.phase')) AS has_tutorialPhase,

  -- ספירת פרמטרים של Audit
  COUNT(JSON_VALUE(params, '$.hasEconomy')) AS has_audit_economy,
  COUNT(JSON_VALUE(params, '$.hasLogger')) AS has_audit_logger

FROM `ppltx-project-dev.playpltx.v_staging`
GROUP BY eventName
ORDER BY total_occurrences DESC