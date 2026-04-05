#!/usr/bin/env python3
"""
Stateful synthetic event generator for PlayPLTX.
Loads schemas from game-events.json + game-economy.json in this repository root.
Persists user progress in users_state.json under the output directory.

BigQuery: load local events_*.jsonl with the upload-bq subcommand, e.g.:
  python generator.py upload-bq --config bq_config.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shlex
import string
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# -----------------------------------------------------------------------------
# Paths: simulation/ is inside the ppltx-public repo (sibling to game-events.json).
# -----------------------------------------------------------------------------
SIM_DIR = Path(__file__).resolve().parent
REPO_ROOT = SIM_DIR.parent  # ppltx-public repository root
EVENTS_JSON = REPO_ROOT / "game-events.json"
ECONOMY_JSON = REPO_ROOT / "game-economy.json"

# Output (outside repo): <parent-of-repo>/temp/data/ppltx-public/simulation/
# Contains users_state.json and events_YYYY-MM-DD.jsonl files.
OUTPUT_DIR = (SIM_DIR / "../../temp/data/ppltx-public/simulation").resolve()
STATE_FILENAME = "users_state.json"
DEFAULT_BQ_CONFIG_PATH = SIM_DIR / "bq_config.json"

VILLAGE_ITEMS = ("Castle", "Cannon", "Statue", "Farm", "Boat")
SYMBOL_NAMES = ("Hammer", "Pig", "Shield", "Coin", "Bag", "Spins")
BOT_NAMES = ("RivalA", "RivalB", "RivalC", "IslandBot", "CoinMaster")


def village_scale(factor: float, village_id: int) -> float:
    v = max(1, village_id)
    return float(factor) ** (v - 1)


def scaled_coin(base: float, factor: float, village_id: int) -> int:
    return max(0, int(round(base * village_scale(factor, village_id))))


def upgrade_cost(
    building: str,
    stars_before: int,
    buildings_cfg: Dict[str, Any],
    factor: float,
    village_id: int,
) -> int:
    model = buildings_cfg.get(building) or {}
    base = float(model.get("baseCost", 100))
    mult = float(model.get("multiplier", 1.4))
    s = max(0, stars_before)
    scale = village_scale(factor, village_id)
    return max(1, int(round(base * scale * (mult**s))))


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def weighted_choice(rng: random.Random, weights: Dict[str, float]) -> str:
    keys = list(weights.keys())
    w = [max(0.0, float(weights[k])) for k in keys]
    total = sum(w) or 1.0
    r = rng.random() * total
    acc = 0.0
    for k, wi in zip(keys, w):
        acc += wi
        if r <= acc:
            return k
    return keys[-1]


def symbol_from_weight_key(key: str) -> str:
    m = {
        "hammer": "Hammer",
        "pig": "Pig",
        "shield": "Shield",
        "coin": "Coin",
        "bag": "Bag",
        "spins": "Spins",
    }
    return m.get(key.lower(), key.capitalize())


@dataclass
class UserState:
    userId: str
    playerName: str
    coins: int
    currentVillage: int
    stars: int  # total stars in current village (0..25)
    lastPlayedTimestamp: str
    condition: str = "A"
    energy: int = 10
    spin_index: int = 0
    building_stars: Dict[str, int] = field(
        default_factory=lambda: {b: 0 for b in VILLAGE_ITEMS}
    )
    total_spins_village: int = 0
    village_started_at: Optional[str] = None

    @classmethod
    def new_user(cls, seq: int, rng: random.Random) -> "UserState":
        uid = f"sim_{uuid.uuid4().hex[:12]}"
        name = f"Player_{seq}_{rng.choice(string.ascii_uppercase)}{rng.randint(10, 99)}"
        return cls(
            userId=uid,
            playerName=name,
            coins=rng.randint(2000, 25000),
            currentVillage=1,
            stars=0,
            lastPlayedTimestamp=datetime.now(timezone.utc).isoformat(),
            condition=rng.choice(["A", "B"]),
            energy=10,
            spin_index=0,
            building_stars={b: 0 for b in VILLAGE_ITEMS},
            total_spins_village=0,
            village_started_at=None,
        )

    def sync_stars(self) -> None:
        self.stars = sum(self.building_stars.get(b, 0) for b in VILLAGE_ITEMS)


class EventCatalog:
    def __init__(self, events_blob: Dict[str, Any]) -> None:
        self.version = str(events_blob.get("currentAppVersion", "0.0.0"))
        self.events: Dict[str, Dict[str, Any]] = events_blob.get("events") or {}

    def props(self, name: str) -> Dict[str, Any]:
        ev = self.events.get(name) or {}
        return ev.get("properties") or {}


class EconomyConfig:
    def __init__(self, eco: Dict[str, Any]) -> None:
        self.raw = eco

    def condition_key(self, letter: str) -> str:
        return "condition_B" if letter == "B" else "condition_A"

    def block(self, letter: str) -> Dict[str, Any]:
        return self.raw.get(self.condition_key(letter)) or self.raw.get("condition_A") or {}

    def factor(self, letter: str) -> float:
        b = self.block(letter)
        f = float(b.get("villageScalingFactor", 1.5))
        return f if f > 0 else 1.5

    def slot_weights(self, letter: str) -> Dict[str, float]:
        return dict(self.block(letter).get("slotWeights") or {})

    def payouts(self, letter: str) -> Dict[str, float]:
        return dict(self.block(letter).get("payouts") or {})

    def buildings(self, letter: str) -> Dict[str, Any]:
        return dict(self.block(letter).get("buildings") or {})

    def initial_spins(self, letter: str) -> int:
        return int(self.block(letter).get("initialSpins", 10))

    def max_spins(self, letter: str) -> int:
        return int(self.block(letter).get("maxSpins", 10))

    def village_complete_reward(self, letter: str) -> Tuple[int, int]:
        r = self.block(letter).get("villageCompleteReward") or {}
        return int(r.get("coins", 500000)), int(r.get("spins", 20))


def dynamic_fill_params(
    event_name: str,
    catalog: EventCatalog,
    rng: random.Random,
    ctx: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build eventParams from game-events.json property keys & types (with overrides in ctx).
    """
    ctx = ctx or {}
    if event_name in ctx:
        return dict(ctx[event_name])
    props = catalog.props(event_name)
    out: Dict[str, Any] = {}
    for key, spec in props.items():
        if not isinstance(spec, dict):
            continue
        required = spec.get("required", False)
        if not required and rng.random() > 0.35:
            continue
        typ = spec.get("type")
        enum = spec.get("enum")
        if enum is not None:
            choices = [x for x in enum if x is not None]
            if choices:
                out[key] = rng.choice(choices)
            else:
                out[key] = None
            continue
        if typ == "number":
            out[key] = rng.randint(0, 500000)
        elif typ == "boolean":
            out[key] = rng.choice([True, False])
        elif typ == "string":
            out[key] = f"syn_{key}_{rng.randint(1, 9999)}"
        elif typ == "array":
            out[key] = [rng.choice(SYMBOL_NAMES) for _ in range(3)]
        elif isinstance(typ, list):
            if rng.random() < 0.15:
                out[key] = None
            else:
                out[key] = f"syn_{key}"
        else:
            out[key] = None
    return out


