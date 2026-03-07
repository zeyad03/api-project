"""Seed script – populates MongoDB with F1 drivers, teams, and trivia facts.

Run with:  python -m src.data.seed
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from src.config.settings import settings
from src.db.collections import collections
from src.core.security import hash_password
from src.models.common import utc_now


# ═══════════════════════════════════════════════════════════════════════════════
#  2025 F1 TEAMS
# ═══════════════════════════════════════════════════════════════════════════════
TEAMS = [
    {
        "name": "Red Bull Racing",
        "full_name": "Oracle Red Bull Racing",
        "base": "Milton Keynes, UK",
        "team_principal": "Christian Horner",
        "championships": 6,
        "first_entry": 2005,
        "car": "RB21",
        "engine": "Honda RBPT",
        "active": True,
    },
    {
        "name": "Mercedes",
        "full_name": "Mercedes-AMG Petronas F1 Team",
        "base": "Brackley, UK",
        "team_principal": "Toto Wolff",
        "championships": 8,
        "first_entry": 2010,
        "car": "W16",
        "engine": "Mercedes",
        "active": True,
    },
    {
        "name": "Ferrari",
        "full_name": "Scuderia Ferrari HP",
        "base": "Maranello, Italy",
        "team_principal": "Frédéric Vasseur",
        "championships": 16,
        "first_entry": 1950,
        "car": "SF-25",
        "engine": "Ferrari",
        "active": True,
    },
    {
        "name": "McLaren",
        "full_name": "McLaren Formula 1 Team",
        "base": "Woking, UK",
        "team_principal": "Andrea Stella",
        "championships": 8,
        "first_entry": 1966,
        "car": "MCL39",
        "engine": "Mercedes",
        "active": True,
    },
    {
        "name": "Aston Martin",
        "full_name": "Aston Martin Aramco F1 Team",
        "base": "Silverstone, UK",
        "team_principal": "Andy Cowell",
        "championships": 0,
        "first_entry": 2021,
        "car": "AMR25",
        "engine": "Honda RBPT",
        "active": True,
    },
    {
        "name": "Alpine",
        "full_name": "BWT Alpine F1 Team",
        "base": "Enstone, UK",
        "team_principal": "Oliver Oakes",
        "championships": 2,
        "first_entry": 2021,
        "car": "A525",
        "engine": "Mercedes",
        "active": True,
    },
    {
        "name": "Williams",
        "full_name": "Williams Racing",
        "base": "Grove, UK",
        "team_principal": "James Vowles",
        "championships": 9,
        "first_entry": 1978,
        "car": "FW47",
        "engine": "Mercedes",
        "active": True,
    },
    {
        "name": "RB (Visa Cash App)",
        "full_name": "Visa Cash App Racing Bulls F1 Team",
        "base": "Faenza, Italy",
        "team_principal": "Laurent Mekies",
        "championships": 0,
        "first_entry": 2006,
        "car": "VCARB 02",
        "engine": "Honda RBPT",
        "active": True,
    },
    {
        "name": "Kick Sauber",
        "full_name": "Stake F1 Team Kick Sauber",
        "base": "Hinwil, Switzerland",
        "team_principal": "Mattia Binotto",
        "championships": 0,
        "first_entry": 1993,
        "car": "C45",
        "engine": "Ferrari",
        "active": True,
    },
    {
        "name": "Haas",
        "full_name": "MoneyGram Haas F1 Team",
        "base": "Kannapolis, USA",
        "team_principal": "Ayao Komatsu",
        "championships": 0,
        "first_entry": 2016,
        "car": "VF-25",
        "engine": "Ferrari",
        "active": True,
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
#  2025 F1 DRIVERS
# ═══════════════════════════════════════════════════════════════════════════════
DRIVERS = [
    {"name": "Max Verstappen", "number": 1, "team": "Red Bull Racing", "nationality": "Dutch", "date_of_birth": "1997-09-30", "championships": 4, "wins": 63, "podiums": 111, "poles": 40, "bio": "Four-time World Champion and one of the most dominant drivers in F1 history.", "active": True},
    {"name": "Liam Lawson", "number": 30, "team": "Red Bull Racing", "nationality": "New Zealander", "date_of_birth": "2002-02-11", "championships": 0, "wins": 0, "podiums": 0, "poles": 0, "bio": "Promoted to Red Bull Racing for 2025 after impressive stints at VCARB.", "active": True},
    {"name": "Lewis Hamilton", "number": 44, "team": "Ferrari", "nationality": "British", "date_of_birth": "1985-01-07", "championships": 7, "wins": 105, "podiums": 201, "poles": 104, "bio": "Seven-time World Champion who joined Ferrari for 2025 in a blockbuster move.", "active": True},
    {"name": "Charles Leclerc", "number": 16, "team": "Ferrari", "nationality": "Monégasque", "date_of_birth": "1997-10-16", "championships": 0, "wins": 8, "podiums": 40, "poles": 26, "bio": "Ferrari's star driver known for his raw speed and passionate driving style.", "active": True},
    {"name": "Lando Norris", "number": 4, "team": "McLaren", "nationality": "British", "date_of_birth": "1999-11-13", "championships": 0, "wins": 4, "podiums": 28, "poles": 8, "bio": "McLaren's team leader, blending speed with a charismatic personality.", "active": True},
    {"name": "Oscar Piastri", "number": 81, "team": "McLaren", "nationality": "Australian", "date_of_birth": "2001-04-06", "championships": 0, "wins": 2, "podiums": 14, "poles": 2, "bio": "Former F2 and F3 champion making waves in only his third F1 season.", "active": True},
    {"name": "George Russell", "number": 63, "team": "Mercedes", "nationality": "British", "date_of_birth": "1998-02-15", "championships": 0, "wins": 3, "podiums": 18, "poles": 5, "bio": "Mercedes team leader known for his consistency and racecraft.", "active": True},
    {"name": "Andrea Kimi Antonelli", "number": 12, "team": "Mercedes", "nationality": "Italian", "date_of_birth": "2006-08-25", "championships": 0, "wins": 0, "podiums": 0, "poles": 0, "bio": "Teenage prodigy fast-tracked to Mercedes, tipped as a future champion.", "active": True},
    {"name": "Fernando Alonso", "number": 14, "team": "Aston Martin", "nationality": "Spanish", "date_of_birth": "1981-07-29", "championships": 2, "wins": 32, "podiums": 106, "poles": 22, "bio": "Two-time World Champion and the elder statesman of the grid at 43.", "active": True},
    {"name": "Lance Stroll", "number": 18, "team": "Aston Martin", "nationality": "Canadian", "date_of_birth": "1998-10-29", "championships": 0, "wins": 0, "podiums": 3, "poles": 1, "bio": "Son of team owner Lawrence Stroll, a podium finisher in multiple seasons.", "active": True},
    {"name": "Pierre Gasly", "number": 10, "team": "Alpine", "nationality": "French", "date_of_birth": "1996-02-07", "championships": 0, "wins": 1, "podiums": 5, "poles": 0, "bio": "Former race winner leading Alpine's charge up the grid.", "active": True},
    {"name": "Jack Doohan", "number": 7, "team": "Alpine", "nationality": "Australian", "date_of_birth": "2003-01-20", "championships": 0, "wins": 0, "podiums": 0, "poles": 0, "bio": "Son of motorcycle legend Mick Doohan, making his full-time F1 debut.", "active": True},
    {"name": "Alexander Albon", "number": 23, "team": "Williams", "nationality": "Thai-British", "date_of_birth": "1996-03-23", "championships": 0, "wins": 0, "podiums": 2, "poles": 0, "bio": "Fan favourite known for his wheel-to-wheel racing and resilience.", "active": True},
    {"name": "Carlos Sainz", "number": 55, "team": "Williams", "nationality": "Spanish", "date_of_birth": "1994-09-01", "championships": 0, "wins": 4, "podiums": 25, "poles": 6, "bio": "Multiple race winner who joined Williams after his Ferrari departure.", "active": True},
    {"name": "Yuki Tsunoda", "number": 22, "team": "RB (Visa Cash App)", "nationality": "Japanese", "date_of_birth": "2000-05-11", "championships": 0, "wins": 0, "podiums": 0, "poles": 0, "bio": "Fiery Japanese driver with raw speed and entertaining radio messages.", "active": True},
    {"name": "Isack Hadjar", "number": 6, "team": "RB (Visa Cash App)", "nationality": "French-Algerian", "date_of_birth": "2004-09-28", "championships": 0, "wins": 0, "podiums": 0, "poles": 0, "bio": "2024 F2 runner-up earning his F1 seat through the Red Bull junior programme.", "active": True},
    {"name": "Nico Hülkenberg", "number": 27, "team": "Kick Sauber", "nationality": "German", "date_of_birth": "1987-08-19", "championships": 0, "wins": 0, "podiums": 0, "poles": 1, "bio": "Experienced campaigner joining the Audi project via Kick Sauber.", "active": True},
    {"name": "Gabriel Bortoleto", "number": 5, "team": "Kick Sauber", "nationality": "Brazilian", "date_of_birth": "2004-10-14", "championships": 0, "wins": 0, "podiums": 0, "poles": 0, "bio": "2024 F2 champion and exciting young talent from Brazil.", "active": True},
    {"name": "Esteban Ocon", "number": 31, "team": "Haas", "nationality": "French", "date_of_birth": "1996-09-17", "championships": 0, "wins": 1, "podiums": 3, "poles": 0, "bio": "Race winner who brings experience and determination to Haas.", "active": True},
    {"name": "Oliver Bearman", "number": 87, "team": "Haas", "nationality": "British", "date_of_birth": "2005-05-08", "championships": 0, "wins": 0, "podiums": 0, "poles": 0, "bio": "Became the youngest British F1 driver when he debuted as a Ferrari sub in 2024.", "active": True},
]

# ═══════════════════════════════════════════════════════════════════════════════
#  F1 TRIVIA FACTS
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
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client.get_database(settings.DB_NAME)

    now = utc_now()

    # ── Teams ────────────────────────────────────────────────────────────────
    existing_teams = await db[collections.teams].count_documents({})
    if existing_teams == 0:
        for t in TEAMS:
            t["created_at"] = now
        await db[collections.teams].insert_many(TEAMS)
        print(f"✅  Seeded {len(TEAMS)} teams")
    else:
        print(f"ℹ️  Teams collection already has {existing_teams} documents, skipping")

    # ── Drivers ──────────────────────────────────────────────────────────────
    existing_drivers = await db[collections.drivers].count_documents({})
    if existing_drivers == 0:
        for d in DRIVERS:
            d["created_at"] = now
        await db[collections.drivers].insert_many(DRIVERS)
        print(f"✅  Seeded {len(DRIVERS)} drivers")
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

    # ── Admin user ───────────────────────────────────────────────────────────
    admin = await db[collections.users].find_one({"username": "admin"})
    if not admin:
        await db[collections.users].insert_one({
            "username": "admin",
            "email": "admin@f1facts.api",
            "display_name": "Admin",
            "password_hash": hash_password("admin123"),
            "is_admin": True,
            "created_at": now,
        })
        print("✅  Created admin user (username: admin, password: admin123)")
    else:
        print("ℹ️  Admin user already exists, skipping")

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
