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
├── pyproject.toml            # Pytest / coverage configuration
├── requirements.txt          # Python dependencies
├── Makefile                  # Quick commands
├── README.md
├── scripts/
│   └── mongodb/
│       └── onboard.py        # Admin user onboarding helper
├── tests/                    # API and DB-layer test suite
│   ├── conftest.py
│   └── test_*.py
└── src/
    ├── main.py               # FastAPI app entry point
    ├── config/
    │   └── settings.py       # Pydantic settings from .env
    ├── core/
    │   ├── exceptions.py     # Custom API exception hierarchy
    │   ├── rate_limit.py     # SlowAPI limiter configuration
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

Create a `.env` file in the project root and add the settings you want to override:

```bash
cat > .env <<'EOF'
MONGO_URI=mongodb://localhost:27017
DB_NAME=f1_facts_db
JWT_SECRET=replace-me-with-a-long-random-secret
TOKEN_EXPIRY_MINUTES=120
ORIGINS=http://localhost:3000,http://localhost:5173
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_AUTH=5/minute
EOF
```

Key variables:
| Variable | Default | Description |
|---|---|---|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `DB_NAME` | `f1_facts_db` | Database name |
| `JWT_SECRET` | random | Change this in production! |
| `TOKEN_EXPIRY_MINUTES` | `120` | JWT expiry time |
| `ORIGINS` | `http://localhost:3000,http://localhost:5173` | Allowed CORS origins |
| `RATE_LIMIT_DEFAULT` | `100/minute` | Default per-IP API rate limit |
| `RATE_LIMIT_AUTH` | `5/minute` | Stricter per-IP limit for auth endpoints |

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

## Security Notes

- The API uses JWT bearer authentication for protected endpoints.
- Requests are rate-limited per IP using `slowapi`.
- The default API-wide limit is `100/minute`.
- The `/auth/register` and `/auth/login` endpoints use a stricter `5/minute` limit.
- When a limit is exceeded, the API returns HTTP `429 Too Many Requests`.

## Makefile Reference

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

### Health
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | No | Health check and docs link |

### Auth
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Create account |
| POST | `/auth/login` | No | Login (form-data), get JWT |
| GET | `/auth/me` | Yes | Get profile |
| PATCH | `/auth/me` | Yes | Update profile |
| DELETE | `/auth/me` | Yes | Delete account |

### Drivers
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/drivers` | No | List all drivers |
| GET | `/drivers/search?name=&team=` | No | Search drivers |
| GET | `/drivers/{id}` | No | Get driver by ID |
| POST | `/drivers` | Admin | Create driver |
| PATCH | `/drivers/{id}` | Admin | Update driver |
| DELETE | `/drivers/{id}` | Admin | Delete driver |

### Teams
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/teams` | No | List all teams |
| GET | `/teams/search?name=` | No | Search teams |
| GET | `/teams/{id}` | No | Get team by ID |
| POST | `/teams` | Admin | Create team |
| PATCH | `/teams/{id}` | Admin | Update team |
| DELETE | `/teams/{id}` | Admin | Delete team |

### Favourites
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/favourites` | Yes | List my favourite lists |
| GET | `/favourites/{id}` | Yes | Get a specific list |
| POST | `/favourites` | Yes | Create a new list |
| PATCH | `/favourites/{id}` | Yes | Rename a list |
| DELETE | `/favourites/{id}` | Yes | Delete a list |
| POST | `/favourites/{id}/items` | Yes | Add item to list |
| DELETE | `/favourites/{id}/items/{item_id}` | Yes | Remove item from list |

### Predictions & Leaderboard
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/predictions` | Yes | List my predictions |
| GET | `/predictions/view/{id}` | Yes | Get a prediction |
| POST | `/predictions` | Yes | Submit prediction |
| PATCH | `/predictions/{id}` | Yes | Update prediction |
| DELETE | `/predictions/{id}` | Yes | Delete prediction |
| GET | `/predictions/leaderboard/drivers?season=2025` | No | Driver championship votes |
| GET | `/predictions/leaderboard/constructors?season=2025` | No | Constructor championship votes |

### Trivia & Facts
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/trivia/random` | No | Random F1 fact |
| GET | `/trivia` | No | All approved facts |
| POST | `/trivia` | Yes | Submit a fact |
| POST | `/trivia/{id}/like` | Yes | Like / unlike |
| PATCH | `/trivia/{id}/approve` | Admin | Approve fact |
| DELETE | `/trivia/{id}` | Admin | Delete fact |
| GET | `/trivia/quiz` | No | Random quiz question |
| POST | `/trivia/quiz/answer` | No | Check quiz answer |

### Head-to-Head
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/head-to-head/compare/{driver1_name}/{driver2_name}` | No | Compare two drivers by name + votes |
| POST | `/head-to-head/vote` | Yes | Vote on who's better |

### Hot Takes
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/hot-takes?sort_by=recent\|spicy\|popular` | No | List hot takes |
| GET | `/hot-takes/{id}` | No | Get a hot take |
| POST | `/hot-takes` | Yes | Post a hot take |
| POST | `/hot-takes/{id}/react` | Yes | Agree / disagree |
| DELETE | `/hot-takes/{id}` | Yes | Delete (own or admin) |

## Authentication

The API uses **JWT Bearer tokens**. After registering or logging in, include the token in requests:

```
Authorization: Bearer <your-token>
```

In the Swagger UI, click the **Authorize** button and paste your token.

For names in path parameters, URL-encode spaces. Example:

```
/head-to-head/compare/Lewis%20Hamilton/Max%20Verstappen
```

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

### Compare two drivers by name
```bash
curl http://localhost:8000/head-to-head/compare/Lewis%20Hamilton/Max%20Verstappen
```

## Tech Stack

- **FastAPI** – Modern async Python web framework
- **MongoDB** + **Motor** – Async document database
- **Pydantic v2** – Data validation and serialization
- **python-jose** – JWT token encoding/decoding
- **bcrypt** – Secure password hashing (direct usage, no passlib wrapper)
- **slowapi** – Per-IP request rate limiting and `429` handling
- **kagglehub** – Downloads the [F1 Race Data](https://www.kaggle.com/datasets/jtrotman/formula-1-race-data) dataset for seeding

## License

This project was built for COMP3011 Web Services Development coursework.
