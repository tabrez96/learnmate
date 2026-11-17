"""The month's AI spend for the parent side, and the error for a reached budget."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from learnmate.api.deps import AppSettings, DbSession
from learnmate.llm.budget import status

router = APIRouter(prefix="/api/v1")


class BudgetOut(BaseModel):
    month: str
    spent_usd: float
    budget_usd: float
    reached: bool


@router.get("/budget")
def get_budget(request: Request, db: DbSession, settings: AppSettings) -> BudgetOut:
    current = status(db, settings, request.app.state.clock)
    return BudgetOut(
        month=current.month,
        spent_usd=float(current.spent_usd),
        budget_usd=float(current.budget_usd),
        reached=current.reached,
    )


def budget_reached_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=409, content={"error": "budget_reached", "detail": str(exc)}
    )
