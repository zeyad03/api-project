"""Circuits router – browse F1 circuit / venue data."""

from fastapi import APIRouter, HTTPException, Query, Request, status

from src.db.circuits import get_all_circuits, get_circuit_by_id, search_circuits
from src.models.circuit import Circuit

router = APIRouter()


@router.get("", response_model=list[Circuit])
async def list_circuits(
    request: Request,
    active_only: bool = Query(False, description="Only return currently active circuits"),
    country: str | None = Query(None, description="Filter by country"),
):
    """List all F1 circuits. No auth required."""
    return await get_all_circuits(
        request.app.state.db, active_only=active_only, country=country
    )


@router.get("/search", response_model=list[Circuit])
async def search(
    request: Request,
    name: str | None = Query(None, description="Circuit name (partial match)"),
    country: str | None = Query(None, description="Country (partial match)"),
):
    """Search circuits by name or country."""
    return await search_circuits(request.app.state.db, name=name, country=country)


@router.get("/{circuit_id}", response_model=Circuit)
async def get_circuit(circuit_id: int, request: Request):
    """Get a single circuit by its Kaggle circuitId."""
    circuit = await get_circuit_by_id(circuit_id, request.app.state.db)
    if not circuit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circuit with id '{circuit_id}' was not found.",
        )
    return circuit