def make_envelope_row(
    *,
    catalog: EventCatalog,
    user: UserState,
    session_id: str,
    event_name: str,
    event_params: Dict[str, Any],
    ts: datetime,
    platform: str,
    country: str,
) -> Dict[str, Any]:
    ms = int(ts.timestamp() * 1000)
    return {
        "userId": user.userId,
        "playerName": user.playerName,
        "sessionId": session_id,
        "condition": user.condition,
        "timestamp": ts.isoformat().replace("+00:00", "Z"),
        "eventName": event_name,
        "eventParams": json.dumps(event_params, separators=(",", ":")),
        "currentLevel": user.currentVillage,
        "currentVillage": user.currentVillage,
        "clientTimestampMs": ms,
        "platform": platform,
        "countryCode": country,
        "version": catalog.version,
    }


def compute_spin_outcome(
    rng: random.Random,
    eco: EconomyConfig,
    user: UserState,
) -> Tuple[List[str], int, Optional[str], int, str]:
    w = eco.slot_weights(user.condition)
    keys = list(w.keys()) or ["coin", "coin", "coin"]
    triple = [weighted_choice(rng, w) for _ in range(3)]
    symbols = [symbol_from_weight_key(k) for k in triple]
    factor = eco.factor(user.condition)
    vid = user.currentVillage
    payouts = eco.payouts(user.condition)

    coin_base = float(payouts.get("coin_single", 1000))
    bag_trip = float(payouts.get("bag_triple", 50000))
    spins_trip = int(payouts.get("spins_triple", 10))

    payout_coins = 0
    action: Optional[str] = None
    spins_bonus = 0
    detailed = "No payout this spin."

    if symbols[0] == symbols[1] == symbols[2]:
        if symbols[0] == "Spins":
            spins_bonus = spins_trip
            detailed = f"Triple Spins! +{spins_bonus} spins."
        elif symbols[0] == "Coin":
            payout_coins = scaled_coin(coin_base, factor, vid)
            detailed = f"Triple Coin! +{payout_coins} coins."
        elif symbols[0] == "Bag":
            payout_coins = scaled_coin(bag_trip, factor, vid)
            detailed = f"Triple Bag! +{payout_coins} coins."
        elif symbols[0] == "Hammer":
            action = "attack"
            detailed = "Three hammers! Attack triggered."
        elif symbols[0] == "Pig":
            action = "raid"
            detailed = "Three pigs! Raid triggered."
        elif symbols[0] == "Shield":
            action = "shield"
            detailed = "Three shields! Defense fortified."
    else:
        n_coin_like = sum(1 for s in symbols if s in ("Coin", "Bag"))
        if n_coin_like > 0:
            payout_coins = max(
                1,
                int(round(scaled_coin(coin_base, factor, vid) * n_coin_like / 3)),
            )
            detailed = f"Partial match: +{payout_coins} coins."

    return symbols, payout_coins, action, spins_bonus, detailed


