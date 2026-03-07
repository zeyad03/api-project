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
#  F1 TRIVIA FACTS  (hand-curated – not available in the Kaggle dataset)
# ═══════════════════════════════════════════════════════════════════════════════
FACTS = [
    {"content": "The first ever F1 race was the 1950 British Grand Prix at Silverstone, won by Giuseppe Farina.", "category": "history", "approved": True},
    {"content": "An F1 car can accelerate from 0-100 mph and brake back to 0 in under 5 seconds.", "category": "technical", "approved": True},
    {"content": "Ferrari is the only team to have competed in every single F1 season since the championship began in 1950.", "category": "history", "approved": True},
    {"content": "The steering wheel of a modern F1 car costs around $50,000-$100,000 and has over 20 buttons and switches.", "category": "technical", "approved": True},
    {"content": "Lewis Hamilton holds the record for the most race wins in F1 history with over 100 victories.", "category": "records", "approved": True},
    {"content": "An F1 car generates enough downforce to theoretically drive upside down on a ceiling at speed.", "category": "technical", "approved": True},
    {"content": "Michael Schumacher once won the Belgian Grand Prix from 6th on the grid – in the rain – during his very first full season.", "category": "history", "approved": True},
    {"content": "The Monaco Grand Prix is the slowest race on the calendar but considered the most prestigious.", "category": "fun", "approved": True},
    {"content": "F1 drivers can lose up to 3 kg of body weight through sweat during a single race.", "category": "fun", "approved": True},
    {"content": "Ayrton Senna won 6 Monaco Grand Prix, more than any other driver in history.", "category": "records", "approved": True},
    {"content": "An F1 pit stop can be completed in under 2 seconds – the record is 1.80 seconds by Red Bull.", "category": "records", "approved": True},
    {"content": "The DRS (Drag Reduction System) was introduced in 2011 to promote overtaking.", "category": "technical", "approved": True},
    {"content": "Kimi Räikkönen famously ate an ice cream on the pit wall during a race when he retired from the 2009 Malaysian Grand Prix.", "category": "fun", "approved": True},
    {"content": "The youngest F1 World Champion is Sebastian Vettel, who won his first title aged 23 in 2010.", "category": "records", "approved": True},
    {"content": "F1 brakes can reach temperatures of over 1,000°C during heavy braking zones.", "category": "technical", "approved": True},
    {"content": "Juan Manuel Fangio won 5 World Championships in the 1950s, a record that stood for 46 years.", "category": "history", "approved": True},
    {"content": "A Formula 1 car has about 80,000 components. If it were assembled 99.9% correctly, it would start with 80 things wrong.", "category": "technical", "approved": True},
    {"content": "The longest F1 race by distance was the 1951 Indianapolis 500, which counted towards the F1 championship.", "category": "history", "approved": True},
    {"content": "Max Verstappen scored 575 points in the 2023 season, winning 19 out of 22 races – both all-time records.", "category": "records", "approved": True},
    {"content": "In 2005, only 6 cars started the US Grand Prix at Indianapolis due to tyre safety concerns – the most bizarre race in F1 history.", "category": "fun", "approved": True},
    {"content": "An F1 car's energy recovery system (ERS) can produce up to 163 horsepower from waste energy.", "category": "technical", "approved": True},
    {"content": "Lando Norris streams on Twitch and is one of the most popular gamers among current F1 drivers.", "category": "fun", "approved": True},
    {"content": "The Halo safety device, introduced in 2018, can withstand the weight of a London double-decker bus.", "category": "technical", "approved": True},
    {"content": "Fernando Alonso became the youngest World Champion in 2005 at age 24, breaking a record that had stood since 1972.", "category": "records", "approved": True},
    {"content": "In 2020, Pierre Gasly won the Italian Grand Prix for AlphaTauri – one of the biggest upsets in modern F1.", "category": "fun", "approved": True},
    {"content": "F1 tyres are filled with nitrogen rather than regular air to maintain more consistent pressure.", "category": "technical", "approved": True},
    {"content": "Niki Lauda returned to race just 42 days after his horrific 1976 Nürburgring crash, finishing 4th.", "category": "history", "approved": True},
    {"content": "The cost cap for F1 teams was introduced in 2021, set at $145 million per season.", "category": "fun", "approved": True},
    {"content": "Charles Leclerc grew up in Monaco and used to play with Jules Bianchi as a child.", "category": "fun", "approved": True},
    {"content": "An F1 car's V6 turbo-hybrid engine revs up to 15,000 RPM and produces around 1,000 horsepower.", "category": "technical", "approved": True},
]


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
