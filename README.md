# F1 Facts API

A Formula 1 backend service with two interfaces over the same domain:

- REST API (FastAPI)
- Native MCP endpoint (`/mcp`) for AI tool discovery and calls

This README is intentionally focused on:

- how to run the service locally (developers / contributors)
- how to use the deployed API (API consumers)

For full endpoint contracts, schemas, and examples, use the OpenAPI documentation links below.

## Project overview

This project is a Formula 1 facts service built around a single domain + data-access layer, exposed through two interfaces:

- **REST API (FastAPI)** for standard client/server use
- **MCP endpoint (`/mcp`)** for AI tool discovery and tool calls (JSON-RPC)

The core idea is that both interfaces share the same DB/query layer and Pydantic models, so REST and MCP stay consistent as the domain evolves.

### Tech stack (at a glance)

- **Python 3.12** + **FastAPI** (ASGI)
- **MongoDB** via **Motor** (async driver built on PyMongo)
- **Pydantic models** for schema/validation (`src/models/`)
- **JWT auth** (bcrypt + `python-jose`) with roles (`user`/`moderator`/`admin`)
- **Rate limiting** via **slowapi** (per-IP)
- **Pytest** test suite (`tests/`)
- Deployment support via **Docker** and **Render** (`docker/`, `render.yaml`)

### High-level architecture

At runtime, the app follows a simple layered structure:

1. **App entrypoint** wires routers + middleware (`src/main.py`)
2. **Routers** define REST request/response contracts (`src/routers/`)
3. **DB layer** encapsulates MongoDB queries and write patterns (`src/db/`)
4. **Models** define domain schemas and shared types (`src/models/`)
5. **Core utilities** implement cross-cutting concerns like auth, rate limits, and errors (`src/core/`)

The MongoDB connection is created once per app lifespan and stored on `app.state.db` (see `src/main.py`). Startup also ensures a small set of security-related indexes (refresh tokens, blacklist JTIs, audit log query indexes).

The MCP adapter (`src/mcp/`) exposes a JSON-RPC surface over the same domain operations (tool registry + auth adapter). Both REST routers and MCP tools call into the same `src/db/*` functions.

### Request flow (REST + MCP)

- **REST**: client → FastAPI router → DB layer → MongoDB → response
- **MCP**: client → `/mcp` JSON-RPC → tool registry → DB layer → MongoDB → tool result

In both cases, the service aims for consistent validation (Pydantic), consistent error semantics (central exceptions), and consistent data-access behavior (shared query functions).

### Core features

- **Authentication & authorization**
  - JWT bearer auth for protected endpoints
  - Password hashing via bcrypt (`src/core/security.py`)
  - Access + refresh token flow with refresh-token rotation
  - Refresh tokens are stored **hashed** (SHA-256), not in plaintext (`src/db/tokens.py`)
  - Access-token revocation via **JTI blacklist** checked on protected routes (`src/db/tokens.py`, `src/core/security.py`)
  - Optional stricter auth requirements for MCP (`MCP_REQUIRE_AUTH`)
  - Role hierarchy utilities exist (`user` < `moderator` < `admin`) via `require_role()` / `require_admin()` (`src/core/security.py`, `src/models/user.py`)

- **Rate limiting**
  - Configurable default/auth/sensitive limits (see `RATE_LIMIT_*` in `.env`)
  - Per-IP limiting via slowapi (`src/core/rate_limit.py`)
  - Uses in-memory limiter storage by default (resets on restart; per-instance)

- **Consistent error handling**
  - Shared exception types and error semantics in `src/core/exceptions.py`

- **Auditing (security events)**
  - Auth flows emit audit events (register/login/login_failed/logout/logout_all/token_refresh) (`src/db/audit_logs.py`, `src/routers/auth.py`)

- **Structured logging**
  - Central logger configuration driven by `LOG_LEVEL` (`src/core/logging.py`)

- **Domain features (what the API actually does)**
  - Core data browsing: drivers/teams/circuits/seasons/races/results (`src/routers/drivers.py`, `src/routers/teams.py`, `src/routers/circuits.py`, `src/routers/seasons.py`, `src/routers/races.py`, `src/routers/results.py`)
  - Community features: favourites lists, championship predictions + leaderboards, head-to-head voting, hot takes (`src/routers/favourites.py`, `src/routers/predictions.py`, `src/routers/head_to_head.py`, `src/routers/hot_takes.py`)
  - Trivia & facts: an in-memory quiz bank plus user-submitted facts that require admin approval (`src/routers/trivia.py`, `src/db/facts.py`)
  - Current admin-only actions include approving/deleting facts and deleting any user's hot take (`src/routers/trivia.py`, `src/routers/hot_takes.py`)

