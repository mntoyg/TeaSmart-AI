"""Encoded-image fixtures shared by the backend tests."""

import io

from PIL import Image

# PNG cannot encode CMYK, so a CMYK fixture has to ride in a JPEG.
_FORMAT_FOR_MODE = {"CMYK": "JPEG"}


def make_test_image(
    *,
    size: tuple[int, int] = (64, 64),
    mode: str = "RGB",
    fmt: str = "PNG",
    colour: tuple[int, int, int] = (34, 139, 34),
    exif_orientation: int | None = None,
) -> bytes:
    """Return the encoded bytes of a solid test image."""
    image = Image.new("RGB", size, colour)
    if mode != "RGB":
        image = image.convert(mode)

    save_kwargs: dict[str, object] = {}
    if exif_orientation is not None:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation
        save_kwargs["exif"] = exif

    buffer = io.BytesIO()
    image.save(buffer, format=_FORMAT_FOR_MODE.get(mode, fmt), **save_kwargs)
    return buffer.getvalue()
