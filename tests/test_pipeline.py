"""
Test suite for the image processing pipeline.

Tests cover:
- Image file detection and filtering
- Session directory creation
- Image gathering from directories
- JSON metadata gathering
- Pipeline execution and output structure
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from utils.pipeline import (
    IMAGE_EXT,
    _create_session_dir,
    _gather_images_in_dir,
    _gather_main_jsons,
    _image_name_from_json,
    _is_image,
    run_whitening,
)


class TestIsImage:
    """Test image file detection based on extensions."""

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("photo.jpg", True),
            ("photo.JPG", True),
            ("photo.jpeg", True),
            ("photo.JPEG", True),
            ("photo.png", True),
            ("photo.PNG", True),
            ("photo.tif", True),
            ("photo.tiff", True),
            ("photo.bmp", True),
            ("photo.gif", True),
            ("document.pdf", False),
            ("document.txt", False),
            ("video.mp4", False),
            ("script.py", False),
            ("config.json", False),
            ("image.jpg.bak", False),
        ],
    )
    def test_is_image_with_various_extensions(self, filename, expected):
        """Test that image extensions are correctly identified."""
        result = _is_image(filename)
        assert result == expected

    def test_is_image_case_insensitive(self):
        """Test that extension checking is case-insensitive."""
        assert _is_image("photo.JpG") is True
        assert _is_image("photo.jpEG") is True
        assert _is_image("photo.PNG") is True

    def test_is_image_with_full_path(self):
        """Test image detection with full file paths."""
        assert _is_image("/path/to/photo.jpg") is True
        assert _is_image("C:\\Users\\user\\photo.jpg") is True
        assert _is_image("/path/to/document.pdf") is False


class TestGatherImagesInDir:
    """Test recursive image gathering from directories."""

    def test_gather_images_empty_directory(self):
        """Test gathering from an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _gather_images_in_dir(tmpdir)
            assert result == []

    def test_gather_images_flat_directory(self):
        """Test gathering images from a flat directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test images
            img1 = Path(tmpdir) / "photo1.jpg"
            img2 = Path(tmpdir) / "photo2.png"
            non_img = Path(tmpdir) / "document.txt"

            img1.touch()
            img2.touch()
            non_img.touch()

            result = _gather_images_in_dir(tmpdir)

            assert len(result) == 2
            assert str(img1) in result
            assert str(img2) in result
            assert str(non_img) not in result

    def test_gather_images_nested_directories(self):
        """Test gathering images from nested directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            subdir = Path(tmpdir) / "subfolder"
            subdir.mkdir()

            img1 = Path(tmpdir) / "photo1.jpg"
            img2 = subdir / "photo2.jpg"
            non_img = subdir / "document.txt"

            img1.touch()
            img2.touch()
            non_img.touch()

            result = _gather_images_in_dir(tmpdir)

            assert len(result) == 2
            assert str(img1) in result
            assert str(img2) in result
            assert str(non_img) not in result

    def test_gather_images_multiple_levels(self):
        """Test gathering from multiple nesting levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create deep nesting
            level1 = Path(tmpdir) / "level1"
            level2 = level1 / "level2"
            level2.mkdir(parents=True)

            img1 = Path(tmpdir) / "photo1.jpg"
            img2 = level1 / "photo2.jpg"
            img3 = level2 / "photo3.jpg"

            img1.touch()
            img2.touch()
            img3.touch()

            result = _gather_images_in_dir(tmpdir)

            assert len(result) == 3
            assert all(img in result for img in [str(img1), str(img2), str(img3)])

    def test_gather_images_various_formats(self):
        """Test gathering with various image formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            formats = ["jpg", "jpeg", "png", "tif", "tiff", "bmp", "gif"]

            for fmt in formats:
                (Path(tmpdir) / f"photo.{fmt}").touch()

            result = _gather_images_in_dir(tmpdir)
            assert len(result) == len(formats)

    def test_gather_images_case_insensitive(self):
        """Test that gathered images work with various case formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "photo.JPG").touch()
            (Path(tmpdir) / "photo.Png").touch()
            (Path(tmpdir) / "photo.TIFF").touch()

            result = _gather_images_in_dir(tmpdir)
            assert len(result) == 3


class TestCreateSessionDir:
    """Test session directory creation."""

    def test_create_session_dir_returns_two_values(self):
        """Test that session creation returns directory path and name."""
        session_dir, session_name = _create_session_dir()

        assert isinstance(session_dir, str)
        assert isinstance(session_name, str)
        assert len(session_name) > 0

    def test_create_session_dir_exists(self):
        """Test that created session directory actually exists."""
        session_dir, _ = _create_session_dir()

        try:
            assert os.path.isdir(session_dir)
            assert os.access(session_dir, os.W_OK)
        finally:
            shutil.rmtree(session_dir, ignore_errors=True)

    def test_create_session_dir_name_format(self):
        """Test that session directory name follows expected format (YYYYMMDD_HHMMSS)."""
        session_dir, session_name = _create_session_dir()

        try:
            # Should be format: YYYYMMDD_HHMMSS
            parts = session_name.split("_")
            assert len(parts) == 2
            assert len(parts[0]) == 8  # YYYYMMDD
            assert len(parts[1]) == 6  # HHMMSS
            assert parts[0].isdigit()
            assert parts[1].isdigit()
        finally:
            shutil.rmtree(session_dir, ignore_errors=True)

    def test_create_session_dir_in_temp(self):
        """Test that session directories are created in system temp."""
        session_dir, _ = _create_session_dir()

        try:
            assert tempfile.gettempdir() in session_dir
            assert "whitening_" in session_dir
        finally:
            shutil.rmtree(session_dir, ignore_errors=True)

    def test_create_session_dir_unique(self):
        """Test that multiple session directories have unique names."""
        import time

        session_dir1, name1 = _create_session_dir()
        time.sleep(1.1)  # Wait for at least one second to ensure different timestamp
        session_dir2, name2 = _create_session_dir()

        try:
            assert name1 != name2
            assert session_dir1 != session_dir2
        finally:
            shutil.rmtree(session_dir1, ignore_errors=True)
            shutil.rmtree(session_dir2, ignore_errors=True)


class TestGatherMainJsons:
    """Test JSON file gathering from processed output."""

    def test_gather_main_jsons_empty_directory(self):
        """Test gathering from empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _gather_main_jsons(tmpdir)
            assert result == []

    def test_gather_main_jsons_flat_structure(self):
        """Test gathering JSON files from flat directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create JSON files
            json1 = Path(tmpdir) / "image1.json"
            json2 = Path(tmpdir) / "image2.json"
            other = Path(tmpdir) / "config.txt"

            json1.touch()
            json2.touch()
            other.touch()

            result = _gather_main_jsons(tmpdir)

            assert len(result) == 2
            assert str(json1) in result
            assert str(json2) in result

    def test_gather_main_jsons_skips_all_metadata(self):
        """Test that _all_metadata_file.json files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json1 = Path(tmpdir) / "image1.json"
            metadata_all = Path(tmpdir) / "image1_all_metadata_file.json"

            json1.touch()
            metadata_all.touch()

            result = _gather_main_jsons(tmpdir)

            assert len(result) == 1
            assert str(json1) in result
            assert str(metadata_all) not in result

    def test_gather_main_jsons_nested_structure(self):
        """Test gathering from nested directory structure (per-image folders)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Per-image folder structure
            img1_dir = Path(tmpdir) / "image1"
            img1_dir.mkdir()

            json1 = img1_dir / "image1.json"
            metadata1 = img1_dir / "image1_all_metadata_file.json"

            json1.touch()
            metadata1.touch()

            result = _gather_main_jsons(tmpdir)

            assert len(result) == 1
            assert str(json1) in result
            assert str(metadata1) not in result

    def test_gather_main_jsons_case_insensitive(self):
        """Test that JSON extension check is case-insensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_lower = Path(tmpdir) / "image.json"

            json_lower.touch()

            result = _gather_main_jsons(tmpdir)
            assert len(result) >= 1
            assert str(json_lower) in result


