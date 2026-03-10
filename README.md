# 🏎️ F1 Facts API

A community-driven Formula 1 RESTful API built with **FastAPI** and **MongoDB**. Track drivers & teams, build personal favourite lists, predict championship winners, play trivia quizzes, compare drivers head-to-head, and share your hottest F1 takes!

## Features

| Feature | Description |
|---|---|
| **Auth** | Register, login, JWT-based authentication |
| **Drivers** | Full CRUD for the 2025 F1 driver grid (admin-managed, public read) |
| **Teams** | Full CRUD for the 2025 constructor lineup (admin-managed, public read) |
| **Favourites** | Create personal lists of favourite drivers and teams |
| **Predictions** | Predict the Driver & Constructor Champions with confidence ratings |
| **Leaderboard** | Global aggregated view of who the community thinks will win |
| **Trivia & Facts** | Random F1 facts, user-submitted facts with like/approve, plus a quiz mode |
| **Head-to-Head** | Compare any two drivers' stats side-by-side and vote on who's better |
| **Hot Takes** | Post controversial F1 opinions — others agree or disagree |

## Project Structure

```
cw1/
├── .env                      # Environment variables
├── requirements.txt          # Python dependencies
├── Makefile                  # Quick commands
├── README.md
└── src/
    ├── main.py               # FastAPI app entry point
    ├── config/
    │   └── settings.py       # Pydantic settings from .env
    ├── core/
    │   └── security.py       # JWT + password hashing
    ├── models/               # Pydantic models (schemas)
    │   ├── common.py         # Shared base classes
    │   ├── user.py
    │   ├── driver.py
    │   ├── team.py
    │   ├── favourite.py
    │   ├── prediction.py
    │   ├── fact.py
    │   ├── head_to_head.py
    │   └── hot_take.py
    ├── db/                   # MongoDB query functions
    │   ├── collections.py    # Collection name constants
    │   ├── users.py
    │   ├── drivers.py
    │   ├── teams.py
    │   ├── favourites.py
    │   ├── predictions.py
    │   ├── facts.py
    │   ├── head_to_head.py
    │   └── hot_takes.py
    ├── routers/              # API route handlers
    │   ├── auth.py
    │   ├── drivers.py
    │   ├── teams.py
    │   ├── favourites.py
    │   ├── predictions.py
    │   ├── trivia.py
    │   ├── head_to_head.py
    │   └── hot_takes.py
    └── data/
        └── seed.py           # Database seeder (drivers, teams, facts, admin user)
```

## Getting Started

### Prerequisites

- **Python 3.12** (3.14 is not yet supported by pydantic-core)
- **MongoDB** installed via Homebrew (`brew install mongodb-community@7.0`)

### 1. Create a virtual environment & install dependencies

```bash
python3 -m venv venv
make install
```

### 2. Configure environment

Copy the example and edit as needed:

```bash
cp .env.example .env
```

Key variables:
| Variable | Default | Description |
|---|---|---|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `DB_NAME` | `f1_facts_db` | Database name |
| `JWT_SECRET` | random | Change this in production! |
| `TOKEN_EXPIRY_MINUTES` | `120` | JWT expiry time |

### 3. Seed the database

