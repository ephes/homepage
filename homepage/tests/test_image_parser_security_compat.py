"""Exercise the image and JSON APIs used by the security-updated dependency stack."""

import bz2
from io import BytesIO

import pytest
from PIL import Image, ImageOps
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from willow.image import Image as WillowImage


@pytest.mark.parametrize("format_name", ["JPEG", "PNG", "WEBP", "GIF", "TIFF"])
def test_image_decode_resize_and_willow_conversion(format_name):
    encoded = BytesIO()
    Image.new("RGB", (80, 40), "navy").save(encoded, format=format_name)
    encoded.seek(0)
    with Image.open(encoded) as image:
        image.load()
        assert image.size == (80, 40)
        image.thumbnail((20, 20), Image.Resampling.LANCZOS)
        assert image.size == (20, 10)
    encoded.seek(0)
    converted = BytesIO()
    WillowImage.open(encoded).resize((20, 10)).save_as_jpeg(converted)
    converted.seek(0)
    with Image.open(converted) as image:
        assert image.size == (20, 10)
        assert image.format == "JPEG"


def test_exif_orientation_is_applied_and_removed():
    encoded = BytesIO()
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (80, 40), "navy").save(encoded, format="JPEG", exif=exif)
    encoded.seek(0)
    with Image.open(encoded) as image:
        oriented = ImageOps.exif_transpose(image)
        assert oriented.size == (40, 80)
        assert 274 not in oriented.getexif()


def test_json_parser_accepts_utf8():
    assert JSONParser().parse(BytesIO(b'{"value": 1}'), parser_context={"encoding": "utf-8"}) == {"value": 1}


def test_json_parser_rejects_binary_transform_charset():
    payload = bz2.compress(b'{"value": 1}')
    with pytest.raises(ParseError, match="Unsupported charset"):
        JSONParser().parse(BytesIO(payload), parser_context={"encoding": "bz2_codec"})
