"""
Simulation API v1 — Monte Carlo, Markov analysis, cost analysis, historical insights.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Optional

from congress_twin.services.cost_function import compute_total_cost
from congress_twin.services.historical_analyzer import get_historical_insights
from congress_twin.services.markov_chain_tracker import get_markov_analysis
from congress_twin.services.monte_carlo_simulator import run_simulation
from congress_twin.services.planner_simulated_data import DEFAULT_PLAN_ID

router = APIRouter()


class MonteCarloRequest(BaseModel):
    plan_id: str = DEFAULT_PLAN_ID
    n_iterations: int = 10000
    historical_plan_ids: Optional[list[str]] = None


class CostAnalysisRequest(BaseModel):
    plan_id: str = DEFAULT_PLAN_ID
    weights: Optional[dict[str, float]] = None


@router.post("/monte-carlo")
async def run_monte_carlo_simulation(request: MonteCarloRequest) -> dict[str, Any]:
    """
    Run Monte Carlo simulation: 10K iterations, DAG traversal, resource contention, external events.
    Returns percentiles, critical path probability, bottlenecks, risk heatmap.
    """
    try:
        result = run_simulation(
            plan_id=request.plan_id,
            n_iterations=request.n_iterations,
            historical_plan_ids=request.historical_plan_ids,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monte Carlo simulation failed: {str(e)}")


@router.get("/markov-analysis")
async def get_markov_analysis_endpoint(
    plan_id: str = Query(default=DEFAULT_PLAN_ID),
    task_id: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    """
    Get Markov chain analysis: State transition probabilities, expected completion time.
    """
    try:
        result = get_markov_analysis(plan_id, task_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Markov analysis failed: {str(e)}")


@router.post("/cost-analysis")
async def compute_cost_analysis(request: CostAnalysisRequest) -> dict[str, Any]:
    """
    Compute cost analysis: Multi-objective cost breakdown with configurable weights.
    """
    try:
        result = compute_total_cost(
            plan_id=request.plan_id,
            weights=request.weights,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cost analysis failed: {str(e)}")


@router.get("/historical-insights")
async def get_historical_insights_endpoint(
    plan_id: str = Query(default=DEFAULT_PLAN_ID),
    historical_plan_ids: Optional[list[str]] = Query(default=None),
) -> dict[str, Any]:
    """
    Get historical insights: Duration bias, bottleneck patterns, resource profiles, risk patterns.
    """
    try:
        result = get_historical_insights(
            current_plan_id=plan_id,
            historical_plan_ids=historical_plan_ids,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Historical insights failed: {str(e)}")
