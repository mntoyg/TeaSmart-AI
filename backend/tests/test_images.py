import io

import numpy
import pytest
from PIL import Image

from app.core.config import get_settings
from app.core.images import (
    CorruptImageError,
    ImageTooLargeError,
    UnsupportedImageError,
    decode_image,
)
from tests.fixtures import make_test_image

_SETTINGS = get_settings()
CAPS = dict(
    max_bytes=_SETTINGS.max_upload_bytes, max_pixels=_SETTINGS.max_image_pixels
)


def test_rejects_a_text_file_renamed_as_an_image():
    with pytest.raises(UnsupportedImageError):
        decode_image(b"#!/bin/sh\necho pwned\n", **CAPS)


def test_rejects_a_zip_polyglot():
    with pytest.raises(UnsupportedImageError):
        decode_image(b"PK\x03\x04" + b"\x00" * 64, **CAPS)


def test_rejects_payload_over_the_byte_cap():
    with pytest.raises(ImageTooLargeError):
        decode_image(make_test_image(size=(64, 64)), max_bytes=10, max_pixels=40000000)


def test_rejects_a_decompression_bomb_within_the_byte_cap():
    bomb = make_test_image(size=(7000, 7000), mode="L", colour=(0, 0, 0))
    assert len(bomb) < CAPS["max_bytes"]
    with pytest.raises(ImageTooLargeError):
        decode_image(bomb, **CAPS)


def test_rejects_a_truncated_jpeg():
    data = make_test_image(size=(256, 256), fmt="JPEG")
    with pytest.raises(CorruptImageError):
        decode_image(data[: len(data) // 3], **CAPS)


@pytest.mark.parametrize("mode", ["L", "RGBA", "P", "CMYK"])
def test_every_colour_mode_decodes_to_three_channel_rgb(mode):
    image = decode_image(make_test_image(size=(32, 48), mode=mode), **CAPS)
    assert image.shape == (48, 32, 3)
    assert image.dtype == numpy.uint8


def test_applies_exif_orientation():
    # A 64x32 landscape JPEG tagged Orientation=6 must come back 32 wide by 64 tall.
    image = decode_image(
        make_test_image(size=(64, 32), fmt="JPEG", exif_orientation=6), **CAPS
    )
    assert image.shape[:2] == (64, 32)


def test_strips_exif_so_no_metadata_survives():
    data = make_test_image(size=(32, 32), fmt="JPEG", exif_orientation=6)
    assert Image.open(io.BytesIO(data)).getexif()
    decoded = decode_image(data, **CAPS)
    assert isinstance(decoded, numpy.ndarray)


def test_exif_orientation_rotates_the_right_way_not_merely_some_way():
    # Orientation 6 means "rotate 90 degrees clockwise to display", so a stripe on
    # the left edge has to land on the top edge. A shape-only assertion cannot
    # tell orientation 6 from orientation 8, which turns the other way, and a
    # frame rotated backwards puts every later crop and lesion measurement in the
    # wrong place.
    decoded = decode_image(
        make_test_image(
            size=(64, 32), fmt="JPEG", exif_orientation=6, band_colour=(200, 20, 20)
        ),
        **CAPS,
    )
    assert decoded.shape[:2] == (64, 32)
    top = decoded[:4, :, :].reshape(-1, 3).mean(axis=0)
    bottom = decoded[-4:, :, :].reshape(-1, 3).mean(axis=0)
    assert top[0] > top[1], "the red stripe should be at the top after rotation"
    assert bottom[1] > bottom[0], "the green body should be at the bottom"
