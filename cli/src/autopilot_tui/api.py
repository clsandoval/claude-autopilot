"""Managed Agents REST client."""

from __future__ import annotations

import httpx

BASE_URL = "https://api.anthropic.com"
HEADERS = {
    "anthropic-version": "2023-06-01",
    "anthropic-beta": "managed-agents-2026-04-01",
}


class AutopilotAPI:
    def __init__(self, api_key: str, environment_id: str) -> None:
        self._environment_id = environment_id
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={**HEADERS, "x-api-key": api_key},
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def list_sessions(self) -> list[dict]:
        resp = await self._client.get("/v1/sessions")
        resp.raise_for_status()
        data = resp.json()
        sessions = data.get("data", data) if isinstance(data, dict) else data
        # Filter to our environment client-side
        return [
            s for s in sessions
            if s.get("environment_id") == self._environment_id
        ]

    async def get_session(self, session_id: str) -> dict:
        resp = await self._client.get(f"/v1/sessions/{session_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_events(
        self, session_id: str, after_event_id: str | None = None
    ) -> list[dict]:
        params: dict = {}
        if after_event_id:
            params["after_id"] = after_event_id
        resp = await self._client.get(
            f"/v1/sessions/{session_id}/events", params=params
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", data) if isinstance(data, dict) else data

    async def send_tool_result(
        self, session_id: str, tool_use_id: str, content: str
    ) -> dict:
        resp = await self._client.post(
            f"/v1/sessions/{session_id}/events",
            json={
                "events": [
                    {
                        "type": "user.custom_tool_result",
                        "custom_tool_use_id": tool_use_id,
                        "content": [{"type": "text", "text": content}],
                    }
                ]
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_session(self, session_id: str) -> None:
        resp = await self._client.delete(f"/v1/sessions/{session_id}")
        resp.raise_for_status()
