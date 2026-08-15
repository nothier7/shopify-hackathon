import json

import httpx
import pytest

from roomswipe_api.services.shopify_mcp import ShopifyMcpClient, ShopifyMcpError

PROFILE_URL = "https://agent.example.com/profile.json"
ENDPOINT = "https://catalog.shopify.com/api/ucp/mcp"


async def test_call_tool_adds_profile_and_returns_structured_content() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["jsonrpc"] == "2.0"
        assert body["method"] == "tools/call"
        assert body["params"]["name"] == "search_catalog"
        assert body["params"]["arguments"]["meta"] == {
            "ucp-agent": {"profile": PROFILE_URL}
        }
        assert body["params"]["arguments"]["catalog"]["query"] == "brass lamp"
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {"structuredContent": {"products": []}},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ShopifyMcpClient(
            agent_profile_url=PROFILE_URL,
            http_client=http_client,
        )
        result = await client.call_tool(
            endpoint=ENDPOINT,
            name="search_catalog",
            arguments={"catalog": {"query": "brass lamp"}},
        )

    assert result == {"products": []}


async def test_call_tool_converts_mcp_tool_errors() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "result": {
                    "isError": True,
                    "content": [{"type": "text", "text": "Invalid catalog filters"}],
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ShopifyMcpClient(
            agent_profile_url=PROFILE_URL,
            http_client=http_client,
        )
        with pytest.raises(ShopifyMcpError, match="Invalid catalog filters"):
            await client.call_tool(
                endpoint=ENDPOINT,
                name="search_catalog",
                arguments={"catalog": {"query": "lamp"}},
            )


async def test_call_tool_hides_upstream_response_body_on_http_failure() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="private upstream details")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = ShopifyMcpClient(
            agent_profile_url=PROFILE_URL,
            http_client=http_client,
        )
        with pytest.raises(ShopifyMcpError, match="HTTP 503") as error:
            await client.call_tool(
                endpoint=ENDPOINT,
                name="search_catalog",
                arguments={"catalog": {"query": "lamp"}},
            )

    assert "private upstream details" not in error.value.detail
