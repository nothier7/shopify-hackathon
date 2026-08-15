"""Small JSON-RPC client for Shopify's MCP-over-HTTP endpoints."""

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import httpx


class ShopifyMcpError(RuntimeError):
    def __init__(self, detail: str, *, code: int | str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code


class ShopifyMcpClient:
    def __init__(
        self,
        *,
        agent_profile_url: str,
        timeout_seconds: float = 20,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not agent_profile_url:
            raise ValueError("Shopify agent profile URL is required")

        self.agent_profile_url = agent_profile_url
        self._client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = http_client is None

    async def call_tool(
        self,
        *,
        endpoint: str,
        name: str,
        arguments: Mapping[str, Any],
    ) -> dict[str, Any]:
        existing_meta = arguments.get("meta")
        meta = dict(existing_meta) if isinstance(existing_meta, Mapping) else {}
        meta["ucp-agent"] = {"profile": self.agent_profile_url}
        request_arguments = {**arguments, "meta": meta}
        request_id = str(uuid4())

        try:
            response = await self._client.post(
                endpoint,
                json={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": request_arguments},
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise ShopifyMcpError(
                f"Shopify MCP returned HTTP {exc.response.status_code}"
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ShopifyMcpError("Shopify MCP request failed") from exc

        if not isinstance(payload, dict):
            raise ShopifyMcpError("Shopify MCP returned an invalid JSON-RPC response")

        error = payload.get("error")
        if isinstance(error, dict):
            raise ShopifyMcpError(
                str(error.get("message", "Shopify MCP tool call failed")),
                code=error.get("code"),
            )

        result = payload.get("result")
        if not isinstance(result, dict):
            raise ShopifyMcpError("Shopify MCP response is missing a result")
        if result.get("isError"):
            raise ShopifyMcpError(self._tool_error_detail(result))

        structured_content = result.get("structuredContent")
        if not isinstance(structured_content, dict):
            raise ShopifyMcpError("Shopify MCP response is missing structured content")
        return structured_content

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @staticmethod
    def _tool_error_detail(result: Mapping[str, Any]) -> str:
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    return item["text"]
        return "Shopify MCP tool call failed"
