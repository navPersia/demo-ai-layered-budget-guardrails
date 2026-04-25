from __future__ import annotations

from .models import BudgetDecision


def check_request_budget(workspace: dict, estimated_request_cost_usd: float) -> BudgetDecision:
    if estimated_request_cost_usd > float(workspace["requestBudgetUsd"]):
        return BudgetDecision(
            allowed=False,
            reason="Estimated request cost exceeds the configured request budget.",
        )
    return BudgetDecision(allowed=True)


def check_session_budget(workspace: dict, session: dict) -> BudgetDecision:
    if session.get("status") != "active":
        return BudgetDecision(allowed=False, reason="Session is not active.")

    if float(session["totalEstimatedCostUsd"]) >= float(workspace["sessionBudgetUsd"]):
        return BudgetDecision(allowed=False, reason="Session budget exceeded.")

    if int(session["requestCount"]) >= int(workspace["maxRequestsPerSession"]):
        return BudgetDecision(allowed=False, reason="Session request limit exceeded.")

    return BudgetDecision(allowed=True)


def check_workspace_budget(workspace: dict, daily_total: float, monthly_total: float) -> BudgetDecision:
    if daily_total >= float(workspace["dailyBudgetUsd"]):
        return BudgetDecision(
            allowed=False,
            reason="Workspace daily budget exceeded. AI calls are temporarily disabled.",
        )

    if monthly_total >= float(workspace["monthlyBudgetUsd"]):
        return BudgetDecision(
            allowed=False,
            reason="Workspace monthly budget exceeded. AI calls are temporarily disabled.",
        )

    return BudgetDecision(allowed=True)


def build_budget_status(
    workspace_id: str,
    kill_switch_enabled: bool,
    session: dict | None = None,
    request_estimated_cost_usd: float | None = None,
    daily_estimated_cost_usd: float | None = None,
    monthly_estimated_cost_usd: float | None = None,
) -> dict:
    status = {
        "workspaceId": workspace_id,
        "killSwitchEnabled": kill_switch_enabled,
    }
    if session:
        status["sessionId"] = session["id"]
        status["sessionEstimatedCostUsd"] = session["totalEstimatedCostUsd"]
        status["sessionRequestCount"] = session["requestCount"]
    if request_estimated_cost_usd is not None:
        status["requestEstimatedCostUsd"] = request_estimated_cost_usd
    if daily_estimated_cost_usd is not None:
        status["dailyEstimatedCostUsd"] = daily_estimated_cost_usd
    if monthly_estimated_cost_usd is not None:
        status["monthlyEstimatedCostUsd"] = monthly_estimated_cost_usd
    return status

