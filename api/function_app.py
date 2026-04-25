from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

import azure.functions as func

from services.ai_service import AiService
from services.budget_service import (
    build_budget_status,
    check_request_budget,
    check_session_budget,
    check_workspace_budget,
)
from services.cosmos_service import CosmosService, utc_now
from services.cost_calculator import CostCalculator

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

cosmos = CosmosService()
costs = CostCalculator()
ai = AiService()


@app.route(route="health", methods=["GET", "OPTIONS"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return empty_cors_response()

    return json_response(
        {
            "ok": True,
            "service": "demo-ai-budget-guardrails-api",
            "cosmosMode": "memory" if cosmos.use_memory else "cosmos",
        }
    )


@app.route(route="chat", methods=["POST", "OPTIONS"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return empty_cors_response()

    unauthorized = require_api_key(req)
    if unauthorized:
        return unauthorized

    request_id = str(uuid.uuid4())

    try:
        body = req.get_json()
    except ValueError:
        return json_response({"allowed": False, "reason": "Request body must be valid JSON."}, 400)

    workspace_id = str(body.get("workspaceId") or os.getenv("DEFAULT_WORKSPACE_ID", "demo-workspace"))
    session_id = str(body.get("sessionId") or f"session-{uuid.uuid4()}")
    message = str(body.get("message") or "").strip()

    if not message:
        return json_response({"allowed": False, "reason": "message is required."}, 400)

    logging.info(
        "chat request received requestId=%s workspaceId=%s sessionId=%s",
        request_id,
        workspace_id,
        session_id,
    )

    workspace = cosmos.get_workspace(workspace_id)
    kill_switch = cosmos.get_kill_switch(workspace_id)
    if kill_switch["enabled"]:
        return json_response(
            {
                "allowed": False,
                "reason": "Workspace budget exceeded. AI calls are temporarily disabled.",
                "budget": build_budget_status(workspace_id, True),
            },
            200,
        )

    session = cosmos.get_or_create_session(workspace_id, session_id)
    session_decision = check_session_budget(workspace, session)
    if not session_decision.allowed:
        return blocked_response(workspace_id, session_decision.reason, session=session)

    daily_total = cosmos.get_workspace_usage_total(workspace_id, "daily")
    monthly_total = cosmos.get_workspace_usage_total(workspace_id, "monthly")
    workspace_decision = check_workspace_budget(workspace, daily_total, monthly_total)
    if not workspace_decision.allowed:
        cosmos.set_kill_switch(workspace_id, True, workspace_decision.reason)
        return blocked_response(workspace_id, workspace_decision.reason, session=session, kill_switch=True)

    max_output_tokens = int(workspace.get("maxOutputTokens") or os.getenv("DEFAULT_MAX_OUTPUT_TOKENS", "500"))
    prompt_tokens_estimate = costs.estimate_prompt_tokens(message)
    estimated_request_cost = costs.estimate_cost_usd(prompt_tokens_estimate, max_output_tokens)
    request_decision = check_request_budget(workspace, estimated_request_cost)
    if not request_decision.allowed:
        return blocked_response(
            workspace_id,
            request_decision.reason,
            session=session,
            request_estimated_cost_usd=estimated_request_cost,
        )

    try:
        result = ai.send_chat_message(message, max_output_tokens)
    except Exception:
        logging.exception(
            "AI call failed requestId=%s workspaceId=%s sessionId=%s",
            request_id,
            workspace_id,
            session_id,
        )
        return json_response({"allowed": False, "reason": "AI service call failed."}, 502)

    actual_request_cost = costs.estimate_cost_usd(result.prompt_tokens, result.completion_tokens)
    usage = {
        "id": f"event-{uuid.uuid4()}",
        "workspaceId": workspace_id,
        "sessionId": session_id,
        "requestId": request_id,
        "model": result.model,
        "promptTokens": result.prompt_tokens,
        "completionTokens": result.completion_tokens,
        "totalTokens": result.total_tokens,
        "estimatedCostUsd": actual_request_cost,
        "createdAt": utc_now(),
    }
    cosmos.record_usage_event(usage)
    session = cosmos.update_session_usage(workspace_id, session_id, usage)

    daily_total = cosmos.get_workspace_usage_total(workspace_id, "daily")
    monthly_total = cosmos.get_workspace_usage_total(workspace_id, "monthly")
    warning = None
    workspace_decision = check_workspace_budget(workspace, daily_total, monthly_total)
    if not workspace_decision.allowed:
        cosmos.set_kill_switch(workspace_id, True, workspace_decision.reason)
        warning = "Workspace budget exceeded. Kill switch has been enabled for future requests."

    response: dict[str, Any] = {
        "allowed": True,
        "message": result.text,
        "budget": build_budget_status(
            workspace_id,
            kill_switch_enabled=warning is not None,
            session=session,
            request_estimated_cost_usd=actual_request_cost,
            daily_estimated_cost_usd=daily_total,
            monthly_estimated_cost_usd=monthly_total,
        ),
    }
    if warning:
        response["warning"] = warning

    logging.info(
        "chat request completed requestId=%s workspaceId=%s sessionId=%s totalTokens=%s estimatedCostUsd=%s",
        request_id,
        workspace_id,
        session_id,
        result.total_tokens,
        actual_request_cost,
    )
    return json_response(response)


@app.route(route="admin/status", methods=["GET", "OPTIONS"])
def admin_status(req: func.HttpRequest) -> func.HttpResponse:
    return build_status_response(req)


@app.route(route="status", methods=["GET", "OPTIONS"])
def status(req: func.HttpRequest) -> func.HttpResponse:
    return build_status_response(req)


def build_status_response(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return empty_cors_response()

    unauthorized = require_api_key(req)
    if unauthorized:
        return unauthorized

    workspace_id = req.params.get("workspaceId") or os.getenv("DEFAULT_WORKSPACE_ID", "demo-workspace")
    workspace = cosmos.get_workspace(workspace_id)
    kill_switch = cosmos.get_kill_switch(workspace_id)
    return json_response(
        {
            "workspace": workspace,
            "killSwitch": kill_switch,
            "dailyEstimatedCostUsd": cosmos.get_workspace_usage_total(workspace_id, "daily"),
            "monthlyEstimatedCostUsd": cosmos.get_workspace_usage_total(workspace_id, "monthly"),
            "fakeAiEnabled": os.getenv("USE_FAKE_AI", "true").lower() == "true",
            "cosmosMode": "memory" if cosmos.use_memory else "cosmos",
        }
    )


@app.route(route="admin/kill-switch/enable", methods=["POST", "OPTIONS"])
def enable_kill_switch(req: func.HttpRequest) -> func.HttpResponse:
    return build_enable_kill_switch_response(req)


@app.route(route="kill-switch/enable", methods=["POST", "OPTIONS"])
def enable_kill_switch_alias(req: func.HttpRequest) -> func.HttpResponse:
    return build_enable_kill_switch_response(req)


def build_enable_kill_switch_response(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return empty_cors_response()

    unauthorized = require_admin_key(req)
    if unauthorized:
        return unauthorized

    body = get_json_or_empty(req)
    workspace_id = str(body.get("workspaceId") or os.getenv("DEFAULT_WORKSPACE_ID", "demo-workspace"))
    reason = str(body.get("reason") or "Manual kill switch enabled.")
    kill_switch = cosmos.set_kill_switch(workspace_id, True, reason, "admin")
    return json_response({"killSwitch": kill_switch})


@app.route(route="admin/kill-switch/disable", methods=["POST", "OPTIONS"])
def disable_kill_switch(req: func.HttpRequest) -> func.HttpResponse:
    return build_disable_kill_switch_response(req)


@app.route(route="kill-switch/disable", methods=["POST", "OPTIONS"])
def disable_kill_switch_alias(req: func.HttpRequest) -> func.HttpResponse:
    return build_disable_kill_switch_response(req)


def build_disable_kill_switch_response(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return empty_cors_response()

    unauthorized = require_admin_key(req)
    if unauthorized:
        return unauthorized

    body = get_json_or_empty(req)
    workspace_id = str(body.get("workspaceId") or os.getenv("DEFAULT_WORKSPACE_ID", "demo-workspace"))
    kill_switch = cosmos.set_kill_switch(workspace_id, False, None, "admin")
    return json_response({"killSwitch": kill_switch})


@app.route(route="admin/budget/reset-demo", methods=["POST", "OPTIONS"])
def reset_demo_budget(req: func.HttpRequest) -> func.HttpResponse:
    return build_reset_demo_budget_response(req)


@app.route(route="budget/reset-demo", methods=["POST", "OPTIONS"])
def reset_demo_budget_alias(req: func.HttpRequest) -> func.HttpResponse:
    return build_reset_demo_budget_response(req)


def build_reset_demo_budget_response(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return empty_cors_response()

    unauthorized = require_admin_key(req)
    if unauthorized:
        return unauthorized

    body = get_json_or_empty(req)
    workspace_id = str(body.get("workspaceId") or os.getenv("DEFAULT_WORKSPACE_ID", "demo-workspace"))
    cosmos.get_workspace(workspace_id)
    cosmos.reset_demo_budget(workspace_id)
    return json_response({"reset": True, "workspaceId": workspace_id})


@app.route(route="admin/budget/configure-demo", methods=["POST", "OPTIONS"])
def configure_demo_budget(req: func.HttpRequest) -> func.HttpResponse:
    return build_configure_demo_budget_response(req)


@app.route(route="budget/configure-demo", methods=["POST", "OPTIONS"])
def configure_demo_budget_alias(req: func.HttpRequest) -> func.HttpResponse:
    return build_configure_demo_budget_response(req)


def build_configure_demo_budget_response(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return empty_cors_response()

    unauthorized = require_admin_key(req)
    if unauthorized:
        return unauthorized

    body = get_json_or_empty(req)
    workspace_id = str(body.get("workspaceId") or os.getenv("DEFAULT_WORKSPACE_ID", "demo-workspace"))
    workspace = cosmos.get_workspace(workspace_id)

    number_fields = {
        "dailyBudgetUsd",
        "monthlyBudgetUsd",
        "sessionBudgetUsd",
        "requestBudgetUsd",
    }
    integer_fields = {
        "maxRequestsPerSession",
        "maxOutputTokens",
    }

    for field in number_fields:
        if field in body:
            value = float(body[field])
            if value < 0:
                return json_response({"error": f"{field} must be greater than or equal to 0."}, 400)
            workspace[field] = value

    for field in integer_fields:
        if field in body:
            value = int(body[field])
            if value < 1:
                return json_response({"error": f"{field} must be greater than or equal to 1."}, 400)
            workspace[field] = value

    workspace = cosmos.upsert_workspace(workspace)
    kill_switch = cosmos.set_kill_switch(workspace_id, False, None, "admin")
    return json_response({"workspace": workspace, "killSwitch": kill_switch})


def blocked_response(
    workspace_id: str,
    reason: str | None,
    session: dict | None = None,
    kill_switch: bool = False,
    request_estimated_cost_usd: float | None = None,
) -> func.HttpResponse:
    return json_response(
        {
            "allowed": False,
            "reason": reason or "Request blocked by budget guardrails.",
            "budget": build_budget_status(
                workspace_id,
                kill_switch_enabled=kill_switch,
                session=session,
                request_estimated_cost_usd=request_estimated_cost_usd,
            ),
        }
    )


def require_admin_key(req: func.HttpRequest) -> func.HttpResponse | None:
    return require_api_key(req)


def require_api_key(req: func.HttpRequest) -> func.HttpResponse | None:
    expected = os.getenv("ADMIN_API_KEY")
    if not expected:
        return None

    actual = req.headers.get("x-admin-api-key")
    if actual != expected:
        return json_response({"error": "Unauthorized."}, 401)

    return None


def get_json_or_empty(req: func.HttpRequest) -> dict[str, Any]:
    try:
        return req.get_json()
    except ValueError:
        return {}


def json_response(body: dict[str, Any], status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body),
        status_code=status_code,
        mimetype="application/json",
        headers=cors_headers(),
    )


def empty_cors_response() -> func.HttpResponse:
    return func.HttpResponse("", status_code=204, headers=cors_headers())


def cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": os.getenv("CORS_ALLOWED_ORIGIN", "*"),
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,x-admin-api-key",
    }
