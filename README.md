# Space Facts API

A FastAPI project for managing fun and educational space facts, using SQLite for storage.

## Features
- CRUD endpoints for space facts
- Categories: planet, star, mission, etc.
- Seed script for initial facts

## Endpoints
- `POST /facts` — Create a new fact
- `GET /facts` — Retrieve all facts
- `GET /facts/{id}` — Retrieve a specific fact
- `PUT /facts/{id}` — Update a fact
- `DELETE /facts/{id}` — Delete a fact

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Seed the database:
   ```bash
   python seed.py
   ```
3. Run the API:
   ```bash
   uvicorn main:app --reload
   ```

## Example Fact
```
{
  "title": "The Sun is a star",
  "description": "The Sun is the closest star to Earth.",
  "source": "NASA",
  "category": "star"
}
```