- **MCP tool surface (subset of the REST surface)**
  - Tools are defined in `src/mcp/tools.py` and mirror selected public REST reads (e.g., list/search drivers/teams/circuits, seasons/races/results, facts, prediction leaderboards)

- **Seed + admin utilities**
  - Dataset seeding pipeline: `src/data/seed.py`
  - MongoDB reset + onboarding helpers: `scripts/mongodb/`

### Configuration and runtime behavior

- Environment-driven settings are parsed in `src/config/settings.py` (Mongo connection, JWT settings, CORS origins, rate-limit defaults, logging).
- The same configuration is used for REST and MCP; in particular `MCP_REQUIRE_AUTH` controls whether MCP tool calls require bearer auth.

### Repository map (where to find things)

- `src/main.py`: FastAPI app creation + router wiring
- `src/routers/`: REST endpoints grouped by domain area (drivers, races, results, etc.)
- `src/db/`: MongoDB query layer used by both REST and MCP
- `src/models/`: Pydantic models shared across routers/DB/MCP
- `src/mcp/`: MCP server adapter + tool registry
- `src/core/`: cross-cutting concerns (security, rate limiting, logging, exceptions)
- `tests/`: unit/API/auth/integration tests

For additional pointers, see [Useful source references](#useful-source-references) further down.

## API documentation (hosted)

- OpenAPI HTML (ReDoc): https://api-project-qa2c.onrender.com/documentation/api-docs.html
- OpenAPI PDF: https://api-project-qa2c.onrender.com/documentation/api-docs.pdf
- Swagger UI: https://api-project-qa2c.onrender.com/docs

Base URL: https://api-project-qa2c.onrender.com

## For developers (local setup / contributing)

### Prerequisites

- Python 3.12
- MongoDB Community 7.0 (macOS via Homebrew: `brew install mongodb-community@7.0`)

Optional (only needed if you plan to seed from Kaggle):

- Kaggle access configured for `kagglehub` (see the seeder in `src/data/seed.py`)

### 1) Create a venv and install dependencies

```bash
python3 -m venv venv
make install
```

### 2) Configure environment

Create a `.env` file in the repository root:

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
LOG_LEVEL=INFO
EOF
```

Key variables used most often:

| Variable | What it controls | Typical local value |
|---|---|---|
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `DB_NAME` | Database name | `f1_facts_db` |
| `JWT_SECRET` | Access-token signing secret | long random string |
| `MCP_REQUIRE_AUTH` | Whether `POST /mcp` `tools/call` needs auth | `false` |
| `LOG_LEVEL` | App log verbosity | `INFO` |

### 3) Start MongoDB, seed data (optional), and run the API

```bash
make db-start

# Optional: populate the DB from the Kaggle dataset
make seed

# Optional: create an admin user for local testing
make onboard

# Run with hot reload
make dev
```

Server will be available at:

- http://localhost:8000 (API)
- http://localhost:8000/docs (Swagger UI)

To stop:

```bash
make stop
make db-stop
```

### 4) Tests

```bash
make test
make test-fast
make test-cov
```

Useful focused runs:

```bash
python -m pytest tests/ -m unit -v
python -m pytest tests/ -m api -v
python -m pytest tests/ -m auth -v
python -m pytest tests/ -m integration -v
```

### 5) Typical contributor workflow

1. Pull latest changes.
2. Activate venv and install dependencies if needed.
3. Start MongoDB and run `make dev`.
4. Run targeted tests while developing.
5. Run `make test-cov` before pushing.
6. Open OpenAPI docs locally at `http://localhost:8000/docs` to validate request/response behavior.

### Useful source references

| Area | Where to look |
|---|---|
| App entry + router wiring | `src/main.py` |
| Settings/env parsing | `src/config/settings.py` |
| Auth + JWT + RBAC | `src/core/security.py` and `src/routers/auth.py` |
| Rate limiting | `src/core/rate_limit.py` |
| Exceptions + error semantics | `src/core/exceptions.py` |
| MongoDB query layer (shared by REST + MCP) | `src/db/` |
| REST routers (request/response contracts) | `src/routers/` |
| MCP adapter + tool registry | `src/mcp/server.py`, `src/mcp/tools.py`, `src/mcp/auth.py` |
| Seeding pipeline | `src/data/seed.py` |
| Admin onboarding + DB reset helpers | `scripts/mongodb/onboard.py`, `scripts/mongodb/reset_db.py` |
| Test suite | `tests/` |

### Deployment references (for maintainers)

- Container image: `docker/Dockerfile`
- Render blueprint: `render.yaml`
- CI test entrypoint: `scripts/ci/run-tests.sh`

## For API users (consumers)

### 1) Use the hosted API

You do not need to install anything to use the API. Use the hosted base URL:

- https://api-project-qa2c.onrender.com

Then build your client from one of the published API docs:

- HTML: https://api-project-qa2c.onrender.com/documentation/api-docs.html
- PDF: https://api-project-qa2c.onrender.com/documentation/api-docs.pdf

### 2) Authentication (summary)

- Protected endpoints use JWT bearer tokens:

  `Authorization: Bearer <access_token>`

- Login/register returns both `access_token` and `refresh_token`.
- Use `refresh_token` only on the refresh route to rotate tokens.

### 3) Minimal request examples

Health check:

```bash
curl https://api-project-qa2c.onrender.com/
```

Login:

```bash
curl -X POST https://api-project-qa2c.onrender.com/auth/login \
  -d 'username=<your-username>&password=<your-password>'
```

Public paginated list example:

```bash
curl "https://api-project-qa2c.onrender.com/drivers?skip=0&limit=5"
```

### 4) Using the API from your code

Below are minimal examples that follow the real API auth flow:

1. Login via `POST /auth/login` using form-data (`username`, `password`)
2. Read `access_token` from the response
3. Call a protected endpoint with `Authorization: Bearer <access_token>`

Python (`requests`) example:

```python
import requests

BASE_URL = "https://api-project-qa2c.onrender.com"

# 1) Login (form-data)
login_resp = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": "<your-username>", "password": "<your-password>"},
    timeout=20,
)
login_resp.raise_for_status()
token_payload = login_resp.json()

access_token = token_payload["access_token"]

# 2) Call protected endpoint
me_resp = requests.get(
    f"{BASE_URL}/auth/me",
    headers={"Authorization": f"Bearer {access_token}"},
    timeout=20,
)
me_resp.raise_for_status()

print(me_resp.json())
```

JavaScript (`fetch`) example:

```javascript
const BASE_URL = "https://api-project-qa2c.onrender.com";

async function run() {
  // 1) Login (application/x-www-form-urlencoded)
  const form = new URLSearchParams();
  form.set("username", "<your-username>");
  form.set("password", "<your-password>");

  const loginRes = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });

  if (!loginRes.ok) {
    throw new Error(`Login failed: ${loginRes.status}`);
  }

  const { access_token } = await loginRes.json();

  // 2) Call protected endpoint
  const meRes = await fetch(`${BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${access_token}` },
  });

  if (!meRes.ok) {
    throw new Error(`Request failed: ${meRes.status}`);
  }

  const me = await meRes.json();
  console.log(me);
}

run().catch(console.error);
```

For full schemas (including refresh/logout payloads and response models), use the OpenAPI docs instead of duplicating endpoint details in this README.

### 5) MCP (optional)

MCP endpoints:

- `POST /mcp` (JSON-RPC calls)
- `GET /mcp` (basic discovery)

`tools/list` example:

```bash
curl -X POST https://api-project-qa2c.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Troubleshooting

### Local server does not start

- Ensure MongoDB is running: `make db-start`
- Check whether port `8000` is occupied, then run: `make stop`
- Re-run with hot reload: `make dev`

### `401` on protected endpoints

- Confirm `Authorization` header format is exactly `Bearer <access_token>`
- If token expired, call refresh to obtain a new pair
- If you logged out, your current access token may be blacklisted

### Seeding fails

- Verify network access and Kaggle credentials/configuration
- Confirm MongoDB connection in `.env` (`MONGO_URI`, `DB_NAME`)
- Retry with `make seed`; to fully reset first, use `make reseed`

### MCP calls rejected

- If `MCP_REQUIRE_AUTH=true`, include bearer auth in requests
- Check JSON-RPC payload shape (`jsonrpc`, `id`, `method`, `params`)
- Compare against examples in hosted API docs

### Tests fail unexpectedly

- Reinstall deps after pulls: `make install`
- Ensure `.env` points to a reachable MongoDB
- Run a focused test group first, then full suite (`make test-cov`)
