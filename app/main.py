from fastapi import FastAPI, HTTPException
from app.models.models import Fact, FactCreate, FactUpdate
from app.database.database import SessionLocal, engine, Base
from sqlalchemy.orm import Session

app = FastAPI()

Base.metadata.create_all(bind=engine)

@app.post("/facts", response_model=Fact, status_code=201)
def create_fact(fact: FactCreate):
    db: Session = SessionLocal()
    db_fact = Fact(**fact.dict())
    db.add(db_fact)
    db.commit()
    db.refresh(db_fact)
    db.close()
    return db_fact

@app.get("/facts", response_model=list[Fact])
def get_facts():
    db: Session = SessionLocal()
    facts = db.query(Fact).all()
    db.close()
    return facts

@app.get("/facts/{fact_id}", response_model=Fact)
def get_fact(fact_id: int):
    db: Session = SessionLocal()
    fact = db.query(Fact).filter(Fact.id == fact_id).first()
    db.close()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    return fact

@app.put("/facts/{fact_id}", response_model=Fact)
def update_fact(fact_id: int, fact_update: FactUpdate):
    db: Session = SessionLocal()
    fact = db.query(Fact).filter(Fact.id == fact_id).first()
    if not fact:
        db.close()
        raise HTTPException(status_code=404, detail="Fact not found")
    for key, value in fact_update.dict(exclude_unset=True).items():
        setattr(fact, key, value)
    db.commit()
    db.refresh(fact)
    db.close()
    return fact

@app.delete("/facts/{fact_id}", status_code=204)
def delete_fact(fact_id: int):
    db: Session = SessionLocal()
    fact = db.query(Fact).filter(Fact.id == fact_id).first()
    if not fact:
        db.close()
        raise HTTPException(status_code=404, detail="Fact not found")
    db.delete(fact)
    db.commit()
    db.close()
    return None
