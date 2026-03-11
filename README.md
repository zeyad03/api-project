# 🏎️ F1 Facts API

A community-driven Formula 1 RESTful API built with **FastAPI** and **MongoDB**. Track drivers & teams, build personal favourite lists, predict championship winners, play trivia quizzes, compare drivers head-to-head, and share your hottest F1 takes!

## Features

| Feature | Description |
|---|---|
| **Auth** | Register, login, refresh / revoke tokens, JWT bearer auth, and role-aware permissions |
| **Drivers** | Full CRUD for the 2025 F1 driver grid (admin-managed, public read) + historical season stats |
| **Teams** | Full CRUD for the 2025 constructor lineup (admin-managed, public read) + standings, results & season stats |
| **Circuits** | Browse all F1 circuits/venues with location, country, and active-status filtering |
| **Seasons** | Explore every championship season with champion info and calendar metadata |
| **Races** | Full race calendar with winner info, filterable by season and circuit |
| **Results** | Race results, sprint results, and lap-time analytics with flexible filtering |
| **Favourites** | Create personal lists of favourite drivers and teams |
| **Predictions** | Predict the Driver & Constructor Champions with confidence ratings |
| **Leaderboard** | Global aggregated view of who the community thinks will win |
| **Trivia & Facts** | Random F1 facts, user-submitted facts with like/approve, plus a quiz mode |
| **Head-to-Head** | Compare any two drivers' stats side-by-side and vote on who's better |
| **Hot Takes** | Post controversial F1 opinions — others agree or disagree |
| **Native MCP** | Built-in Model Context Protocol endpoint (`/mcp`) for AI tools/agents |

## Project Structure

```
cw1/
├── .github/                  # GitHub Actions workflows
├── docker/
│   ├── .dockerignore
│   └── Dockerfile            # Container image for deployment
├── scripts/
│   ├── ci/
│   │   └── run-tests.sh      # CI test entrypoint used by GitHub Actions
│   └── mongodb/
│       ├── onboard.py        # Admin user onboarding helper
│       └── reset_db.py       # Drop/reset database helper
├── src/
│   ├── main.py               # FastAPI app entry point
│   ├── mcp/                  # Native MCP package
│   │   ├── __init__.py       # Exports MCP router
│   │   ├── auth.py           # MCP auth helpers
│   │   ├── server.py         # JSON-RPC protocol + MCP routes
│   │   └── tools.py          # MCP tool schemas, handlers, registry
│   ├── config/
│   │   └── settings.py       # Pydantic settings from .env
│   ├── core/
│   │   ├── exceptions.py     # Custom API exception hierarchy
│   │   ├── rate_limit.py     # SlowAPI limiter configuration
│   │   └── security.py       # JWT, refresh-token helpers, RBAC, password hashing
│   ├── data/
│   │   └── seed.py           # Kaggle-based seeder for grid + historical data
│   ├── db/                   # MongoDB query functions
│   │   ├── audit_logs.py     # Security audit log writes / reads
│   │   ├── collections.py    # Collection name constants
│   │   ├── circuits.py       # Circuit queries
│   │   ├── drivers.py        # Driver CRUD + season stats queries
│   │   ├── facts.py
│   │   ├── favourites.py
│   │   ├── head_to_head.py
│   │   ├── hot_takes.py
│   │   ├── predictions.py
│   │   ├── races.py          # Race + status queries
│   │   ├── results.py        # Race/sprint result + lap-time queries
│   │   ├── seasons.py        # Season queries
│   │   ├── teams.py          # Team CRUD + constructor history queries
│   │   ├── tokens.py         # Refresh-token storage + access-token blacklist
│   │   └── users.py
│   ├── models/               # Pydantic models (schemas)
│   │   ├── circuit.py        # Circuit model
│   │   ├── common.py         # Shared base classes & historical mixins
│   │   ├── driver.py         # Driver + DriverSeasonStat
│   │   ├── fact.py
│   │   ├── favourite.py
│   │   ├── head_to_head.py
│   │   ├── hot_take.py
│   │   ├── prediction.py
│   │   ├── race.py           # Race + Status models
│   │   ├── result.py         # RaceResult, SprintResult, LapTimeSummary
│   │   ├── season.py         # Season model
│   │   ├── team.py           # Team + constructor history models
│   │   └── user.py
│   └── routers/              # REST API route handlers
│       ├── auth.py
│       ├── circuits.py       # List, search, and fetch circuits
│       ├── drivers.py        # CRUD + driver season stats
│       ├── favourites.py
│       ├── head_to_head.py
│       ├── hot_takes.py
│       ├── predictions.py
│       ├── races.py          # Races + finish status endpoints
│       ├── results.py        # Race results, sprint results, lap-times
│       ├── seasons.py        # Season browsing endpoints
│       ├── teams.py          # CRUD + constructor stats/standings/results
│       └── trivia.py
├── tests/                    # API and DB-layer test suite
│   ├── conftest.py
│   └── test_*.py
├── Makefile                  # Quick commands
├── pyproject.toml            # Pytest / coverage configuration
├── README.md
├── render.yaml               # Render deployment blueprint
└── requirements.txt          # Python dependencies
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
TOKEN_EXPIRY_MINUTES=30
REFRESH_TOKEN_EXPIRY_DAYS=7
ORIGINS=http://localhost:3000,http://localhost:5173
RATE_LIMIT_DEFAULT=60/minute
RATE_LIMIT_AUTH=3/minute
RATE_LIMIT_SENSITIVE=10/minute
MCP_REQUIRE_AUTH=false
EOF
```

