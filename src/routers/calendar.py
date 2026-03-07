"""Calendar router – 2025 F1 race calendar (read-only reference data)."""

from fastapi import APIRouter, Query

router = APIRouter()

CALENDAR_2025 = [
    {"round": 1, "name": "Australian Grand Prix", "circuit": "Albert Park", "location": "Melbourne, Australia", "date": "2025-03-16"},
    {"round": 2, "name": "Chinese Grand Prix", "circuit": "Shanghai International Circuit", "location": "Shanghai, China", "date": "2025-03-23"},
    {"round": 3, "name": "Japanese Grand Prix", "circuit": "Suzuka", "location": "Suzuka, Japan", "date": "2025-04-06"},
    {"round": 4, "name": "Bahrain Grand Prix", "circuit": "Bahrain International Circuit", "location": "Sakhir, Bahrain", "date": "2025-04-13"},
    {"round": 5, "name": "Saudi Arabian Grand Prix", "circuit": "Jeddah Corniche Circuit", "location": "Jeddah, Saudi Arabia", "date": "2025-04-20"},
    {"round": 6, "name": "Miami Grand Prix", "circuit": "Miami International Autodrome", "location": "Miami, USA", "date": "2025-05-04"},
    {"round": 7, "name": "Emilia Romagna Grand Prix", "circuit": "Imola", "location": "Imola, Italy", "date": "2025-05-18"},
    {"round": 8, "name": "Monaco Grand Prix", "circuit": "Circuit de Monaco", "location": "Monte Carlo, Monaco", "date": "2025-05-25"},
    {"round": 9, "name": "Spanish Grand Prix", "circuit": "Circuit de Barcelona-Catalunya", "location": "Barcelona, Spain", "date": "2025-06-01"},
    {"round": 10, "name": "Canadian Grand Prix", "circuit": "Circuit Gilles Villeneuve", "location": "Montreal, Canada", "date": "2025-06-15"},
    {"round": 11, "name": "Austrian Grand Prix", "circuit": "Red Bull Ring", "location": "Spielberg, Austria", "date": "2025-06-29"},
    {"round": 12, "name": "British Grand Prix", "circuit": "Silverstone", "location": "Silverstone, UK", "date": "2025-07-06"},
    {"round": 13, "name": "Belgian Grand Prix", "circuit": "Spa-Francorchamps", "location": "Stavelot, Belgium", "date": "2025-07-27"},
    {"round": 14, "name": "Hungarian Grand Prix", "circuit": "Hungaroring", "location": "Budapest, Hungary", "date": "2025-08-03"},
    {"round": 15, "name": "Dutch Grand Prix", "circuit": "Zandvoort", "location": "Zandvoort, Netherlands", "date": "2025-08-31"},
    {"round": 16, "name": "Italian Grand Prix", "circuit": "Monza", "location": "Monza, Italy", "date": "2025-09-07"},
    {"round": 17, "name": "Azerbaijan Grand Prix", "circuit": "Baku City Circuit", "location": "Baku, Azerbaijan", "date": "2025-09-21"},
    {"round": 18, "name": "Singapore Grand Prix", "circuit": "Marina Bay Street Circuit", "location": "Singapore", "date": "2025-10-05"},
    {"round": 19, "name": "United States Grand Prix", "circuit": "Circuit of the Americas", "location": "Austin, USA", "date": "2025-10-19"},
    {"round": 20, "name": "Mexico City Grand Prix", "circuit": "Autódromo Hermanos Rodríguez", "location": "Mexico City, Mexico", "date": "2025-10-26"},
    {"round": 21, "name": "São Paulo Grand Prix", "circuit": "Interlagos", "location": "São Paulo, Brazil", "date": "2025-11-09"},
    {"round": 22, "name": "Las Vegas Grand Prix", "circuit": "Las Vegas Street Circuit", "location": "Las Vegas, USA", "date": "2025-11-22"},
    {"round": 23, "name": "Qatar Grand Prix", "circuit": "Lusail International Circuit", "location": "Lusail, Qatar", "date": "2025-11-30"},
    {"round": 24, "name": "Abu Dhabi Grand Prix", "circuit": "Yas Marina Circuit", "location": "Abu Dhabi, UAE", "date": "2025-12-07"},
]


@router.get("")
async def get_calendar(
    upcoming_only: bool = Query(False, description="Show only races that haven't happened yet"),
):
    """Get the 2025 F1 race calendar."""
    if upcoming_only:
        from datetime import date
        today = date.today().isoformat()
        return [r for r in CALENDAR_2025 if r["date"] >= today]
    return CALENDAR_2025


@router.get("/{round_number}")
async def get_race(round_number: int):
    """Get details for a specific round."""
    race = next((r for r in CALENDAR_2025 if r["round"] == round_number), None)
    if not race:
        from src.core.exceptions import RaceRoundNotFoundError
        raise RaceRoundNotFoundError(round_number)
    return race
