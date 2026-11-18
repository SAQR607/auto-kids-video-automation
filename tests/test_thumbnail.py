"""Thumbnail redesign: title trim rule + close-up render smoke."""

from PIL import Image


def test_thumb_text_trims_title_to_four_words():
    from app.render.thumbnail import _thumb_text

    pkg = {"title": "What whispers from the glowing heart?"}
    assert _thumb_text(pkg, {}, {}) == "What whispers glowing heart"


def test_thumb_text_falls_back_below_two_words():
    from app.render.thumbnail import _thumb_text

    assert _thumb_text({}, {"text": "Big Day"}, {}) == "Big Day"
    assert _thumb_text({}, {}, {}) == "Fernwood Friends"


def test_render_thumbnail_is_jpeg_1280x720(tmp_path):
    from app.bench.reference import PACKAGE
    from app.config import load_config
    from app.render.thumbnail import render_thumbnail

    out = render_thumbnail(load_config(), PACKAGE, tmp_path / "thumb.jpg")
    with Image.open(out) as im:
        assert im.format == "JPEG"
        assert im.size == (1280, 720)
    assert out.stat().st_size < 2 * 1024 * 1024  # YouTube custom-thumb limit
