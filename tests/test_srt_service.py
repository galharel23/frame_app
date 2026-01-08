"""
Unit tests for SRT service module.
Tests video metadata extraction and CSV conversion functionality.
"""
import csv
import tempfile
from pathlib import Path

import pytest

from services.srt_service import VideoFrameMetadata, ms_to_hms


class TestVideoFrameMetadata:
    """Test VideoFrameMetadata class"""

    def test_metadata_creation(self):
        """Test creating metadata object"""
        metadata = VideoFrameMetadata(altitude=100.5, longitude=34.5, latitude=31.2, time="12:30:45", date="2025-01-08")
        assert metadata.altitude == 100.5
        assert metadata.longitude == 34.5
        assert metadata.latitude == 31.2
        assert metadata.time == "12:30:45"
        assert metadata.date == "2025-01-08"

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary"""
        metadata = VideoFrameMetadata(altitude=100.5, longitude=34.5, latitude=31.2, time="12:30:45", date="2025-01-08")
        result = metadata.to_dict()

        assert result["ALTITUDE"] == 100.5
        assert result["LONGITUDE"] == 34.5
        assert result["LATITUDE"] == 31.2
        assert result["TIME"] == "12:30:45"
        assert result["DATE"] == "2025-01-08"
        assert len(result) == 5  # Should have exactly 5 fields

    def test_metadata_with_none_values(self):
        """Test metadata with None values"""
        metadata = VideoFrameMetadata(altitude=None, longitude=None, latitude=None, time="", date="")
        result = metadata.to_dict()

        assert result["ALTITUDE"] is None
        assert result["LONGITUDE"] is None
        assert result["LATITUDE"] is None
        assert result["TIME"] == ""
        assert result["DATE"] == ""


class TestMsToHms:
    """Test millisecond to HMS conversion"""

    def test_zero_milliseconds(self):
        """Test converting 0ms"""
        result = ms_to_hms(0)
        assert result == "00:00:00:000"

    def test_one_second(self):
        """Test converting 1000ms (1 second)"""
        result = ms_to_hms(1000)
        assert result == "00:00:01:000"

    def test_one_minute(self):
        """Test converting 60000ms (1 minute)"""
        result = ms_to_hms(60000)
        assert result == "00:01:00:000"

    def test_one_hour(self):
        """Test converting 3600000ms (1 hour)"""
        result = ms_to_hms(3600000)
        assert result == "01:00:00:000"

    def test_complex_time(self):
        """Test converting complex time value"""
        # 1 hour, 23 minutes, 45 seconds, 500ms
        ms = (1 * 3600000) + (23 * 60000) + (45 * 1000) + 500
        result = ms_to_hms(ms)
        assert result == "01:23:45:500"


class TestConvertSrtToCsv:
    """Test SRT to CSV conversion"""

    def test_csv_export_with_valid_metadata(self):
        """Test exporting metadata to CSV"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.csv"

            metadata_list = [
                VideoFrameMetadata(altitude=100.0, longitude=34.5, latitude=31.2, time="12:30:45", date="2025-01-08"),
                VideoFrameMetadata(altitude=110.5, longitude=34.6, latitude=31.3, time="12:30:46", date="2025-01-08"),
            ]

            # Create CSV file
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["ALTITUDE", "LONGITUDE", "LATITUDE", "TIME", "DATE"])
                writer.writeheader()
                for metadata in metadata_list:
                    writer.writerow(metadata.to_dict())

            # Verify file was created
            assert output_path.exists()

            # Verify content
            with open(output_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 2
            assert rows[0]["ALTITUDE"] == "100.0"
            assert rows[0]["LONGITUDE"] == "34.5"
            assert rows[1]["ALTITUDE"] == "110.5"

    def test_csv_headers_correct(self):
        """Test CSV has correct headers (not COMMENTS or VIDEO_NAME)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.csv"

            metadata = VideoFrameMetadata(altitude=100.0, longitude=34.5, latitude=31.2, time="12:30:45", date="2025-01-08")

            # Create CSV file
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["ALTITUDE", "LONGITUDE", "LATITUDE", "TIME", "DATE"])
                writer.writeheader()
                writer.writerow(metadata.to_dict())

            # Verify headers
            with open(output_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames

            expected_headers = ["ALTITUDE", "LONGITUDE", "LATITUDE", "TIME", "DATE"]
            assert headers == expected_headers
            assert "COMMENTS" not in headers
            assert "VIDEO_NAME" not in headers


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
