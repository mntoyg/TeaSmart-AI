"""Hardened decoding of untrusted uploaded images.

This is the only door images from outside enter through, so every later stage
may assume what this module guarantees: a C-contiguous uint8 RGB array,
upright, with no metadata attached.
"""

import io

import numpy
from PIL import Image, ImageOps, UnidentifiedImageError

SUPPORTED_MIME = frozenset({"image/jpeg", "image/png", "image/webp"})

_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)


class ImageLoadError(Exception):
    """Base class for every rejection this module makes."""


class UnsupportedImageError(ImageLoadError):
    """The payload is not an image format we accept."""


class ImageTooLargeError(ImageLoadError):
    """The payload exceeds the byte cap or the pixel cap."""


class CorruptImageError(ImageLoadError):
    """The payload claims to be an image but cannot be decoded."""


def sniff_mime(data: bytes) -> str | None:
    """Identify the format from magic bytes alone.

    The client-declared content type and the filename are never consulted: both
    are attacker-controlled.
    """
    for magic, mime in _MAGIC:
        if data.startswith(magic):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def decode_image(data: bytes, *, max_bytes: int, max_pixels: int) -> numpy.ndarray:
    """Decode an untrusted payload into an upright RGB array, or reject it."""
    if len(data) > max_bytes:
        raise ImageTooLargeError(f"upload is {len(data)} bytes, cap is {max_bytes}")

    if sniff_mime(data) not in SUPPORTED_MIME:
        raise UnsupportedImageError("payload is not a JPEG, PNG or WebP image")

    try:
        with Image.open(io.BytesIO(data)) as opened:
            # Pillow reads the header lazily, so the dimensions are known before
            # any pixel memory is committed. Reject a decompression bomb here,
            # rather than after allocating gigabytes to decode it.
            width, height = opened.size
            if width * height > max_pixels:
                raise ImageTooLargeError(
                    f"image is {width}x{height} pixels, cap is {max_pixels}"
                )
            rgb = ImageOps.exif_transpose(opened).convert("RGB")
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageTooLargeError(str(exc)) from exc
    except UnidentifiedImageError as exc:
        raise CorruptImageError("image could not be decoded") from exc
    except OSError as exc:
        raise CorruptImageError("image data is truncated or corrupt") from exc

    # Re-reading the pixels into a fresh array is what strips EXIF, colour
    # profiles and any other embedded payload: only pixels survive this call.
    return numpy.ascontiguousarray(numpy.asarray(rgb, dtype=numpy.uint8))