class TestImageNameFromJson:
    """Test extraction of image filename from JSON metadata."""

    def test_image_name_from_valid_json(self):
        """Test extracting image name from valid JSON with imageFile field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "test.json"
            json_data = {"BasicData": {"imageFile": "photo.jpg"}}

            with open(json_path, "w") as f:
                json.dump(json_data, f)

            result = _image_name_from_json(str(json_path))
            assert result == "photo.jpg"

    def test_image_name_from_json_no_image_file(self):
        """Test fallback when imageFile is not in JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "test.json"
            json_data = {"BasicData": {"otherField": "value"}}

            with open(json_path, "w") as f:
                json.dump(json_data, f)

            result = _image_name_from_json(str(json_path))
            # Should fallback to filename + .JPG
            assert result == "test.JPG"

    def test_image_name_from_json_no_basic_data(self):
        """Test fallback when BasicData is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "test.json"
            json_data = {"OtherData": {}}

            with open(json_path, "w") as f:
                json.dump(json_data, f)

            result = _image_name_from_json(str(json_path))
            assert result == "test.JPG"

    def test_image_name_from_invalid_json(self):
        """Test fallback for invalid JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "invalid.json"

            with open(json_path, "w") as f:
                f.write("invalid json content {{{")

            result = _image_name_from_json(str(json_path))
            assert result == "invalid.JPG"

    def test_image_name_from_nonexistent_file(self):
        """Test fallback for non-existent file."""
        result = _image_name_from_json("/nonexistent/path/file.json")
        assert result == "file.JPG"

    def test_image_name_empty_image_file_field(self):
        """Test fallback when imageFile field is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "test.json"
            json_data = {"BasicData": {"imageFile": ""}}  # Empty string

            with open(json_path, "w") as f:
                json.dump(json_data, f)

            result = _image_name_from_json(str(json_path))
            assert result == "test.JPG"


class TestRunWhiteningIntegration:
    """Integration tests for the complete whitening pipeline."""

    @patch("utils.pipeline.process_images_to_individual_json")
    @patch("utils.pipeline.prepare_data_for_qgis")
    def test_run_whitening_with_single_image(self, mock_qgis, mock_process, tmp_path):
        """Test whitening pipeline with a single image file."""
        # Create a test image
        test_image = tmp_path / "test.jpg"
        test_image.touch()

        # Mock returns - with proper directory setup
        def mock_process_side_effect(session_dir, drone_type):
            # Create expected output structure
            output_dir = Path(session_dir) / "output"
            output_dir.mkdir(exist_ok=True)
            to_qgis_dir = Path(session_dir) / "TO_QGIS"
            to_qgis_dir.mkdir(exist_ok=True)
            (to_qgis_dir / "test.json").write_text("{}")
            return session_dir

        mock_process.side_effect = mock_process_side_effect

        # Run whitening
        result = run_whitening([str(test_image)], drone_type="DJI")

        # Verify structure
        assert "session_dir" in result
        assert "zip_path" in result
        assert "output_dir" in result
        assert "fail_output_dir" in result
        assert "to_qgis_dir" in result
        assert "results" in result

    @patch("utils.pipeline.process_images_to_individual_json")
    @patch("utils.pipeline.prepare_data_for_qgis")
    def test_run_whitening_with_directory(self, mock_qgis, mock_process, tmp_path):
        """Test whitening pipeline with a directory containing images."""
        # Create directory with images
        images_dir = tmp_path / "images"
        images_dir.mkdir()

        (images_dir / "photo1.jpg").touch()
        (images_dir / "photo2.jpg").touch()

        # Mock returns with proper setup
        def mock_process_side_effect(session_dir, drone_type):
            output_dir = Path(session_dir) / "output"
            output_dir.mkdir(exist_ok=True)
            to_qgis_dir = Path(session_dir) / "TO_QGIS"
            to_qgis_dir.mkdir(exist_ok=True)
            (to_qgis_dir / "data.json").write_text("{}")
            return session_dir

        mock_process.side_effect = mock_process_side_effect

        # Run whitening
        result = run_whitening([str(images_dir)], drone_type="Autel")

        # Verify mock was called
        mock_process.assert_called_once()
        assert "session_dir" in result

    @patch("utils.pipeline.process_images_to_individual_json")
    @patch("utils.pipeline.prepare_data_for_qgis")
    def test_run_whitening_mixed_paths(self, mock_qgis, mock_process, tmp_path):
        """Test whitening with both file and directory paths."""
        # Create test file and directory
        test_file = tmp_path / "photo.jpg"
        test_file.touch()

        images_dir = tmp_path / "images"
        images_dir.mkdir()
        (images_dir / "photo2.jpg").touch()

        # Mock returns
        def mock_process_side_effect(session_dir, drone_type):
            output_dir = Path(session_dir) / "output"
            output_dir.mkdir(exist_ok=True)
            to_qgis_dir = Path(session_dir) / "TO_QGIS"
            to_qgis_dir.mkdir(exist_ok=True)
            (to_qgis_dir / "data.json").write_text("{}")
            return session_dir

        mock_process.side_effect = mock_process_side_effect

        # Run whitening
        result = run_whitening([str(test_file), str(images_dir)], drone_type="DJI")

        assert "session_dir" in result

    @patch("utils.pipeline.process_images_to_individual_json")
    @patch("utils.pipeline.prepare_data_for_qgis")
    def test_run_whitening_no_images_raises_error(self, mock_qgis, mock_process, tmp_path):
        """Test that error is raised when no images are found."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with pytest.raises(RuntimeError) as exc_info:
            run_whitening([str(empty_dir)], drone_type="DJI")

        assert "לא נמצאו תמונות" in str(exc_info.value)

    @patch("utils.pipeline.process_images_to_individual_json")
    @patch("utils.pipeline.prepare_data_for_qgis")
    def test_run_whitening_creates_config_json(self, mock_qgis, mock_process, tmp_path):
        """Test that config.json is created in session directory."""
        test_image = tmp_path / "test.jpg"
        test_image.touch()

        # Mock to capture session directory
        def mock_process_side_effect(session_dir, drone_type):
            # Check config exists
            config_path = os.path.join(session_dir, "config.json")
            assert os.path.exists(config_path)

            with open(config_path, "r") as f:
                config = json.load(f)

            assert config["drone_type"] == "DJI"
            assert config["skip_log"] is False

            # Create expected output structure
            output_dir = os.path.join(session_dir, "output")
            to_qgis_dir = os.path.join(session_dir, "TO_QGIS")
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(to_qgis_dir, exist_ok=True)

            with open(os.path.join(to_qgis_dir, "test.json"), "w") as f:
                json.dump({}, f)

            return session_dir

        mock_process.side_effect = mock_process_side_effect

        run_whitening([str(test_image)], drone_type="DJI", skip_log=False)

        # Verify mock was called with expected drone type
        mock_process.assert_called_once()

    @patch("utils.pipeline.process_images_to_individual_json")
    @patch("utils.pipeline.prepare_data_for_qgis")
    def test_run_whitening_writes_quality_filter_to_config(self, mock_qgis, mock_process, tmp_path):
        test_image = tmp_path / "test.jpg"
        test_image.touch()

        def mock_process_side_effect(session_dir, drone_type):
            config_path = os.path.join(session_dir, "config.json")
            assert os.path.exists(config_path)
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            assert config["quality_filter"]["min_relative_altitude"] == 200.0
            assert config["quality_filter"]["allow_wide"] is True
            assert config["quality_filter"]["allow_zoom"] is False

            output_dir = os.path.join(session_dir, "output")
            to_qgis_dir = os.path.join(session_dir, "TO_QGIS")
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(to_qgis_dir, exist_ok=True)
            with open(os.path.join(to_qgis_dir, "test.json"), "w", encoding="utf-8") as f:
                json.dump({}, f)
            return session_dir

        mock_process.side_effect = mock_process_side_effect

        run_whitening(
            [str(test_image)],
            drone_type="DJI",
            skip_log=True,
            quality_filter={
                "blur_threshold": 5.0,
                "min_relative_altitude": 200.0,
                "max_relative_altitude": 5000.0,
                "allow_thermal": True,
                "allow_visible": True,
                "allow_zoom": False,
                "allow_wide": True,
            },
        )
        mock_process.assert_called_once()

    @patch("utils.pipeline.process_images_to_individual_json")
    @patch("utils.pipeline.prepare_data_for_qgis")
    def test_run_whitening_creates_zip(self, mock_qgis, mock_process, tmp_path):
        """Test that ZIP file is created."""
        test_image = tmp_path / "test.jpg"
        test_image.touch()

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Create TO_QGIS directory structure
        to_qgis_dir = session_dir / "TO_QGIS"
        to_qgis_dir.mkdir()
        (to_qgis_dir / "test.json").write_text("{}")

        output_dir = session_dir / "output"
        output_dir.mkdir()

        mock_process.return_value = str(session_dir)

        result = run_whitening([str(test_image)], drone_type="DJI")

        # Verify ZIP was created
        assert result["zip_path"].endswith(".zip")
        assert os.path.exists(result["zip_path"])


class TestImageExtensionConstant:
    """Test the IMAGE_EXT constant."""

    def test_image_ext_is_set(self):
        """Test that IMAGE_EXT constant is defined."""
        assert IMAGE_EXT is not None
        assert len(IMAGE_EXT) > 0

    def test_image_ext_contains_common_formats(self):
        """Test that IMAGE_EXT contains common image formats."""
        expected_formats = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"}
        assert IMAGE_EXT == expected_formats

    def test_image_ext_is_set_type(self):
        """Test that IMAGE_EXT is a set."""
        assert isinstance(IMAGE_EXT, set)
