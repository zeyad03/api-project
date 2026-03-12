"""Circuits router – browse F1 circuit / venue data."""

from fastapi import APIRouter, Query, Request

from src.core.exceptions import NotFoundError
from src.db.circuits import get_all_circuits, get_circuit_by_id, search_circuits
from src.models.circuit import Circuit
from src.models.common import PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[Circuit])
async def list_circuits(
    request: Request,
    active_only: bool = Query(False, description="Only return currently active circuits"),
    country: str | None = Query(None, description="Filter by country"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
):
    """List all F1 circuits. No auth required."""
    circuits, total = await get_all_circuits(
        request.app.state.db, active_only=active_only, country=country,
        skip=skip, limit=limit,
    )
    return PaginatedResponse(data=circuits, total=total, skip=skip, limit=limit)


@router.get("/search", response_model=PaginatedResponse[Circuit])
async def search(
    request: Request,
    name: str | None = Query(None, description="Circuit name (partial match)"),
    country: str | None = Query(None, description="Country (partial match)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
):
    """Search circuits by name or country."""
    circuits, total = await search_circuits(
        request.app.state.db, name=name, country=country, skip=skip, limit=limit,
    )
    return PaginatedResponse(data=circuits, total=total, skip=skip, limit=limit)


@router.get("/{circuit_id}", response_model=Circuit)
async def get_circuit(circuit_id: int, request: Request):
    """Get a single circuit by its Kaggle circuitId."""
    circuit = await get_circuit_by_id(circuit_id, request.app.state.db)
    if not circuit:
        raise NotFoundError("Circuit", str(circuit_id))
    return circuit
