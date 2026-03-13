# F1 Facts API

A Formula 1 backend service with two interfaces over the same domain:

- REST API (FastAPI)
- Native MCP endpoint (`/mcp`) for AI tool discovery and calls

This README is intentionally focused on:

- how to run the service locally (developers / contributors)
- how to use the deployed API (API consumers)

For full endpoint contracts, schemas, and examples, use the OpenAPI documentation links below.

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
