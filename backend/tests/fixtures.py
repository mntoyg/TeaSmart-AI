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
    band_colour: tuple[int, int, int] | None = None,
) -> bytes:
    """Return the encoded bytes of a test image.

    band_colour paints a stripe down the LEFT edge, which is what makes the
    image asymmetric enough to tell one rotation from another.
    """
    image = Image.new("RGB", size, colour)
    if band_colour is not None:
        width, height = size
        image.paste(band_colour, (0, 0, max(1, width // 8), height))
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
