from app.database.database import SessionLocal, Base, engine
from app.models.models import Fact

Base.metadata.create_all(bind=engine)

def seed_facts():
    db = SessionLocal()
    facts = [
        Fact(title="The Sun is a star", description="The Sun is the closest star to Earth.", source="NASA", category="star"),
        Fact(title="Jupiter is the largest planet", description="Jupiter is the largest planet in our Solar System.", source="NASA", category="planet"),
        Fact(title="Apollo 11 landed on the Moon", description="Apollo 11 was the first mission to land humans on the Moon.", source="NASA", category="mission"),
        Fact(title="Mars has two moons", description="Mars has two small moons: Phobos and Deimos.", source="NASA", category="planet")
    ]
    db.add_all(facts)
    db.commit()
    db.close()

if __name__ == "__main__":
    seed_facts()
