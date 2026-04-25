from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class CosmosService:
    def __init__(self) -> None:
        endpoint = os.getenv("COSMOS_ENDPOINT")
        key = os.getenv("COSMOS_KEY")
        self.database_name = os.getenv("COSMOS_DATABASE_NAME", "ai-budget-db")
        self.use_memory = not endpoint
        self._memory = {
            "workspaces": {},
            "sessions": {},
            "usageEvents": {},
            "killSwitch": {},
        }

        if not self.use_memory and key:
            credential = key or DefaultAzureCredential(
                managed_identity_client_id=os.getenv("AZURE_CLIENT_ID")
            )
            client = CosmosClient(endpoint, credential=credential)
            self.database = client.create_database_if_not_exists(self.database_name)
            self.containers = {
                name: self.database.create_container_if_not_exists(
                    id=name,
                    partition_key=PartitionKey(path="/workspaceId"),
                )
                for name in self._memory
            }
        elif not self.use_memory:
            credential = DefaultAzureCredential(managed_identity_client_id=os.getenv("AZURE_CLIENT_ID"))
            client = CosmosClient(endpoint, credential=credential)
            self.database = client.get_database_client(self.database_name)
            self.containers = {
                name: self.database.get_container_client(name)
                for name in self._memory
            }

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._read("workspaces", workspace_id, workspace_id)
        if workspace:
            return workspace

        now = utc_now()
        workspace = {
            "id": workspace_id,
            "workspaceId": workspace_id,
            "dailyBudgetUsd": float(os.getenv("DEFAULT_DAILY_BUDGET_USD", "5.00")),
            "monthlyBudgetUsd": float(os.getenv("DEFAULT_MONTHLY_BUDGET_USD", "30.00")),
            "sessionBudgetUsd": float(os.getenv("DEFAULT_SESSION_BUDGET_USD", "1.00")),
            "requestBudgetUsd": float(os.getenv("DEFAULT_REQUEST_BUDGET_USD", "0.05")),
            "maxRequestsPerSession": int(os.getenv("DEFAULT_MAX_REQUESTS_PER_SESSION", "20")),
            "maxOutputTokens": int(os.getenv("DEFAULT_MAX_OUTPUT_TOKENS", "500")),
            "createdAt": now,
            "updatedAt": now,
        }
        return self.upsert_workspace(workspace)

    def upsert_workspace(self, workspace: dict[str, Any]) -> dict[str, Any]:
        workspace["updatedAt"] = utc_now()
        return self._upsert("workspaces", workspace)

    def get_kill_switch(self, workspace_id: str) -> dict[str, Any]:
        kill_switch = self._read("killSwitch", "default", workspace_id)
        if kill_switch:
            return kill_switch

        kill_switch = {
            "id": "default",
            "workspaceId": workspace_id,
            "enabled": False,
            "reason": None,
            "updatedAt": utc_now(),
            "updatedBy": "system",
        }
        return self._upsert("killSwitch", kill_switch)

    def set_kill_switch(
        self,
        workspace_id: str,
        enabled: bool,
        reason: str | None,
        updated_by: str = "system",
    ) -> dict[str, Any]:
        kill_switch = {
            "id": "default",
            "workspaceId": workspace_id,
            "enabled": enabled,
            "reason": reason,
            "updatedAt": utc_now(),
            "updatedBy": updated_by,
        }
        return self._upsert("killSwitch", kill_switch)

    def get_or_create_session(self, workspace_id: str, session_id: str) -> dict[str, Any]:
        session = self._read("sessions", session_id, workspace_id)
        if session:
            return session

        now = utc_now()
        session = {
            "id": session_id,
            "workspaceId": workspace_id,
            "totalPromptTokens": 0,
            "totalCompletionTokens": 0,
            "totalTokens": 0,
            "totalEstimatedCostUsd": 0.0,
            "requestCount": 0,
            "status": "active",
            "createdAt": now,
            "updatedAt": now,
        }
        return self._upsert("sessions", session)

    def record_usage_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event.setdefault("createdAt", utc_now())
        return self._upsert("usageEvents", event)

    def update_session_usage(
        self,
        workspace_id: str,
        session_id: str,
        usage: dict[str, Any],
    ) -> dict[str, Any]:
        session = self.get_or_create_session(workspace_id, session_id)
        session["totalPromptTokens"] += int(usage.get("promptTokens", 0))
        session["totalCompletionTokens"] += int(usage.get("completionTokens", 0))
        session["totalTokens"] += int(usage.get("totalTokens", 0))
        session["totalEstimatedCostUsd"] = round(
            float(session["totalEstimatedCostUsd"]) + float(usage.get("estimatedCostUsd", 0.0)),
            6,
        )
        session["requestCount"] += 1
        session["updatedAt"] = utc_now()
        return self._upsert("sessions", session)

    def get_workspace_usage_total(self, workspace_id: str, period: str) -> float:
        now = datetime.now(UTC)
        if period == "daily":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "monthly":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now - timedelta(days=3650)

        if self.use_memory:
            events = self._memory["usageEvents"].values()
            total = sum(
                float(event.get("estimatedCostUsd", 0.0))
                for event in events
                if event.get("workspaceId") == workspace_id
                and _parse_time(event.get("createdAt")) >= start
            )
            return round(total, 6)

        query = (
            "SELECT VALUE SUM(c.estimatedCostUsd) FROM c "
            "WHERE c.workspaceId = @workspaceId AND c.createdAt >= @start"
        )
        values = list(
            self.containers["usageEvents"].query_items(
                query=query,
                parameters=[
                    {"name": "@workspaceId", "value": workspace_id},
                    {"name": "@start", "value": start.isoformat().replace("+00:00", "Z")},
                ],
                partition_key=workspace_id,
            )
        )
        return round(float(values[0] or 0.0), 6)

    def reset_demo_budget(self, workspace_id: str) -> None:
        self.set_kill_switch(workspace_id, False, None, "admin")
        if self.use_memory:
            self._memory["sessions"] = {
                key: value
                for key, value in self._memory["sessions"].items()
                if value.get("workspaceId") != workspace_id
            }
            self._memory["usageEvents"] = {
                key: value
                for key, value in self._memory["usageEvents"].items()
                if value.get("workspaceId") != workspace_id
            }
            return

        for container_name in ("sessions", "usageEvents"):
            container = self.containers[container_name]
            items = list(
                container.query_items(
                    query="SELECT c.id FROM c WHERE c.workspaceId = @workspaceId",
                    parameters=[{"name": "@workspaceId", "value": workspace_id}],
                    partition_key=workspace_id,
                )
            )
            for item in items:
                container.delete_item(item=item["id"], partition_key=workspace_id)

    def _read(self, container_name: str, item_id: str, workspace_id: str) -> dict[str, Any] | None:
        if self.use_memory:
            return self._memory[container_name].get(f"{workspace_id}:{item_id}")

        try:
            return self.containers[container_name].read_item(
                item=item_id,
                partition_key=workspace_id,
            )
        except CosmosResourceNotFoundError:
            return None

    def _upsert(self, container_name: str, item: dict[str, Any]) -> dict[str, Any]:
        if self.use_memory:
            key = f"{item['workspaceId']}:{item['id']}"
            self._memory[container_name][key] = item
            return item

        return self.containers[container_name].upsert_item(item)


def _parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