Key variables:
| Variable | Default | Description |
|---|---|---|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `DB_NAME` | `f1_facts_db` | Database name |
| `JWT_SECRET` | random | Change this in production! |
| `TOKEN_EXPIRY_MINUTES` | `30` | Access-token expiry time in minutes |
| `REFRESH_TOKEN_EXPIRY_DAYS` | `7` | Refresh-token expiry time in days |
| `ORIGINS` | `http://localhost:3000,http://localhost:5173` | Allowed CORS origins |
| `RATE_LIMIT_DEFAULT` | `60/minute` | Default per-IP API rate limit |
| `RATE_LIMIT_AUTH` | `3/minute` | Stricter per-IP limit for register / login |
| `RATE_LIMIT_SENSITIVE` | `10/minute` | Per-IP limit for sensitive auth flows such as token refresh |
| `MCP_REQUIRE_AUTH` | `false` | Require `Authorization: Bearer <JWT>` for MCP `tools/call` |

### 3. Seed the database

Downloads the [Kaggle F1 Race Data](https://www.kaggle.com/datasets/jtrotman/formula-1-race-data) dataset and populates the database with current drivers and teams, historical circuits / seasons / races / results, compact lap-time and season-summary analytics, plus seeded trivia facts:

```bash
make seed

# Or to drop all collections and re-seed from scratch:
make reseed
```

`make reseed` now drops the whole configured database first, so it works for both local MongoDB and MongoDB Atlas when `MONGO_URI` points at your Atlas cluster.

> Default admin credentials: `admin` / `admin123` (created with the `admin` role)

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

### 7. Use native MCP support

This API supports both traditional REST clients and AI-native clients.

- Use the REST endpoints for browsers, frontend apps, Swagger UI, and standard HTTP integrations.
- Use MCP (Model Context Protocol) when an AI assistant, agent, or tool needs a structured way to discover capabilities and call your API safely.

In practice, MCP matters because it gives AI clients a predictable JSON-RPC interface for tool discovery and execution, while the existing REST API remains unchanged for human and web consumers.

The MCP surface is exposed at:

- `POST /mcp` for protocol calls (`initialize`, `tools/list`, `tools/call`)
- `GET /mcp` for basic discovery/health metadata

The implementation is now modularised under `src/mcp/`:

- `src/mcp/server.py` handles JSON-RPC validation, routing, and FastAPI integration
- `src/mcp/tools.py` contains the MCP tool schemas and handlers
- `src/mcp/auth.py` contains optional JWT auth enforcement for `tools/call`

All MCP tools are read-only and mirror the same `src.db` query functions used by the public REST API, so MCP responses stay consistent with the rest of the application.

Currently exposed read-only MCP tools:

- `list_drivers`
- `search_drivers`
- `get_driver_season_stats`
- `list_teams`
- `search_teams`
- `list_circuits`
- `search_circuits`
- `list_seasons`
- `list_races`
- `list_race_results`
- `get_random_fact`
- `list_facts`
- `get_prediction_leaderboard`

Authentication behavior:

- `initialize` and `tools/list` are always public.
- `tools/call` is public by default.
- Set `MCP_REQUIRE_AUTH=true` to require JWT Bearer auth on `tools/call`.
- When auth is enabled, send `Authorization: Bearer <JWT>` exactly like the protected REST endpoints.

Swagger UI notes:

- `POST /mcp` now has a proper request body schema via the `MCPRequest` model.
- You can test `initialize`, `tools/list`, and `tools/call` directly from `/docs` by editing the JSON body.

Example MCP `initialize` request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {}
}
```

Example MCP `tools/list` request:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

Example MCP `tools/call` request:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "list_drivers",
    "arguments": {
      "active_only": true,
      "limit": 5
    }
  }
}
```