Downloads the [Kaggle F1 Race Data](https://www.kaggle.com/datasets/jtrotman/formula-1-race-data) dataset and populates the database with drivers, teams (including computed career stats and championship counts), 30 hand-curated trivia facts, and an admin user:

```bash
make seed

# Or to drop all collections and re-seed from scratch:
make reseed
```

> Default admin credentials: `admin` / `admin123`

### 4. Start MongoDB & run the server

```bash
# Start MongoDB
make db-start

# Development (hot reload)
make dev

# Production
make run

# Stop the server
make stop

# Stop MongoDB when done
make db-stop
```

### 5. Run the tests

```bash
make test           # Run all tests (verbose)
make test-fast      # Stop on first failure
make test-cov       # With coverage report
```

### 6. Explore the API

Open **http://localhost:8000/docs** for the interactive Swagger UI.

## 🛠️ Makefile Reference

| Command | Description |
|---|---|
| `make install` | Install Python dependencies into `venv` |
| `make db-start` | Start MongoDB via `brew services` |
| `make db-stop` | Stop MongoDB via `brew services` |
| `make dev` | Run server with hot-reload |
| `make run` | Run server (production mode) |
| `make stop` | Kill the server process on port 8000 |
| `make seed` | Seed the database from Kaggle dataset |
| `make reseed` | Drop all collections and re-seed from scratch |
| `make test` | Run all tests (verbose) |
| `make test-fast` | Run tests, stop on first failure |
| `make test-cov` | Run tests with coverage report |
| `make lint` | Quick syntax check |
| `make clean` | Remove `__pycache__` and `.pyc` files |

## API Endpoints

### Auth
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | ❌ | Create account |
| POST | `/auth/login` | ❌ | Login (form-data), get JWT |
| GET | `/auth/me` | ✅ | Get profile |
| PATCH | `/auth/me` | ✅ | Update profile |
| DELETE | `/auth/me` | ✅ | Delete account |

### Drivers
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/drivers` | ❌ | List all drivers |
| GET | `/drivers/search?name=&team=` | ❌ | Search drivers |
| GET | `/drivers/{id}` | ❌ | Get driver by ID |
| POST | `/drivers` | 🔑 Admin | Create driver |
| PATCH | `/drivers/{id}` | 🔑 Admin | Update driver |
| DELETE | `/drivers/{id}` | 🔑 Admin | Delete driver |

### Teams
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/teams` | ❌ | List all teams |
| GET | `/teams/search?name=` | ❌ | Search teams |
| GET | `/teams/{id}` | ❌ | Get team by ID |
| POST | `/teams` | 🔑 Admin | Create team |
| PATCH | `/teams/{id}` | 🔑 Admin | Update team |
| DELETE | `/teams/{id}` | 🔑 Admin | Delete team |

### Favourites
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/favourites` | ✅ | List my favourite lists |
| GET | `/favourites/{id}` | ✅ | Get a specific list |
| POST | `/favourites` | ✅ | Create a new list |
| PATCH | `/favourites/{id}` | ✅ | Rename a list |
| DELETE | `/favourites/{id}` | ✅ | Delete a list |
| POST | `/favourites/{id}/items` | ✅ | Add item to list |
| DELETE | `/favourites/{id}/items/{item_id}` | ✅ | Remove item from list |

### Predictions & Leaderboard
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/predictions` | ✅ | List my predictions |
| GET | `/predictions/view/{id}` | ✅ | Get a prediction |
| POST | `/predictions` | ✅ | Submit prediction |
| PATCH | `/predictions/{id}` | ✅ | Update prediction |
| DELETE | `/predictions/{id}` | ✅ | Delete prediction |
| GET | `/predictions/leaderboard/drivers?season=2025` | ❌ | Driver championship votes |
| GET | `/predictions/leaderboard/constructors?season=2025` | ❌ | Constructor championship votes |

### Trivia & Facts
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/trivia/random` | ❌ | Random F1 fact |
| GET | `/trivia` | ❌ | All approved facts |
| POST | `/trivia` | ✅ | Submit a fact |
| POST | `/trivia/{id}/like` | ✅ | Like / unlike |
| PATCH | `/trivia/{id}/approve` | 🔑 Admin | Approve fact |
| DELETE | `/trivia/{id}` | 🔑 Admin | Delete fact |
| GET | `/trivia/quiz` | ❌ | Random quiz question |
| POST | `/trivia/quiz/answer` | ❌ | Check quiz answer |

### Head-to-Head
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/head-to-head/compare/{d1}/{d2}` | ❌ | Compare two drivers + votes |
| POST | `/head-to-head/vote` | ✅ | Vote on who's better |

### Hot Takes
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/hot-takes?sort_by=recent\|spicy\|popular` | ❌ | List hot takes |
| GET | `/hot-takes/{id}` | ❌ | Get a hot take |
| POST | `/hot-takes` | ✅ | Post a hot take |
| POST | `/hot-takes/{id}/react` | ✅ | Agree / disagree |
| DELETE | `/hot-takes/{id}` | ✅ | Delete (own or admin) |

## Authentication

The API uses **JWT Bearer tokens**. After registering or logging in, include the token in requests:

```
Authorization: Bearer <your-token>
```

In the Swagger UI, click the **Authorize** button and paste your token.

## Example Usage

### Register & Login
```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"zeyad","email":"zeyad@example.com","display_name":"Zeyad","password":"mypass123"}'

# Login (uses OAuth2 form-data)
curl -X POST http://localhost:8000/auth/login \
  -d 'username=zeyad&password=mypass123'
```

### Create a favourite list & add drivers
```bash
TOKEN="your-jwt-token"

# Create list
curl -X POST http://localhost:8000/favourites \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"My Dream Team","list_type":"drivers"}'

# Add a driver to the list
curl -X POST http://localhost:8000/favourites/{list_id}/items \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item_id":"driver_id_here","name":"Max Verstappen"}'
```

### Make a championship prediction
```bash
curl -X POST http://localhost:8000/predictions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"season":2025,"category":"driver_championship","predicted_id":"driver_id","predicted_name":"Max Verstappen","confidence":9,"reasoning":"Dominant car and driver combo"}'
```

### Play trivia
```bash
# Get a quiz question
curl http://localhost:8000/trivia/quiz

# Answer it
curl -X POST http://localhost:8000/trivia/quiz/answer \
  -H "Content-Type: application/json" \
  -d '{"question_id":"q01","answer":"Monza"}'
```

## Tech Stack

- **FastAPI** – Modern async Python web framework
- **MongoDB** + **Motor** – Async document database
- **Pydantic v2** – Data validation and serialization
- **python-jose** – JWT token encoding/decoding
- **bcrypt** – Secure password hashing (direct usage, no passlib wrapper)
- **kagglehub** – Downloads the [F1 Race Data](https://www.kaggle.com/datasets/jtrotman/formula-1-race-data) dataset for seeding

## License

This project was built for COMP3011 Web Services Development coursework.
