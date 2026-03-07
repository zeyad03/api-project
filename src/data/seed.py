"""Seed script – populates MongoDB with F1 data from the Kaggle dataset.

Uses the ``jtrotman/formula-1-race-data`` Kaggle dataset for drivers and
teams (constructors).  Career statistics (wins, podiums, poles, championships)
are computed from the historical results and standings CSVs.  Trivia facts
are still provided as hand-curated data.

Run with:  python -m src.data.seed
"""

import asyncio
import csv
import os
from collections import defaultdict

import kagglehub
from motor.motor_asyncio import AsyncIOMotorClient

from src.config.settings import settings
from src.db.collections import collections
from src.models.common import utc_now


# ═══════════════════════════════════════════════════════════════════════════════
#  KAGGLE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _download_dataset() -> str:
    """Download (or use cached) Kaggle F1 race-data and return the path."""
    path = kagglehub.dataset_download("jtrotman/formula-1-race-data")
    print(f"📦  Kaggle dataset path: {path}")
    return path


def _read_csv(dataset_path: str, filename: str) -> list[dict]:
    """Read a CSV file from the dataset into a list of dicts."""
    with open(os.path.join(dataset_path, filename), encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ═══════════════════════════════════════════════════════════════════════════════
#  BUILD TEAMS FROM KAGGLE DATA
# ═══════════════════════════════════════════════════════════════════════════════

def _build_teams(dataset_path: str) -> list[dict]:
    """Return team documents for every constructor that raced in the latest
    season found in the dataset, enriched with all-time championship counts."""

    constructors = _read_csv(dataset_path, "constructors.csv")
    races = _read_csv(dataset_path, "races.csv")
    results = _read_csv(dataset_path, "results.csv")
    con_standings = _read_csv(dataset_path, "constructor_standings.csv")

    constructors_by_id = {c["constructorId"]: c for c in constructors}

    # Latest season & its race IDs
    latest_year = max(r["year"] for r in races)
    latest_race_ids = {r["raceId"] for r in races if r["year"] == latest_year}

    # Constructor IDs that raced in the latest season
    active_cids = {r["constructorId"] for r in results
                   if r["raceId"] in latest_race_ids}

    # Constructor championship counts (position == 1 at final race of each year)
    year_races: dict[str, list[int]] = defaultdict(list)
    for r in races:
        year_races[r["year"]].append(int(r["raceId"]))
    final_race_ids = {str(max(rids)) for rids in year_races.values()}

    champ_counts: dict[str, int] = defaultdict(int)
    for s in con_standings:
        if s["raceId"] in final_race_ids and s["position"] == "1":
            champ_counts[s["constructorId"]] += 1

    teams: list[dict] = []
    for cid in sorted(active_cids, key=int):
        c = constructors_by_id[cid]
        teams.append({
            "name": c["name"],
            "full_name": "",
            "base": "",
            "team_principal": "",
            "championships": champ_counts.get(cid, 0),
            "first_entry": 0,
            "car": "",
            "engine": "",
            "nationality": c.get("nationality", ""),
            "active": True,
        })
    return teams


# ═══════════════════════════════════════════════════════════════════════════════
#  BUILD DRIVERS FROM KAGGLE DATA
# ═══════════════════════════════════════════════════════════════════════════════

def _build_drivers(dataset_path: str) -> list[dict]:
    """Return driver documents for every driver that raced in the latest
    season, with career wins / podiums / poles / championships computed from
    the full historical dataset."""

    drivers_csv = _read_csv(dataset_path, "drivers.csv")
    races = _read_csv(dataset_path, "races.csv")
    results = _read_csv(dataset_path, "results.csv")
    driver_standings = _read_csv(dataset_path, "driver_standings.csv")
    constructors = _read_csv(dataset_path, "constructors.csv")

    drivers_by_id = {d["driverId"]: d for d in drivers_csv}
    constructors_by_id = {c["constructorId"]: c for c in constructors}

    # Latest season
    latest_year = max(r["year"] for r in races)
    latest_race_ids = {r["raceId"] for r in races if r["year"] == latest_year}

    # Driver → constructor mapping for latest season (last entry wins)
    driver_team: dict[str, str] = {}
    for r in results:
        if r["raceId"] in latest_race_ids:
            driver_team[r["driverId"]] = r["constructorId"]

    active_dids = set(driver_team.keys())

    # Career stats: wins, podiums, poles
    career_wins: dict[str, int] = defaultdict(int)
    career_podiums: dict[str, int] = defaultdict(int)
    career_poles: dict[str, int] = defaultdict(int)
    for r in results:
        did = r["driverId"]
        if did not in active_dids:
            continue
        if r["positionOrder"] == "1":
            career_wins[did] += 1
        if r["positionOrder"] in ("1", "2", "3"):
            career_podiums[did] += 1
        if r["grid"] == "1":
            career_poles[did] += 1

    # Championship counts
    year_races: dict[str, list[int]] = defaultdict(list)
    for r in races:
        year_races[r["year"]].append(int(r["raceId"]))
    final_race_ids = {str(max(rids)) for rids in year_races.values()}

    champ_counts: dict[str, int] = defaultdict(int)
    for s in driver_standings:
        if s["raceId"] in final_race_ids and s["position"] == "1":
            champ_counts[s["driverId"]] += 1

    drivers: list[dict] = []
    for did in sorted(active_dids, key=int):
        d = drivers_by_id[did]
        cid = driver_team[did]
        team_name = constructors_by_id.get(cid, {}).get("name", "")
        number_raw = d.get("number", "0")
        number = int(number_raw) if number_raw not in ("\\N", "", None) else 0

        drivers.append({
            "name": f"{d['forename']} {d['surname']}",
            "number": number,
            "team": team_name,
            "nationality": d.get("nationality", ""),
            "date_of_birth": d.get("dob", ""),
            "championships": champ_counts.get(did, 0),
            "wins": career_wins.get(did, 0),
            "podiums": career_podiums.get(did, 0),
            "poles": career_poles.get(did, 0),
            "bio": "",
            "active": True,
        })
    return drivers


# ═══════════════════════════════════════════════════════════════════════════════
#  SEED FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

async def seed():
    # ── Download / cache the Kaggle dataset ──────────────────────────────────
    dataset_path = _download_dataset()

    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client.get_database(settings.DB_NAME)

    now = utc_now()

    # ── Teams ────────────────────────────────────────────────────────────────
    existing_teams = await db[collections.teams].count_documents({})
    if existing_teams == 0:
        teams = _build_teams(dataset_path)
        for t in teams:
            t["created_at"] = now
        await db[collections.teams].insert_many(teams)
        print(f"✅  Seeded {len(teams)} teams from Kaggle dataset")
    else:
        print(f"ℹ️  Teams collection already has {existing_teams} documents, skipping")

    # ── Drivers ──────────────────────────────────────────────────────────────
    existing_drivers = await db[collections.drivers].count_documents({})
    if existing_drivers == 0:
        drivers = _build_drivers(dataset_path)
        for d in drivers:
            d["created_at"] = now
        await db[collections.drivers].insert_many(drivers)
        print(f"✅  Seeded {len(drivers)} drivers from Kaggle dataset")
    else:
        print(f"ℹ️  Drivers collection already has {existing_drivers} documents, skipping")

    # ── Facts ────────────────────────────────────────────────────────────────
    existing_facts = await db[collections.facts].count_documents({})
    if existing_facts == 0:
        for f in FACTS:
            f["created_at"] = now
            f["submitted_by"] = "system"
            f["likes"] = 0
            f["liked_by"] = []
        await db[collections.facts].insert_many(FACTS)
        print(f"✅  Seeded {len(FACTS)} facts")
    else:
        print(f"ℹ️  Facts collection already has {existing_facts} documents, skipping")

    # ── Indexes ──────────────────────────────────────────────────────────────
    await db[collections.users].create_index("username", unique=True)
    await db[collections.users].create_index("email", unique=True)
    await db[collections.drivers].create_index("name")
    await db[collections.teams].create_index("name")
    await db[collections.predictions].create_index(
        [("user_id", 1), ("season", 1), ("category", 1)], unique=True
    )
    await db[collections.head_to_head_votes].create_index(
        [("driver1_id", 1), ("driver2_id", 1), ("user_id", 1)], unique=True
    )
    print("✅  Database indexes created")

    client.close()
    print("\n🏁  Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
