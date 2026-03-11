"""Seed script – populates MongoDB with F1 data from the Kaggle dataset.

Uses the ``jtrotman/formula-1-race-data`` Kaggle dataset to seed the current
grid, historical race data, and compact analytical summaries. Raw CSVs that are
small enough to be useful in the API are stored directly; very large inputs like
``lap_times.csv`` are converted into summary documents.

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


CIRCUITS_CSV = "circuits.csv"
CONSTRUCTOR_RESULTS_CSV = "constructor_results.csv"
CONSTRUCTOR_STANDINGS_CSV = "constructor_standings.csv"
CONSTRUCTORS_CSV = "constructors.csv"
DRIVERS_CSV = "drivers.csv"
DRIVER_STANDINGS_CSV = "driver_standings.csv"
LAP_TIMES_CSV = "lap_times.csv"
RACES_CSV = "races.csv"
RESULTS_CSV = "results.csv"
SEASONS_CSV = "seasons.csv"
SPRINT_RESULTS_CSV = "sprint_results.csv"
STATUS_CSV = "status.csv"


REQUIRED_DATASET_FILES = (
    CIRCUITS_CSV,
    CONSTRUCTOR_RESULTS_CSV,
    CONSTRUCTOR_STANDINGS_CSV,
    CONSTRUCTORS_CSV,
    DRIVERS_CSV,
    LAP_TIMES_CSV,
    RACES_CSV,
    RESULTS_CSV,
    SEASONS_CSV,
    STATUS_CSV,
    SPRINT_RESULTS_CSV,
)

OPTIONAL_DATASET_FILES = (DRIVER_STANDINGS_CSV,)

NULL_VALUES = {"\\N", "", None}


def _download_dataset() -> str:
    """Download (or use cached) Kaggle F1 race-data and return the path."""
    path = kagglehub.dataset_download("jtrotman/formula-1-race-data")
    print(f"Kaggle dataset path: {path}")
    return path


def _read_csv(dataset_path: str, filename: str) -> list[dict]:
    """Read a CSV file from the dataset into a list of dicts."""
    with open(os.path.join(dataset_path, filename), encoding="utf-8") as file_handle:
        return list(csv.DictReader(file_handle))


def _load_dataset_tables(dataset_path: str) -> dict[str, list[dict]]:
    """Load all required dataset tables plus optional ones if present."""
    tables: dict[str, list[dict]] = {}
    for filename in REQUIRED_DATASET_FILES:
        tables[filename] = _read_csv(dataset_path, filename)
    for filename in OPTIONAL_DATASET_FILES:
        full_path = os.path.join(dataset_path, filename)
        if os.path.exists(full_path):
            tables[filename] = _read_csv(dataset_path, filename)
    return tables


def _full_name(row: dict) -> str:
    return f"{row.get('forename', '')} {row.get('surname', '')}".strip()


def _clean_value(value: str | None, default: str = "") -> str:
    return default if value in NULL_VALUES else str(value)


def _as_int(value: str | None, default: int = 0) -> int:
    if value in NULL_VALUES:
        return default
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def _as_float(value: str | None, default: float = 0.0) -> float:
    if value in NULL_VALUES:
        return default
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def _latest_year(races: list[dict]) -> int:
    return max(_as_int(race["year"]) for race in races)


def _final_race_ids_by_year(races: list[dict]) -> dict[int, str]:
    year_races: dict[int, list[int]] = defaultdict(list)
    for race in races:
        year_races[_as_int(race["year"])].append(_as_int(race["raceId"]))
    return {year: str(max(race_ids)) for year, race_ids in year_races.items() if race_ids}


def _is_classified_finish(position_text: str, status_text: str) -> bool:
    if position_text.isdigit():
        return True
    if status_text.startswith("+"):
        return True
    return status_text.lower() == "finished"


def _compute_driver_championship_counts(
    races: list[dict], driver_standings: list[dict]
) -> dict[str, int]:
    final_race_ids = set(_final_race_ids_by_year(races).values())
    counts: dict[str, int] = defaultdict(int)
    for standing in driver_standings:
        if standing.get("raceId") in final_race_ids and standing.get("position") == "1":
            counts[standing["driverId"]] += 1
    return counts


def _compute_constructor_championship_counts(
    races: list[dict], constructor_standings: list[dict]
) -> dict[str, int]:
    final_race_ids = set(_final_race_ids_by_year(races).values())
    counts: dict[str, int] = defaultdict(int)
    for standing in constructor_standings:
        if standing.get("raceId") in final_race_ids and standing.get("position") == "1":
            counts[standing["constructorId"]] += 1
    return counts


def _champion_lookup(
    *,
    final_race_ids: dict[int, str],
    standings: list[dict],
    entity_id_key: str,
    refs: dict[str, dict],
    name_getter,
) -> dict[int, tuple[str, str]]:
    champions: dict[int, tuple[str, str]] = {}
    year_by_race_id = {race_id: year for year, race_id in final_race_ids.items()}
    for standing in standings:
        race_id = standing.get("raceId")
        year = year_by_race_id.get(race_id)
        if year is None or standing.get("position") != "1":
            continue
        entity_id = standing[entity_id_key]
        champions[year] = (entity_id, name_getter(refs.get(entity_id, {})))
    return champions


def _new_driver_season_stat(row: dict) -> dict:
    return {
        "season_year": row["season_year"],
        "driver_id": row["driver_id"],
        "driver_name": row["driver_name"],
        "constructor_id": row["constructor_id"],
        "constructor_name": row["constructor_name"],
        "starts": 0,
        "wins": 0,
        "podiums": 0,
        "poles": 0,
        "race_points": 0.0,
        "sprint_points": 0.0,
        "sprint_wins": 0,
        "sprint_podiums": 0,
        "classified_finishes": 0,
        "dnfs": 0,
        "best_finish": 0,
        "championship_position": 0,
        "champion": False,
    }


def _apply_race_result_to_driver_stat(stat: dict, row: dict) -> None:
    stat["starts"] += 1
    stat["race_points"] += row["points"]
    if row["position_order"] == 1:
        stat["wins"] += 1
    if row["position_order"] in (1, 2, 3):
        stat["podiums"] += 1
    if row["grid"] == 1:
        stat["poles"] += 1
    if row["classified_finish"]:
        stat["classified_finishes"] += 1
    else:
        stat["dnfs"] += 1
    if row["position_order"] > 0 and (
        stat["best_finish"] == 0 or row["position_order"] < stat["best_finish"]
    ):
        stat["best_finish"] = row["position_order"]
    stat["constructor_id"] = row["constructor_id"]
    stat["constructor_name"] = row["constructor_name"]


def _apply_sprint_result_to_driver_stat(stat: dict, row: dict) -> None:
    stat["sprint_points"] += row["points"]
    if row["position_order"] == 1:
        stat["sprint_wins"] += 1
    if row["position_order"] in (1, 2, 3):
        stat["sprint_podiums"] += 1


def _final_driver_positions(tables: dict[str, list[dict]]) -> dict[tuple[int, int], int]:
    races_by_id = {row["raceId"]: row for row in tables[RACES_CSV]}
    final_race_ids = _final_race_ids_by_year(tables[RACES_CSV])
    final_positions: dict[tuple[int, int], int] = {}
    for standing in tables.get(DRIVER_STANDINGS_CSV, []):
        race = races_by_id.get(standing.get("raceId", ""))
        if not race:
            continue
        year = _as_int(race["year"])
        if standing.get("raceId") == final_race_ids.get(year):
            final_positions[(year, _as_int(standing["driverId"]))] = _as_int(standing.get("position"))
    return final_positions


def _build_teams(tables: dict[str, list[dict]]) -> list[dict]:
    """Build current-team profile documents for constructors active in the latest season."""
    constructors = tables[CONSTRUCTORS_CSV]
    races = tables[RACES_CSV]
    results = tables[RESULTS_CSV]
    constructor_standings = tables[CONSTRUCTOR_STANDINGS_CSV]
    constructors_by_id = {row["constructorId"]: row for row in constructors}
    latest_year = _latest_year(races)
    latest_race_ids = {row["raceId"] for row in races if _as_int(row["year"]) == latest_year}
    active_constructor_ids = {
        row["constructorId"] for row in results if row["raceId"] in latest_race_ids
    }
    races_by_id = {row["raceId"]: row for row in races}
    first_entry_by_constructor: dict[str, int] = {}
    for row in results:
        constructor_id = row["constructorId"]
        race = races_by_id.get(row["raceId"])
        if not race:
            continue
        year = _as_int(race["year"])
        current_first = first_entry_by_constructor.get(constructor_id)
        if current_first is None or year < current_first:
            first_entry_by_constructor[constructor_id] = year

    championship_counts = _compute_constructor_championship_counts(races, constructor_standings)

    docs: list[dict] = []
    for constructor_id in sorted(active_constructor_ids, key=int):
        constructor = constructors_by_id[constructor_id]
        docs.append(
            {
                "name": constructor["name"],
                "full_name": constructor["name"],
                "base": "",
                "team_principal": "",
                "nationality": _clean_value(constructor.get("nationality")),
                "championships": championship_counts.get(constructor_id, 0),
                "first_entry": first_entry_by_constructor.get(constructor_id, 0),
                "car": "",
                "engine": "",
                "active": True,
                "kaggle_constructor_id": _as_int(constructor_id),
                "constructor_ref": _clean_value(constructor.get("constructorRef")),
            }
        )
    return docs


def _compute_career_stats(results: list[dict], active_driver_ids: set[str]) -> tuple[dict, dict, dict]:
    """Compute career wins, podiums, and poles for active drivers."""
    career_wins: dict[str, int] = defaultdict(int)
    career_podiums: dict[str, int] = defaultdict(int)
    career_poles: dict[str, int] = defaultdict(int)

    for row in results:
        driver_id = row["driverId"]
        if driver_id not in active_driver_ids:
            continue
        if row["positionOrder"] == "1":
            career_wins[driver_id] += 1
        if row["positionOrder"] in ("1", "2", "3"):
            career_podiums[driver_id] += 1
        if row["grid"] == "1":
            career_poles[driver_id] += 1

    return career_wins, career_podiums, career_poles


def _parse_driver_number(number_raw: str) -> int:
    """Parse driver number, returning 0 for invalid values."""
    return int(number_raw) if number_raw not in NULL_VALUES else 0


def _build_drivers(tables: dict[str, list[dict]]) -> list[dict]:
    """Build current-driver profile documents from the latest season."""
    drivers_csv = tables[DRIVERS_CSV]
    races = tables[RACES_CSV]
    results = tables[RESULTS_CSV]
    constructors = tables[CONSTRUCTORS_CSV]
    driver_standings = tables.get(DRIVER_STANDINGS_CSV, [])

    drivers_by_id = {row["driverId"]: row for row in drivers_csv}
    constructors_by_id = {row["constructorId"]: row for row in constructors}
    latest_year = _latest_year(races)
    latest_race_ids = {row["raceId"] for row in races if _as_int(row["year"]) == latest_year}
    driver_team: dict[str, str] = {}
    for row in results:
        if row["raceId"] in latest_race_ids:
            driver_team[row["driverId"]] = row["constructorId"]

    active_driver_ids = set(driver_team.keys())
    career_wins, career_podiums, career_poles = _compute_career_stats(results, active_driver_ids)
    championship_counts = _compute_driver_championship_counts(races, driver_standings)

    docs: list[dict] = []
    for driver_id in sorted(active_driver_ids, key=int):
        driver = drivers_by_id[driver_id]
        constructor_id = driver_team[driver_id]
        constructor_name = constructors_by_id.get(constructor_id, {}).get("name", "")
        docs.append(
            {
                "name": f"{driver['forename']} {driver['surname']}",
                "number": _parse_driver_number(driver.get("number", "0")),
                "team": constructor_name,
                "nationality": _clean_value(driver.get("nationality")),
                "date_of_birth": _clean_value(driver.get("dob")),
                "championships": championship_counts.get(driver_id, 0),
                "wins": career_wins.get(driver_id, 0),
                "podiums": career_podiums.get(driver_id, 0),
                "poles": career_poles.get(driver_id, 0),
                "bio": "",
                "active": True,
                "kaggle_driver_id": _as_int(driver_id),
                "driver_ref": _clean_value(driver.get("driverRef")),
                "code": _clean_value(driver.get("code")),
            }
        )
    return docs


def _build_circuits(tables: dict[str, list[dict]]) -> list[dict]:
    circuits = tables[CIRCUITS_CSV]
    races = tables[RACES_CSV]
    latest_year = _latest_year(races)
    races_by_circuit: dict[str, list[dict]] = defaultdict(list)
    for race in races:
        races_by_circuit[race["circuitId"]].append(race)

    docs: list[dict] = []
    for circuit in circuits:
        circuit_races = races_by_circuit.get(circuit["circuitId"], [])
        years = [_as_int(race["year"]) for race in circuit_races]
        docs.append(
            {
                "circuit_id": _as_int(circuit["circuitId"]),
                "circuit_ref": _clean_value(circuit.get("circuitRef")),
                "name": _clean_value(circuit.get("name")),
                "location": _clean_value(circuit.get("location")),
                "country": _clean_value(circuit.get("country")),
                "latitude": _as_float(circuit.get("lat")),
                "longitude": _as_float(circuit.get("lng")),
                "altitude": _as_int(circuit.get("alt")),
                "url": _clean_value(circuit.get("url")),
                "race_count": len(circuit_races),
                "first_used_year": min(years) if years else 0,
                "last_used_year": max(years) if years else 0,
                "active": latest_year in years,
            }
        )
    return docs


def _build_seasons(tables: dict[str, list[dict]]) -> list[dict]:
    seasons = tables[SEASONS_CSV]
    races = tables[RACES_CSV]
    sprint_results = tables[SPRINT_RESULTS_CSV]
    constructors = {row["constructorId"]: row for row in tables[CONSTRUCTORS_CSV]}
    drivers = {row["driverId"]: row for row in tables[DRIVERS_CSV]}
    constructor_standings = tables[CONSTRUCTOR_STANDINGS_CSV]
    driver_standings = tables.get(DRIVER_STANDINGS_CSV, [])
    final_race_ids = _final_race_ids_by_year(races)

    races_by_year: dict[int, list[dict]] = defaultdict(list)
    sprint_race_ids = {row["raceId"] for row in sprint_results}
    for race in races:
        races_by_year[_as_int(race["year"])].append(race)

    constructor_champions = _champion_lookup(
        final_race_ids=final_race_ids,
        standings=constructor_standings,
        entity_id_key="constructorId",
        refs=constructors,
        name_getter=lambda row: row.get("name", ""),
    )
    driver_champions = _champion_lookup(
        final_race_ids=final_race_ids,
        standings=driver_standings,
        entity_id_key="driverId",
        refs=drivers,
        name_getter=_full_name,
    )

    docs: list[dict] = []
    for season in seasons:
        year = _as_int(season["year"])
        season_races = sorted(races_by_year.get(year, []), key=lambda race: _as_int(race.get("round")))
        champion_driver_id, champion_driver_name = driver_champions.get(year, ("", ""))
        champion_constructor_id, champion_constructor_name = constructor_champions.get(year, ("", ""))
        docs.append(
            {
                "year": year,
                "url": _clean_value(season.get("url")),
                "race_count": len(season_races),
                "sprint_round_count": sum(1 for race in season_races if race["raceId"] in sprint_race_ids),
                "opening_race": season_races[0]["name"] if season_races else "",
                "final_race": season_races[-1]["name"] if season_races else "",
                "champion_driver_id": _as_int(champion_driver_id),
                "champion_driver_name": champion_driver_name,
                "champion_constructor_id": _as_int(champion_constructor_id),
                "champion_constructor_name": champion_constructor_name,
            }
        )
    return docs


def _build_races(tables: dict[str, list[dict]]) -> list[dict]:
    races = tables[RACES_CSV]
    circuits = {row["circuitId"]: row for row in tables[CIRCUITS_CSV]}
    sprint_race_ids = {row["raceId"] for row in tables[SPRINT_RESULTS_CSV]}
    winning_results = {row["raceId"]: row for row in tables[RESULTS_CSV] if row.get("positionOrder") == "1"}
    drivers = {row["driverId"]: row for row in tables[DRIVERS_CSV]}
    constructors = {row["constructorId"]: row for row in tables[CONSTRUCTORS_CSV]}

    docs: list[dict] = []
    for race in races:
        circuit = circuits.get(race["circuitId"], {})
        winning_result = winning_results.get(race["raceId"], {})
        driver_row = drivers.get(winning_result.get("driverId", ""), {})
        constructor_row = constructors.get(winning_result.get("constructorId", ""), {})
        docs.append(
            {
                "race_id": _as_int(race["raceId"]),
                "season_year": _as_int(race["year"]),
                "round": _as_int(race["round"]),
                "name": _clean_value(race.get("name")),
                "circuit_id": _as_int(race.get("circuitId")),
                "circuit_name": _clean_value(circuit.get("name")),
                "location": _clean_value(circuit.get("location")),
                "country": _clean_value(circuit.get("country")),
                "date": _clean_value(race.get("date")),
                "time": _clean_value(race.get("time")),
                "url": _clean_value(race.get("url")),
                "has_sprint": race["raceId"] in sprint_race_ids,
                "winner_driver_id": _as_int(winning_result.get("driverId")),
                "winner_driver_name": _full_name(driver_row),
                "winner_constructor_id": _as_int(winning_result.get("constructorId")),
                "winner_constructor_name": _clean_value(constructor_row.get("name")),
            }
        )
    return docs


def _build_statuses(tables: dict[str, list[dict]]) -> list[dict]:
    return [
        {"status_id": _as_int(row["statusId"]), "status": _clean_value(row.get("status"))}
        for row in tables[STATUS_CSV]
    ]


def _build_race_results(tables: dict[str, list[dict]]) -> list[dict]:
    races = {row["raceId"]: row for row in tables[RACES_CSV]}
    drivers = {row["driverId"]: row for row in tables[DRIVERS_CSV]}
    constructors = {row["constructorId"]: row for row in tables[CONSTRUCTORS_CSV]}
    circuits = {row["circuitId"]: row for row in tables[CIRCUITS_CSV]}
    statuses = {row["statusId"]: row["status"] for row in tables[STATUS_CSV]}

    docs: list[dict] = []
    for row in tables[RESULTS_CSV]:
        race = races.get(row["raceId"], {})
        driver = drivers.get(row["driverId"], {})
        constructor = constructors.get(row["constructorId"], {})
        circuit = circuits.get(race.get("circuitId", ""), {})
        status_text = _clean_value(statuses.get(row.get("statusId"), ""))
        position_text = _clean_value(row.get("positionText"))
        docs.append(
            {
                "result_id": _as_int(row["resultId"]),
                "race_id": _as_int(row["raceId"]),
                "season_year": _as_int(race.get("year")),
                "round": _as_int(race.get("round")),
                "race_name": _clean_value(race.get("name")),
                "circuit_id": _as_int(race.get("circuitId")),
                "circuit_name": _clean_value(circuit.get("name")),
                "driver_id": _as_int(row["driverId"]),
                "driver_name": _full_name(driver),
                "constructor_id": _as_int(row["constructorId"]),
                "constructor_name": _clean_value(constructor.get("name")),
                "number": _as_int(row.get("number")),
                "grid": _as_int(row.get("grid")),
                "position": _as_int(row.get("position")),
                "position_text": position_text,
                "position_order": _as_int(row.get("positionOrder")),
                "points": _as_float(row.get("points")),
                "laps": _as_int(row.get("laps")),
                "time": _clean_value(row.get("time")),
                "milliseconds": _as_int(row.get("milliseconds")),
                "fastest_lap": _as_int(row.get("fastestLap")),
                "fastest_lap_time": _clean_value(row.get("fastestLapTime")),
                "fastest_lap_speed": _as_float(row.get("fastestLapSpeed")),
                "status_id": _as_int(row.get("statusId")),
                "status": status_text,
                "classified_finish": _is_classified_finish(position_text, status_text),
            }
        )
    return docs


def _build_sprint_results(tables: dict[str, list[dict]]) -> list[dict]:
    races = {row["raceId"]: row for row in tables[RACES_CSV]}
    drivers = {row["driverId"]: row for row in tables[DRIVERS_CSV]}
    constructors = {row["constructorId"]: row for row in tables[CONSTRUCTORS_CSV]}
    statuses = {row["statusId"]: row["status"] for row in tables[STATUS_CSV]}

    docs: list[dict] = []
    for row in tables[SPRINT_RESULTS_CSV]:
        race = races.get(row["raceId"], {})
        driver = drivers.get(row["driverId"], {})
        constructor = constructors.get(row["constructorId"], {})
        status_text = _clean_value(statuses.get(row.get("statusId"), ""))
        position_text = _clean_value(row.get("positionText"))
        docs.append(
            {
                "result_id": _as_int(row["resultId"]),
                "race_id": _as_int(row["raceId"]),
                "season_year": _as_int(race.get("year")),
                "round": _as_int(race.get("round")),
                "race_name": _clean_value(race.get("name")),
                "driver_id": _as_int(row["driverId"]),
                "driver_name": _full_name(driver),
                "constructor_id": _as_int(row["constructorId"]),
                "constructor_name": _clean_value(constructor.get("name")),
                "grid": _as_int(row.get("grid")),
                "position": _as_int(row.get("position")),
                "position_text": position_text,
                "position_order": _as_int(row.get("positionOrder")),
                "points": _as_float(row.get("points")),
                "laps": _as_int(row.get("laps")),
                "time": _clean_value(row.get("time")),
                "milliseconds": _as_int(row.get("milliseconds")),
                "fastest_lap": _as_int(row.get("fastestLap")),
                "fastest_lap_time": _clean_value(row.get("fastestLapTime")),
                "status_id": _as_int(row.get("statusId")),
                "status": status_text,
                "classified_finish": _is_classified_finish(position_text, status_text),
            }
        )
    return docs


def _build_constructor_results(tables: dict[str, list[dict]]) -> list[dict]:
    races = {row["raceId"]: row for row in tables[RACES_CSV]}
    constructors = {row["constructorId"]: row for row in tables[CONSTRUCTORS_CSV]}
    docs: list[dict] = []
    for row in tables[CONSTRUCTOR_RESULTS_CSV]:
        race = races.get(row["raceId"], {})
        constructor = constructors.get(row["constructorId"], {})
        docs.append(
            {
                "constructor_result_id": _as_int(row["constructorResultsId"]),
                "race_id": _as_int(row["raceId"]),
                "season_year": _as_int(race.get("year")),
                "round": _as_int(race.get("round")),
                "race_name": _clean_value(race.get("name")),
                "constructor_id": _as_int(row["constructorId"]),
                "constructor_name": _clean_value(constructor.get("name")),
                "points": _as_float(row.get("points")),
                "status": _clean_value(row.get("status")),
            }
        )
    return docs


def _build_constructor_standings(tables: dict[str, list[dict]]) -> list[dict]:
    races = {row["raceId"]: row for row in tables[RACES_CSV]}
    constructors = {row["constructorId"]: row for row in tables[CONSTRUCTORS_CSV]}
    final_race_ids = set(_final_race_ids_by_year(tables[RACES_CSV]).values())
    docs: list[dict] = []
    for row in tables[CONSTRUCTOR_STANDINGS_CSV]:
        race = races.get(row["raceId"], {})
        constructor = constructors.get(row["constructorId"], {})
        docs.append(
            {
                "constructor_standing_id": _as_int(row["constructorStandingsId"]),
                "race_id": _as_int(row["raceId"]),
                "season_year": _as_int(race.get("year")),
                "round": _as_int(race.get("round")),
                "constructor_id": _as_int(row["constructorId"]),
                "constructor_name": _clean_value(constructor.get("name")),
                "points": _as_float(row.get("points")),
                "position": _as_int(row.get("position")),
                "position_text": _clean_value(row.get("positionText")),
                "wins": _as_int(row.get("wins")),
                "is_final_race": row.get("raceId") in final_race_ids,
            }
        )
    return docs


def _build_lap_time_summaries(tables: dict[str, list[dict]]) -> list[dict]:
    races = {row["raceId"]: row for row in tables[RACES_CSV]}
    drivers = {row["driverId"]: row for row in tables[DRIVERS_CSV]}
    constructor_lookup = {
        (row["raceId"], row["driverId"]): row["constructorId"] for row in tables[RESULTS_CSV]
    }
    constructors = {row["constructorId"]: row for row in tables[CONSTRUCTORS_CSV]}

    summaries: dict[tuple[str, str], dict] = {}
    for row in tables[LAP_TIMES_CSV]:
        key = (row["raceId"], row["driverId"])
        summary = summaries.setdefault(
            key,
            {
                "race_id": _as_int(row["raceId"]),
                "driver_id": _as_int(row["driverId"]),
                "lap_count": 0,
                "total_lap_time_ms": 0,
                "best_lap_time_ms": None,
                "best_lap_number": 0,
            },
        )
        milliseconds = _as_int(row.get("milliseconds"))
        lap_number = _as_int(row.get("lap"))
        summary["lap_count"] += 1
        summary["total_lap_time_ms"] += milliseconds
        if summary["best_lap_time_ms"] is None or milliseconds < summary["best_lap_time_ms"]:
            summary["best_lap_time_ms"] = milliseconds
            summary["best_lap_number"] = lap_number

    docs: list[dict] = []
    for (race_id, driver_id), summary in summaries.items():
        race = races.get(race_id, {})
        driver = drivers.get(driver_id, {})
        constructor_id = constructor_lookup.get((race_id, driver_id), "")
        constructor = constructors.get(constructor_id, {})
        lap_count = summary["lap_count"]
        total_ms = summary["total_lap_time_ms"]
        docs.append(
            {
                "race_id": summary["race_id"],
                "season_year": _as_int(race.get("year")),
                "round": _as_int(race.get("round")),
                "race_name": _clean_value(race.get("name")),
                "driver_id": summary["driver_id"],
                "driver_name": _full_name(driver),
                "constructor_id": _as_int(constructor_id),
                "constructor_name": _clean_value(constructor.get("name")),
                "lap_count": lap_count,
                "best_lap_time_ms": summary["best_lap_time_ms"] or 0,
                "best_lap_number": summary["best_lap_number"],
                "average_lap_time_ms": round(total_ms / lap_count, 2) if lap_count else 0,
                "total_lap_time_ms": total_ms,
            }
        )
    return docs


def _build_driver_season_stats(
    race_results: list[dict],
    sprint_results: list[dict],
    tables: dict[str, list[dict]],
) -> list[dict]:
    final_positions = _final_driver_positions(tables)

    stats: dict[tuple[int, int], dict] = {}
    for row in race_results:
        key = (row["season_year"], row["driver_id"])
        stat = stats.setdefault(key, _new_driver_season_stat(row))
        _apply_race_result_to_driver_stat(stat, row)

    for row in sprint_results:
        key = (row["season_year"], row["driver_id"])
        stat = stats.setdefault(key, _new_driver_season_stat(row))
        _apply_sprint_result_to_driver_stat(stat, row)

    docs: list[dict] = []
    for key, stat in sorted(stats.items()):
        position = final_positions.get(key, 0)
        stat["championship_position"] = position
        stat["champion"] = position == 1
        stat["total_points"] = round(stat["race_points"] + stat["sprint_points"], 2)
        docs.append(stat)
    return docs


def _build_constructor_season_stats(
    constructor_results: list[dict],
    constructor_standings: list[dict],
    race_results: list[dict],
) -> list[dict]:
    stats: dict[tuple[int, int], dict] = {}
    for row in constructor_results:
        key = (row["season_year"], row["constructor_id"])
        stat = stats.setdefault(
            key,
            {
                "season_year": row["season_year"],
                "constructor_id": row["constructor_id"],
                "constructor_name": row["constructor_name"],
                "race_entries": 0,
                "total_points": 0.0,
                "wins": 0,
                "podium_finishes": 0,
                "championship_position": 0,
                "champion": False,
            },
        )
        stat["race_entries"] += 1
        stat["total_points"] += row["points"]

    for row in race_results:
        key = (row["season_year"], row["constructor_id"])
        stat = stats.setdefault(
            key,
            {
                "season_year": row["season_year"],
                "constructor_id": row["constructor_id"],
                "constructor_name": row["constructor_name"],
                "race_entries": 0,
                "total_points": 0.0,
                "wins": 0,
                "podium_finishes": 0,
                "championship_position": 0,
                "champion": False,
            },
        )
        if row["position_order"] == 1:
            stat["wins"] += 1
        if row["position_order"] in (1, 2, 3):
            stat["podium_finishes"] += 1

    for row in constructor_standings:
        if not row["is_final_race"]:
            continue
        key = (row["season_year"], row["constructor_id"])
        stat = stats.setdefault(
            key,
            {
                "season_year": row["season_year"],
                "constructor_id": row["constructor_id"],
                "constructor_name": row["constructor_name"],
                "race_entries": 0,
                "total_points": 0.0,
                "wins": 0,
                "podium_finishes": 0,
                "championship_position": 0,
                "champion": False,
            },
        )
        stat["championship_position"] = row["position"]
        stat["champion"] = row["position"] == 1

    docs: list[dict] = []
    for _, stat in sorted(stats.items()):
        stat["total_points"] = round(stat["total_points"], 2)
        docs.append(stat)
    return docs


FACTS = [
    {
        "content": "Lewis Hamilton has won more races than any other driver in F1 history.",
        "category": "records",
    },
    {
        "content": "The Monaco Grand Prix is held on a street circuit in Monte Carlo.",
        "category": "history",
    },
]


async def _seed_collection_if_empty(db, collection_name: str, documents: list[dict], now: str) -> None:
    existing = await db[collection_name].count_documents({})
    if existing > 0:
        print(f"{collection_name} already has {existing} documents, skipping")
        return
    if not documents:
        print(f"No documents generated for {collection_name}, skipping")
        return
    for document in documents:
        document["created_at"] = now
    await db[collection_name].insert_many(documents)
    print(f"Seeded {len(documents)} documents into {collection_name}")


async def _create_indexes(db) -> None:
    await db[collections.users].create_index("username", unique=True)
    await db[collections.users].create_index("email", unique=True)
    await db[collections.drivers].create_index("name")
    await db[collections.teams].create_index("name")
    await db[collections.circuits].create_index("circuit_id", unique=True)
    await db[collections.seasons].create_index("year", unique=True)
    await db[collections.races].create_index("race_id", unique=True)
    await db[collections.races].create_index([("season_year", 1), ("round", 1)])
    await db[collections.statuses].create_index("status_id", unique=True)
    await db[collections.race_results].create_index("result_id", unique=True)
    await db[collections.race_results].create_index([("race_id", 1), ("driver_id", 1)])
    await db[collections.sprint_results].create_index("result_id", unique=True)
    await db[collections.sprint_results].create_index([("race_id", 1), ("driver_id", 1)])
    await db[collections.constructor_results].create_index("constructor_result_id", unique=True)
    await db[collections.constructor_results].create_index([("race_id", 1), ("constructor_id", 1)])
    await db[collections.constructor_standings].create_index("constructor_standing_id", unique=True)
    await db[collections.constructor_standings].create_index([("race_id", 1), ("constructor_id", 1)])
    await db[collections.lap_time_summaries].create_index(
        [("race_id", 1), ("driver_id", 1)], unique=True
    )
    await db[collections.driver_season_stats].create_index(
        [("season_year", 1), ("driver_id", 1)], unique=True
    )
    await db[collections.constructor_season_stats].create_index(
        [("season_year", 1), ("constructor_id", 1)], unique=True
    )
    await db[collections.predictions].create_index(
        [("user_id", 1), ("season", 1), ("category", 1)], unique=True
    )
    await db[collections.head_to_head_votes].create_index(
        [("driver1_id", 1), ("driver2_id", 1), ("user_id", 1)], unique=True
    )
    print("Database indexes created")


async def seed():
    dataset_path = _download_dataset()
    tables = _load_dataset_tables(dataset_path)

    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client.get_database(settings.DB_NAME)
    now = utc_now()

    race_results = _build_race_results(tables)
    sprint_results = _build_sprint_results(tables)
    constructor_results = _build_constructor_results(tables)
    constructor_standings = _build_constructor_standings(tables)

    await _seed_collection_if_empty(db, collections.teams, _build_teams(tables), now)
    await _seed_collection_if_empty(db, collections.drivers, _build_drivers(tables), now)
    await _seed_collection_if_empty(db, collections.circuits, _build_circuits(tables), now)
    await _seed_collection_if_empty(db, collections.seasons, _build_seasons(tables), now)
    await _seed_collection_if_empty(db, collections.races, _build_races(tables), now)
    await _seed_collection_if_empty(db, collections.statuses, _build_statuses(tables), now)
    await _seed_collection_if_empty(db, collections.race_results, race_results, now)
    await _seed_collection_if_empty(db, collections.sprint_results, sprint_results, now)
    await _seed_collection_if_empty(db, collections.constructor_results, constructor_results, now)
    await _seed_collection_if_empty(
        db, collections.constructor_standings, constructor_standings, now
    )
    await _seed_collection_if_empty(
        db, collections.lap_time_summaries, _build_lap_time_summaries(tables), now
    )
    await _seed_collection_if_empty(
        db,
        collections.driver_season_stats,
        _build_driver_season_stats(race_results, sprint_results, tables),
        now,
    )
    await _seed_collection_if_empty(
        db,
        collections.constructor_season_stats,
        _build_constructor_season_stats(constructor_results, constructor_standings, race_results),
        now,
    )

    facts = [
        {
            **fact,
            "submitted_by": "system",
            "approved": True,
            "likes": 0,
            "liked_by": [],
        }
        for fact in FACTS
    ]
    await _seed_collection_if_empty(db, collections.facts, facts, now)

    await _create_indexes(db)
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