def simulate_session(
    user: UserState,
    catalog: EventCatalog,
    eco: EconomyConfig,
    rng: random.Random,
    session_start: datetime,
    session_end: datetime,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    session_id = f"ses_{uuid.uuid4().hex[:16]}"
    platform = rng.choice(["Mobile", "Tablet", "Desktop"])
    country = rng.choice(["US", "IL", "DE", "GB", "unknown"])

    max_e = eco.max_spins(user.condition)
    user.energy = min(user.energy, max_e)
    init_spins = user.energy
    init_coins = user.coins

    # session_start
    t = session_start
    rows.append(
        make_envelope_row(
            catalog=catalog,
            user=user,
            session_id=session_id,
            event_name="session_start",
            event_params={
                "initialSpins": init_spins,
                "initialCoins": init_coins,
                "consent": True,
            },
            ts=t,
            platform=platform,
            country=country,
        )
    )

    if user.village_started_at is None:
        user.village_started_at = t.isoformat().replace("+00:00", "Z")

    factor = eco.factor(user.condition)
    payouts = eco.payouts(user.condition)
    buildings_cfg = eco.buildings(user.condition)

    # Timeline cursor
    cur = t + timedelta(seconds=rng.randint(2, 8))
    spin_budget = rng.randint(6, 22)

    for _ in range(spin_budget):
        if cur >= session_end - timedelta(seconds=5):
            break
        if user.energy <= 0:
            refill = eco.max_spins(user.condition)
            rows.append(
                make_envelope_row(
                    catalog=catalog,
                    user=user,
                    session_id=session_id,
                    event_name="energy_update",
                    event_params=dynamic_fill_params(
                        "energy_update",
                        catalog,
                        rng,
                        {
                            "energy_update": {
                                "kind": "refill",
                                "spinsBefore": 0,
                                "spinsAfter": refill,
                                "nextRefillTime": int(
                                    (cur + timedelta(minutes=5)).timestamp() * 1000
                                ),
                            }
                        },
                    ),
                    ts=cur,
                    platform=platform,
                    country=country,
                )
            )
            user.energy = refill
            cur += timedelta(seconds=rng.randint(1, 4))

        eb = user.energy
        user.spin_index += 1
        user.total_spins_village += 1
        user.energy = max(0, user.energy - 1)

        symbols, pay, action, spins_b, det = compute_spin_outcome(rng, eco, user)
        user.coins += pay
        if spins_b:
            user.energy = min(max_e, user.energy + spins_b)

        rows.append(
            make_envelope_row(
                catalog=catalog,
                user=user,
                session_id=session_id,
                event_name="spin",
                event_params={
                    "spinIndex": user.spin_index,
                    "energyBefore": eb,
                    "energyAfter": user.energy,
                    "symbols": symbols,
                    "payoutCoins": pay,
                    "actionTriggered": action,
                    "detailedResult": det,
                    "spinsBonus": spins_b,
                    "reactionTimeMs": rng.randint(120, 2800),
                },
                ts=cur,
                platform=platform,
                country=country,
            )
        )

        # Raid / attack side flows (short)
        if action == "raid":
            rival = rng.choice(BOT_NAMES)
            cap = scaled_coin(50000, factor, user.currentVillage) * 2 + scaled_coin(
                1000000, factor, user.currentVillage
            )
            stolen = rng.randint(
                scaled_coin(50000, factor, user.currentVillage),
                min(cap, scaled_coin(800000, factor, user.currentVillage)),
            )
            user.coins += stolen
            cur += timedelta(seconds=rng.randint(2, 6))
            rows.append(
                make_envelope_row(
                    catalog=catalog,
                    user=user,
                    session_id=session_id,
                    event_name="raid_start",
                    event_params={
                        "rivalName": rival,
                        "raidStealCap": cap,
                    },
                    ts=cur,
                    platform=platform,
                    country=country,
                )
            )
            cur += timedelta(seconds=rng.randint(8, 20))
            rows.append(
                make_envelope_row(
                    catalog=catalog,
                    user=user,
                    session_id=session_id,
                    event_name="raid_end",
                    event_params={
                        "totalStolen": stolen,
                        "perfectRaid": stolen >= int(cap * 0.85),
                    },
                    ts=cur,
                    platform=platform,
                    country=country,
                )
            )

        if action == "attack":
            tgt = rng.choice(BOT_NAMES)
            blocked = rng.random() < 0.35
            rew_key = "attack_blocked" if blocked else "attack_hit"
            rew = scaled_coin(float(payouts.get(rew_key, 50000)), factor, user.currentVillage)
            user.coins += rew
            cur += timedelta(seconds=rng.randint(2, 5))
            rows.append(
                make_envelope_row(
                    catalog=catalog,
                    user=user,
                    session_id=session_id,
                    event_name="attack_start",
                    event_params={
                        "targetName": tgt,
                        "targetUserId": f"bot_{tgt.lower()}",
                    },
                    ts=cur,
                    platform=platform,
                    country=country,
                )
            )
            cur += timedelta(seconds=rng.randint(5, 15))
            rows.append(
                make_envelope_row(
                    catalog=catalog,
                    user=user,
                    session_id=session_id,
                    event_name="attack_end",
                    event_params={
                        "targetName": tgt,
                        "result": "blocked" if blocked else "hit",
                        "reward": rew,
                        "buildingName": rng.choice(list(VILLAGE_ITEMS)),
                    },
                    ts=cur,
                    platform=platform,
                    country=country,
                )
            )

        cur += timedelta(seconds=rng.randint(3, 25))

        # building upgrade attempt
        if user.stars < 25 and rng.random() < 0.22:
            b = rng.choice(list(VILLAGE_ITEMS))
            cur_st = user.building_stars.get(b, 0)
            if cur_st < 5:
                cost = upgrade_cost(b, cur_st, buildings_cfg, factor, user.currentVillage)
                if user.coins >= cost:
                    user.coins -= cost
                    user.building_stars[b] = cur_st + 1
                    user.sync_stars()
                    rows.append(
                        make_envelope_row(
                            catalog=catalog,
                            user=user,
                            session_id=session_id,
                            event_name="building_upgrade",
                            event_params={
                                "status": "success",
                                "building": b,
                                "levelAfter": cur_st + 1,
                                "cost": cost,
                                "isFree": False,
                            },
                            ts=cur,
                            platform=platform,
                            country=country,
                        )
                    )
                    if user.stars >= 25:
                        vstart = datetime.fromisoformat(
                            user.village_started_at.replace("Z", "+00:00")
                        )
                        time_spent = max(1, int((cur - vstart).total_seconds()))
                        rows.append(
                            make_envelope_row(
                                catalog=catalog,
                                user=user,
                                session_id=session_id,
                                event_name="village_complete",
                                event_params={
                                    "villageId": user.currentVillage,
                                    "totalSpins": user.total_spins_village,
                                    "timeSpent": time_spent,
                                },
                                ts=cur,
                                platform=platform,
                                country=country,
                            )
                        )
                        rc, rs = eco.village_complete_reward(user.condition)
                        user.coins += scaled_coin(rc, factor, user.currentVillage)
                        user.currentVillage += 1
                        user.building_stars = {x: 0 for x in VILLAGE_ITEMS}
                        user.sync_stars()
                        user.total_spins_village = 0
                        user.village_started_at = cur.isoformat().replace("+00:00", "Z")
                    cur += timedelta(seconds=rng.randint(2, 8))

    # session_end
    total_sec = max(1, int((session_end - session_start).total_seconds()))
    rows.append(
        make_envelope_row(
            catalog=catalog,
            user=user,
            session_id=session_id,
            event_name="session_end",
            event_params={
                "totalSessionTime": total_sec,
                "finalLevel": user.currentVillage,
                "finalCoins": user.coins,
            },
            ts=min(session_end, cur + timedelta(seconds=1)),
            platform=platform,
            country=country,
        )
    )

    user.lastPlayedTimestamp = session_end.isoformat().replace("+00:00", "Z")
    return rows


def load_state(path: Path) -> Tuple[List[UserState], int]:
    if not path.is_file():
        return [], 0
    try:
        data = load_json(path)
    except (json.JSONDecodeError, OSError):
        return [], 0
    users_raw = data.get("users") or []
    seq = int(data.get("nextUserSeq", 0))
    users: List[UserState] = []
    for u in users_raw:
        try:
            bs = u.get("building_stars") or {b: 0 for b in VILLAGE_ITEMS}
            users.append(
                UserState(
                    userId=str(u["userId"]),
                    playerName=str(u.get("playerName", "Player")),
                    coins=int(u.get("coins", 0)),
                    currentVillage=int(u.get("currentVillage", 1)),
                    stars=int(u.get("stars", 0)),
                    lastPlayedTimestamp=str(
                        u.get("lastPlayedTimestamp", datetime.now(timezone.utc).isoformat())
                    ),
                    condition=str(u.get("condition", "A")),
                    energy=int(u.get("energy", 10)),
                    spin_index=int(u.get("spin_index", 0)),
                    building_stars={b: int(bs.get(b, 0)) for b in VILLAGE_ITEMS},
                    total_spins_village=int(u.get("total_spins_village", 0)),
                    village_started_at=u.get("village_started_at"),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    for u in users:
        u.sync_stars()
    return users, seq


def save_state(path: Path, users: List[UserState], next_seq: int) -> None:
    payload = {
        "nextUserSeq": next_seq,
        "users": [
            {
                "userId": u.userId,
                "playerName": u.playerName,
                "coins": u.coins,
                "currentVillage": u.currentVillage,
                "stars": u.stars,
                "lastPlayedTimestamp": u.lastPlayedTimestamp,
                "condition": u.condition,
                "energy": u.energy,
                "spin_index": u.spin_index,
                "building_stars": u.building_stars,
                "total_spins_village": u.total_spins_village,
                "village_started_at": u.village_started_at,
            }
            for u in users
        ],
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def parse_day_bounds(days_back: int) -> Tuple[datetime, datetime]:
    today = datetime.now(timezone.utc).date()
    start_day = today - timedelta(days=days_back - 1)
    start_dt = datetime(start_day.year, start_day.month, start_day.day, tzinfo=timezone.utc)
    end_dt = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc)
    return start_dt, end_dt


def load_bq_config(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing config: {path}\nCopy simulation/bq_config.example.json to bq_config.json and edit."
        )
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def resolve_bq_data_dir(cfg: Dict[str, Any]) -> Path:
    raw = cfg.get("data_dir")
    if raw is None or raw == "":
        return OUTPUT_DIR
    p = Path(raw)
    if not p.is_absolute():
        p = (SIM_DIR / p).resolve()
    return p


def collect_bq_jsonl_files(data_dir: Path) -> List[Path]:
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")
    files = sorted(data_dir.glob("events_*.jsonl"))
    return [f for f in files if f.is_file()]


def build_bq_load_command(
    *,
    project_id: str,
    dataset: str,
    table: str,
    source_files: List[Path],
    replace_table: bool,
) -> List[str]:
    table_ref = f"{dataset}.{table}"
    cmd: List[str] = [
        "bq",
        "load",
        "--project_id",
        project_id,
        "--source_format=NEWLINE_DELIMITED_JSON",
        "--autodetect",
    ]
    if replace_table:
        cmd.append("--replace")
    cmd.append(table_ref)
    cmd.extend(str(p) for p in source_files)
    return cmd


def main_upload_bq() -> None:
    parser = argparse.ArgumentParser(description="Upload simulation events_*.jsonl to BigQuery")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_BQ_CONFIG_PATH,
        help=f"Path to JSON config (default: {DEFAULT_BQ_CONFIG_PATH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print bq command and exit without running",
    )
    args = parser.parse_args()
    cfg_path = args.config.resolve()

    cfg = load_bq_config(cfg_path)
    project_id = (cfg.get("project_id") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
    dataset = (cfg.get("dataset") or "").strip()
    table = (cfg.get("table") or "").strip()
    if not project_id:
        print("Config error: project_id is required (or set GOOGLE_CLOUD_PROJECT).", file=sys.stderr)
        sys.exit(1)
    if not dataset or not table:
        print("Config error: dataset and table are required.", file=sys.stderr)
        sys.exit(1)

    replace_table = bool(cfg.get("replace_table", False))
    data_dir = resolve_bq_data_dir(cfg)
    files = collect_bq_jsonl_files(data_dir)

    if not files:
        print(f"No events_*.jsonl files under {data_dir}; nothing to upload.", file=sys.stderr)
        sys.exit(1)

    cmd = build_bq_load_command(
        project_id=project_id,
        dataset=dataset,
        table=table,
        source_files=files,
        replace_table=replace_table,
    )

    if args.dry_run:
        print("Dry run — would execute:")
        print(" ".join(shlex.quote(str(x)) for x in cmd))
        return

    print(f"Loading {len(files)} file(s) into `{project_id}.{dataset}.{table}` …")
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print(
            "Error: `bq` not found. Install Google Cloud SDK and ensure `bq` is on PATH.\n"
            "https://cloud.google.com/sdk/docs/install",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"bq load failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode or 1)

    print("Done.")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "upload-bq":
        del sys.argv[1]
        main_upload_bq()
        return

    parser = argparse.ArgumentParser(description="PlayPLTX synthetic event generator")
    parser.add_argument(
        "--days-back",
        type=int,
        default=1,
        help="Simulate calendar days from N days ago through today (inclusive).",
    )
    args = parser.parse_args()
    days_back = max(1, args.days_back)

    if not EVENTS_JSON.is_file() or not ECONOMY_JSON.is_file():
        raise SystemExit(f"Missing config: {EVENTS_JSON} or {ECONOMY_JSON}")

    out_dir = ensure_output_dir()
    state_path = out_dir / STATE_FILENAME

    catalog = EventCatalog(load_json(EVENTS_JSON))
    eco = EconomyConfig(load_json(ECONOMY_JSON))

    users, next_seq = load_state(state_path)
    rng = random.Random()

    start_range, end_range = parse_day_bounds(days_back)

    # Inject new users periodically (~15% chance per day of simulation horizon)
    day_cursor = start_range.date()
    end_date = end_range.date()
    while day_cursor <= end_date:
        if rng.random() < 0.15 or len(users) == 0:
            next_seq += 1
            users.append(UserState.new_user(next_seq, rng))
        day_cursor += timedelta(days=1)

    all_rows: List[Tuple[datetime, Dict[str, Any]]] = []

    day = start_range.date()
    while day <= end_range.date():
        day_start = datetime(day.year, day.month, day.day, 8, 0, 0, tzinfo=timezone.utc)
        day_end = datetime(day.year, day.month, day.day, 23, 0, 0, tzinfo=timezone.utc)

        for user in users:
            if rng.random() > 0.55:
                continue
            s0 = day_start + timedelta(
                minutes=rng.randint(0, 120), seconds=rng.randint(0, 59)
            )
            dur_min = rng.randint(4, 55)
            s1 = min(s0 + timedelta(minutes=dur_min), day_end)
            if s1 <= s0:
                continue
            seed = hash((user.userId, day.isoformat())) % (2**32)
            day_rng = random.Random(seed)
            session_rows = simulate_session(
                user, catalog, eco, day_rng, s0, s1
            )
            for row in session_rows:
                ts = datetime.fromisoformat(
                    row["timestamp"].replace("Z", "+00:00")
                )
                all_rows.append((ts, row))

        day += timedelta(days=1)

    all_rows.sort(key=lambda x: x[0])

    # Write per-day JSONL files
    by_day: Dict[str, List[str]] = {}
    for ts, row in all_rows:
        key = ts.strftime("%Y-%m-%d")
        by_day.setdefault(key, []).append(json.dumps(row, separators=(",", ":")))

    for dkey, lines in sorted(by_day.items()):
        fp = out_dir / f"events_{dkey}.jsonl"
        with fp.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            if lines:
                f.write("\n")

    save_state(state_path, users, next_seq)
    print(
        f"Wrote {len(all_rows)} events to {out_dir} "
        f"(state: {len(users)} users, nextSeq={next_seq})"
    )


if __name__ == "__main__":
    main()
