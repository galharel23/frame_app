import os
from PIL import Image, ImageDraw

from image_to_json_generator import _compute_blur_score, _classify_image_quality


def _create_checkerboard_image(path):
    img = Image.new("RGB", (320, 320), "white")
    draw = ImageDraw.Draw(img)
    step = 20
    for y in range(0, 320, step):
        for x in range(0, 320, step):
            if (x // step + y // step) % 2 == 0:
                draw.rectangle([x, y, x + step - 1, y + step - 1], fill="black")
    img.save(path)


def _create_blurry_image(path):
    img = Image.new("RGB", (320, 320), "gray")
    img.save(path)


def test_compute_blur_score_distinguishes_sharp_and_blurry_images(tmp_path):
    sharp_path = tmp_path / "sharp.jpg"
    blurry_path = tmp_path / "blurry.jpg"

    _create_checkerboard_image(str(sharp_path))
    _create_blurry_image(str(blurry_path))

    sharp_score = _compute_blur_score(str(sharp_path))
    blurry_score = _compute_blur_score(str(blurry_path))

    assert sharp_score > blurry_score
    assert sharp_score >= 1.0
    assert blurry_score >= 0.0


def test_classify_image_quality_marks_blurred_or_low_altitude_as_bad(tmp_path):
    image_path = tmp_path / "test_T.JPG"
    _create_blurry_image(str(image_path))

    quality_config = {
        "blur_threshold": 50.0,
        "min_relative_altitude": 5.0,
        "max_relative_altitude": 500.0,
        "allow_thermal": True,
        "allow_visible": True,
    }
    classification, quality_data = _classify_image_quality(
        filename="test_T.JPG",
        full_path=str(image_path),
        tags={},
        relative_alt=1.0,
        los_fields={"losAzimuth": 0.0, "losPitch": 0.0, "losRoll": 0.0},
        session_dir=str(tmp_path),
        quality_config=quality_config,
    )

    assert classification == "bad"
    assert "blurred image" in quality_data["reasons"] or "missing critical flight metadata" in quality_data["reasons"]
    assert quality_data["sensorType"] == "IR"
