from io import BytesIO

import httpx
import pytest
from PIL import Image

from roomswipe_api.schemas import BoundingBox
from roomswipe_api.services.reference_images import ReferenceImageError, ReferenceImageService


def make_image_bytes() -> bytes:
    image = Image.new("RGB", (100, 80), color=(196, 156, 90))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


async def test_download_and_crop_returns_catalog_ready_jpeg() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "image/png"},
            content=make_image_bytes(),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        service = ReferenceImageService(http_client=http_client)
        image_bytes = await service.download("https://images.example.com/room.png")
        cropped = service.crop(
            image_bytes,
            BoundingBox(x=0.5, y=0.25, width=0.4, height=0.5),
        )

    assert cropped.content_type == "image/jpeg"
    assert len(cropped.data) > 50


async def test_download_rejects_oversized_images() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "image/png"},
            content=make_image_bytes(),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        service = ReferenceImageService(max_bytes=20, http_client=http_client)
        with pytest.raises(ReferenceImageError, match="too large"):
            await service.download("https://images.example.com/room.png")


async def test_download_rejects_non_image_content() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"not an image",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        service = ReferenceImageService(http_client=http_client)
        with pytest.raises(ReferenceImageError, match="unsupported content type"):
            await service.download("https://images.example.com/room.png")