Example authenticated MCP request:

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "get_prediction_leaderboard",
      "arguments": {
        "category": "driver_championship",
        "season": 2025
      }
    }
  }'
```

Run MCP-specific tests with:

```bash
python -m pytest tests/test_mcp.py -v
```

## Deployment

This repository is now set up for deployment to **Render** with **GitHub Actions** controlling when a deployment happens.

### Deployment architecture

- **App host:** Render web service using the included Dockerfile
- **Database:** MongoDB Atlas (or another externally reachable MongoDB instance)
- **CI/CD gate:** GitHub Actions runs your custom test script first
- **Deploy rule:** only pushes to `main` deploy, and only if the test job passes

### Files added for deployment

- `docker/Dockerfile` — container image for the FastAPI app
- `docker/.dockerignore` — Docker build exclusions
- `render.yaml` — Render service blueprint with production env vars
- `.github/workflows/ci-cd.yml` — test + deploy workflow
- `scripts/ci/run-tests.example.sh` — sample test script you can copy and customise

### 1. Create your CI test script

Create this file in your repo:

```bash
mkdir -p scripts/ci
cp scripts/ci/run-tests.example.sh scripts/ci/run-tests.sh
chmod +x scripts/ci/run-tests.sh
```

Edit `scripts/ci/run-tests.sh` to run exactly the checks you want GitHub Actions to enforce before deployment.

Example:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

python -m pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=80
```

> The workflow calls `bash scripts/ci/run-tests.sh`, so deployment is blocked until that script exits successfully with at least `80%` coverage.

### 2. Provision production services

Before deploying, create:

- a **MongoDB Atlas** cluster (or another hosted MongoDB)
- a **Render** web service connected to this repository

Use the included `render.yaml` when creating the Render service, or create the service manually with Docker enabled.

### 3. Configure Render environment variables

Set these in Render:

| Variable | Required | Notes |
|---|---|---|
| `MONGO_URI` | Yes | Hosted MongoDB connection string, not localhost |
| `DB_NAME` | Yes | Usually `f1_facts_db` |
| `JWT_SECRET` | Yes | Long random secret for production |
| `TOKEN_EXPIRY_MINUTES` | No | Defaults to `30` |
| `REFRESH_TOKEN_EXPIRY_DAYS` | No | Defaults to `7` |
| `ORIGINS` | Yes | Your frontend origin(s), comma-separated |
| `RATE_LIMIT_DEFAULT` | No | Defaults to `60/minute` |
| `RATE_LIMIT_AUTH` | No | Defaults to `3/minute` |
| `RATE_LIMIT_SENSITIVE` | No | Defaults to `10/minute` |

