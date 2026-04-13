SELECT
  eventName,
  COUNT(*) AS total_events,

  -- 1. session_start & session_end
  COUNT(JSON_VALUE(params, '$.initialSpins')) AS p_initialSpins,
  COUNT(JSON_VALUE(params, '$.initialCoins')) AS p_initialCoins,
  COUNT(JSON_VALUE(params, '$.consent')) AS p_consent,
  COUNT(JSON_VALUE(params, '$.totalSessionTime')) AS p_totalSessionTime,
  COUNT(JSON_VALUE(params, '$.finalLevel')) AS p_finalLevel,
  COUNT(JSON_VALUE(params, '$.finalCoins')) AS p_finalCoins,

  -- 2. building_upgrade
  COUNT(JSON_VALUE(params, '$.status')) AS p_upgradeStatus,
  COUNT(JSON_VALUE(params, '$.building')) AS p_buildingId,
  COUNT(JSON_VALUE(params, '$.levelAfter')) AS p_levelAfter,
  COUNT(JSON_VALUE(params, '$.cost')) AS p_upgradeCost,
  COUNT(JSON_VALUE(params, '$.isFree')) AS p_isFree,
  COUNT(JSON_VALUE(params, '$.reason')) AS p_upgradeReason,
  COUNT(JSON_VALUE(params, '$.cannonIndex')) AS p_cannonIndex,
  COUNT(JSON_VALUE(params, '$.castleStageAfter')) AS p_castleStageAfter,

  -- 3. spin
  COUNT(JSON_VALUE(params, '$.spinIndex')) AS p_spinIndex,
  COUNT(JSON_VALUE(params, '$.energyBefore')) AS p_energyBefore,
  COUNT(JSON_VALUE(params, '$.energyAfter')) AS p_energyAfter,
  COUNT(JSON_QUERY(params, '$.symbols')) AS p_symbols_array,
  COUNT(JSON_VALUE(params, '$.payoutCoins')) AS p_payoutCoins,
  COUNT(JSON_VALUE(params, '$.actionTriggered')) AS p_actionTriggered,
  COUNT(JSON_VALUE(params, '$.reactionTimeMs')) AS p_reactionTimeMs,

  -- 4. attack & raid
  COUNT(JSON_VALUE(params, '$.targetName')) AS p_attackTarget,
  COUNT(JSON_VALUE(params, '$.result')) AS p_attackResult,
  COUNT(JSON_VALUE(params, '$.reward')) AS p_reward,
  COUNT(JSON_VALUE(params, '$.rivalName')) AS p_raidRival,
  COUNT(JSON_VALUE(params, '$.totalStolen')) AS p_totalStolen,
  COUNT(JSON_VALUE(params, '$.perfectRaid')) AS p_perfectRaid,

  -- 5. energy_update
  COUNT(JSON_VALUE(params, '$.kind')) AS p_energyKind,
  COUNT(JSON_VALUE(params, '$.spinsAfter')) AS p_spinsAfterUpdate,
  COUNT(JSON_VALUE(params, '$.nextRefillTime')) AS p_nextRefillTime,

  -- 6. tutorial & progress
  COUNT(JSON_VALUE(params, '$.phase')) AS p_tutorialPhase,
  COUNT(JSON_VALUE(params, '$.tutorialId')) AS p_tutorialId,
  COUNT(JSON_VALUE(params, '$.stepId')) AS p_stepId,
  COUNT(JSON_VALUE(params, '$.stepNumber')) AS p_stepNumber,
  COUNT(JSON_VALUE(params, '$.newLevel')) AS p_newLevel,
  COUNT(JSON_VALUE(params, '$.villageId')) AS p_villageId,
  COUNT(JSON_VALUE(params, '$.timeSpent')) AS p_timeSpent,

  -- 7. audit_stress_test
  COUNT(JSON_VALUE(params, '$.hasEconomy')) AS p_audit_economy,
  COUNT(JSON_VALUE(params, '$.hasLogger')) AS p_audit_logger,
  COUNT(JSON_VALUE(params, '$.hasRunSpin')) AS p_audit_runSpin

FROM `ppltx-project-dev.playpltx.v_staging`
WHERE version = '1.0.6'
GROUP BY eventName
ORDER BY total_events DESC