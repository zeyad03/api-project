"""F1 Facts API – main application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.config.settings import settings
from src.core.exceptions import F1FactsAPIError
from src.core.rate_limit import limiter
from src.routers.auth import router as auth_router
from src.routers.circuits import router as circuits_router
from src.routers.drivers import router as drivers_router
from src.routers.favourites import router as favourites_router
from src.routers.head_to_head import router as h2h_router
from src.routers.hot_takes import router as hot_takes_router
from src.mcp import router as mcp_router
from src.routers.predictions import router as predictions_router
from src.routers.races import router as races_router
from src.routers.results import router as results_router
from src.routers.seasons import router as seasons_router
from src.routers.teams import router as teams_router
from src.routers.trivia import router as trivia_router


# ── Lifespan: connect / disconnect MongoDB ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage MongoDB connection over the application lifespan."""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    app.state.db = client.get_database(settings.DB_NAME)
    # Quick connection check
    try:
        await app.state.db.command("ping")
        print(f"Connected to MongoDB - database: {settings.DB_NAME}")
    except Exception as exc:
        print(f"MongoDB connection failed: {exc}")
        raise
    yield
    client.close()
    print("MongoDB connection closed")


# ── App instance ─────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "A fun, community-driven F1 Facts API. "
        "Track drivers & teams, build favourite lists, predict championships, "
        "play trivia quizzes, compare drivers head-to-head, and share hot takes!"
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter


# ── CORS ─────────────────────────────────────────────────────────────────────
origins = settings.get_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)


# ── Exception handlers ──────────────────────────────────────────────────────
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(
    _: Request, exc: RateLimitExceeded
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(F1FactsAPIError)
async def f1_api_exception_handler(_: Request, exc: F1FactsAPIError) -> JSONResponse:
    """Translate any custom F1FactsAPIError into a JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    # Sanitise errors: convert bytes to str so they're JSON-serialisable
    clean_errors = []
    for err in exc.errors():
        clean = {}
        for k, v in err.items():
            if isinstance(v, bytes):
                clean[k] = v.decode(errors="replace")
            else:
                clean[k] = v
        clean_errors.append(clean)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": clean_errors},
    )


@app.exception_handler(Exception)
async def general_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── Register routers ────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(drivers_router, prefix="/drivers", tags=["Drivers"])
app.include_router(teams_router, prefix="/teams", tags=["Teams"])
app.include_router(favourites_router, prefix="/favourites", tags=["Favourites"])
app.include_router(predictions_router, prefix="/predictions", tags=["Predictions"])
app.include_router(circuits_router, prefix="/circuits", tags=["Circuits"])
app.include_router(seasons_router, prefix="/seasons", tags=["Seasons"])
app.include_router(races_router, prefix="/races", tags=["Races"])
app.include_router(results_router, prefix="/results", tags=["Results"])
app.include_router(trivia_router, prefix="/trivia", tags=["Trivia & Facts"])
app.include_router(hot_takes_router, prefix="/hot-takes", tags=["Hot Takes"])
app.include_router(h2h_router, prefix="/head-to-head", tags=["Head-to-Head"])
app.include_router(mcp_router, prefix="/mcp", tags=["MCP"])


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "project": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs",
    }