### 4. Create the Render deploy hook secret in GitHub

In Render, create a **Deploy Hook** for the service.

Then in GitHub, add this repository secret:

- `RENDER_DEPLOY_HOOK_URL` = your Render deploy hook URL

GitHub path: **Settings → Secrets and variables → Actions → New repository secret**

### 5. GitHub Actions behaviour

The workflow in `.github/workflows/ci-cd.yml` does the following:

- runs on every pull request
- runs on every push to `main`
- installs dependencies
- executes `scripts/ci/run-tests.sh`
- triggers Render deployment **only** when:
  - the event is a push to `main`, and
  - the test job succeeded

### 6. Recommended first deployment flow

1. Create `scripts/ci/run-tests.sh`
2. Push the repo to GitHub
3. Create the Render service
4. Add Render environment variables
5. Add the `RENDER_DEPLOY_HOOK_URL` GitHub secret
6. Push to `main`

Once that is done, future pushes to `main` will deploy automatically after your test script passes.

### Important production note

Your local default `MONGO_URI=mongodb://localhost:27017` will **not** work on an external host. Production must use a hosted MongoDB connection string, such as MongoDB Atlas.

## Security Notes

- The API uses short-lived JWT bearer access tokens for protected endpoints.
- Login and registration return both an `access_token` and a `refresh_token`.
- Refresh tokens are stored hashed in MongoDB and rotated on `POST /auth/refresh`.
- Access tokens include a unique `jti`; revoked access tokens are rejected via a blacklist check.
- `POST /auth/logout` revokes the supplied refresh token and blacklists the current access token.
- `POST /auth/logout-all` revokes all refresh tokens for the current user.
- User roles are hierarchical: `user` < `moderator` < `admin`.
- Security events such as register, login, failed login, refresh, logout, and account deletion are audit-logged.
- Requests are rate-limited per IP using `slowapi`.
- The default API-wide limit is `60/minute`.
- The `/auth/register` and `/auth/login` endpoints use a stricter `3/minute` limit.
- The `/auth/refresh` endpoint uses `10/minute`.
- When a limit is exceeded, the API returns HTTP `429 Too Many Requests`.

### Security Architecture

```text
Client
  ├─ POST /auth/register or /auth/login
  │    └─ receives access_token + refresh_token
  ├─ Uses access_token on protected REST / MCP calls
  │    └─ API validates JWT signature, expiry, role, and JTI blacklist
  ├─ Uses refresh_token on POST /auth/refresh
  │    └─ API validates hashed refresh token in MongoDB, revokes old token, issues new pair
  └─ Uses POST /auth/logout or /auth/logout-all
       └─ API revokes refresh tokens and blacklists current access token JTI
```

| Layer | Responsibility |
|---|---|
| `src/core/security.py` | Creates access tokens, generates refresh tokens, decodes JWTs, enforces RBAC, and blocks blacklisted access tokens |
| `src/db/tokens.py` | Stores hashed refresh tokens, rotates / revokes them, and maintains the access-token blacklist |
| `src/db/audit_logs.py` | Records security-sensitive events for traceability and incident review |
| `src/routers/auth.py` | Exposes register, login, refresh, logout, logout-all, and profile endpoints |
| MongoDB indexes | Speed up token lookups, blacklist checks, and audit-log queries |

### Security Flow Summary

