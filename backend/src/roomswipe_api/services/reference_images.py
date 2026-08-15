"""Download a generated room once and extract visual search references."""

from base64 import b64encode
from dataclasses import dataclass
from io import BytesIO

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

from roomswipe_api.schemas import BoundingBox


class ReferenceImageError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class EncodedImage:
    content_type: str
    data: str


class ReferenceImageService:
    def __init__(
        self,
        *,
        max_bytes: int = 10_000_000,
        timeout_seconds: float = 20,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.max_bytes = max_bytes
        self._client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = http_client is None

    async def download(self, image_url: str) -> bytes:
        if not image_url.startswith(("https://", "http://")):
            raise ReferenceImageError("final image URL must use HTTP or HTTPS")

        try:
            response = await self._client.get(image_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ReferenceImageError("could not download the final room image") from exc

        content_type = response.headers.get("content-type", "").partition(";")[0]
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise ReferenceImageError("final room image has an unsupported content type")
        if len(response.content) > self.max_bytes:
            raise ReferenceImageError("final room image is too large")
        return response.content

    def crop(self, image_bytes: bytes, bounding_box: BoundingBox) -> EncodedImage:
        try:
            with Image.open(BytesIO(image_bytes)) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
        except (UnidentifiedImageError, OSError) as exc:
            raise ReferenceImageError("final room image could not be decoded") from exc

        left = round(bounding_box.x * image.width)
        top = round(bounding_box.y * image.height)
        right = round((bounding_box.x + bounding_box.width) * image.width)
        bottom = round((bounding_box.y + bounding_box.height) * image.height)
        cropped = image.crop((left, top, right, bottom))

        output = BytesIO()
        cropped.save(output, format="JPEG", quality=88, optimize=True)
        return EncodedImage(
            content_type="image/jpeg",
            data=b64encode(output.getvalue()).decode("ascii"),
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