| Flow | What happens |
|---|---|
| Login / register | Issue a short-lived JWT access token plus a long-lived opaque refresh token |
| Protected request | Validate signature, expiry, claims, and blacklist status before serving data |
| Token refresh | Revoke old refresh token, create a new refresh token, and mint a new access token |
| Logout | Revoke the refresh token for that session and blacklist the current access token |
| Logout all | Revoke all refresh tokens for the user and invalidate the current access token |
| Audit trail | Persist login, failed login, refresh, logout, and deletion events with request metadata |

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
| POST | `/auth/register` | No | Create account and receive access + refresh tokens |
| POST | `/auth/login` | No | Login (form-data), receive access + refresh tokens |
| POST | `/auth/refresh` | No | Rotate refresh token and receive a new token pair |
| POST | `/auth/logout` | Yes | Revoke one refresh token and blacklist the current access token |
| POST | `/auth/logout-all` | Yes | Revoke all active refresh-token sessions for the current user |
| GET | `/auth/me` | Yes | Get profile |
| PATCH | `/auth/me` | Yes | Update profile |
| DELETE | `/auth/me` | Yes | Delete account and revoke all sessions |

### Drivers
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/drivers` | No | List all drivers |
| GET | `/drivers/search?name=&team=` | No | Search drivers |
| GET | `/drivers/{id}` | No | Get driver by ID |
| POST | `/drivers` | Admin | Create driver |
| PATCH | `/drivers/{id}` | Admin | Update driver |
| DELETE | `/drivers/{id}` | Admin | Delete driver |
| GET | `/drivers/{id}/stats?season_year=` | No | Historical season stats for a driver |
| GET | `/drivers/stats/season/{year}` | No | All driver stats for a season |

### Teams
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/teams` | No | List all teams |
| GET | `/teams/search?name=` | No | Search teams |
| GET | `/teams/{id}` | No | Get team by ID |
| POST | `/teams` | Admin | Create team |
| PATCH | `/teams/{id}` | Admin | Update team |
| DELETE | `/teams/{id}` | Admin | Delete team |
| GET | `/teams/{id}/stats?season_year=` | No | Historical season stats for a team |
| GET | `/teams/stats/season/{year}` | No | All constructor stats for a season |
| GET | `/teams/{id}/standings?season_year=&final_only=` | No | Championship standings history |
| GET | `/teams/{id}/results?season_year=` | No | Constructor race results history |

### Circuits
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/circuits?active_only=&country=` | No | List all circuits |
| GET | `/circuits/search?name=&country=` | No | Search circuits |
| GET | `/circuits/{circuit_id}` | No | Get circuit by Kaggle circuitId |

### Seasons
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/seasons?start_year=&end_year=` | No | List all seasons (newest first) |
| GET | `/seasons/{year}` | No | Get a single season by year |

### Races
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/races?season_year=&circuit_id=` | No | List races |
| GET | `/races/statuses` | No | List all finish status codes |
| GET | `/races/{race_id}` | No | Get race by Kaggle raceId |
| GET | `/races/season/{year}/round/{round}` | No | Get race by season and round |

### Results
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/results/race?race_id=&season_year=&driver_id=&constructor_id=&limit=` | No | Race results |
| GET | `/results/sprint?race_id=&season_year=&driver_id=&limit=` | No | Sprint results |
| GET | `/results/lap-times?race_id=&driver_id=&season_year=&limit=` | No | Lap-time summaries |

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

The API uses **JWT Bearer access tokens** plus **opaque refresh tokens**.

After registering or logging in, use the `access_token` for authenticated requests:

```
Authorization: Bearer <your-token>
```

Use the `refresh_token` only with `POST /auth/refresh` to obtain a new token pair when the access token expires.

Logout behavior:

- `POST /auth/logout` ends a single session by revoking the supplied refresh token and blacklisting the current access token.
- `POST /auth/logout-all` ends all active sessions for the authenticated user.

Role behavior:

- Most write actions require authentication.
- Admin-managed resources such as driver, team, and trivia moderation endpoints require the `admin` role.

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

# Response includes both tokens; use the access token for Bearer auth
ACCESS_TOKEN="your-access-token"
REFRESH_TOKEN="your-refresh-token"

# Refresh / rotate tokens
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"'"$REFRESH_TOKEN"'"}'

# Logout current session
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"'"$REFRESH_TOKEN"'"}'
```

### Create a favourite list & add drivers
```bash
TOKEN="your-access-token"

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
