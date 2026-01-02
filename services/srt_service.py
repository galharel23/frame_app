"""
SRT to CSV conversion service for video metadata extraction.
Processes DJI SRT subtitle files and extracts GPS/telemetry data to CSV format.
"""
import re
from pathlib import Path
from typing import List, Optional, Dict
import csv

# Regex patterns
TIME_RE = re.compile(r"(\d+):(\d+):(\d+),(\d+)")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)")
LAT_RE = re.compile(r"\[latitude:\s*([-\d.]+)\]")
LON_RE = re.compile(r"\[longitude:\s*([-\d.]+)\]")
ABS_ALT_RE = re.compile(r"abs_alt:\s*([-\d.]+)")


class VideoFrameMetadata:
    """Model for video frame metadata"""
    
    def __init__(
        self,
        comments: str = "",
        video_name: str = "",
        altitude: Optional[float] = None,
        longitude: Optional[float] = None,
        latitude: Optional[float] = None,
        time: str = "",
        date: str = ""
    ):
        self.comments = comments
        self.video_name = video_name
        self.altitude = altitude
        self.longitude = longitude
        self.latitude = latitude
        self.time = time
        self.date = date
    
    def to_dict(self) -> Dict:
        """Convert to dictionary with proper column names"""
        return {
            "COMMENTS": self.comments,
            "VIDEO NAME": self.video_name,
            "ALTITUDE": self.altitude,
            "LONGITUDE": self.longitude,
            "LATITUDE": self.latitude,
            "TIME": self.time,
            "DATE": self.date
        }


def ms_to_hms(ms: int) -> str:
    """Convert milliseconds to HH:MM:SS:mmm format"""
    total_seconds = ms // 1000
    milliseconds = ms % 1000
    seconds = total_seconds % 60
    total_minutes = total_seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{milliseconds:03d}"


def extract_float(pattern: re.Pattern, text: str) -> Optional[float]:
    """Extract float value from text using regex"""
    match = pattern.search(text)
    return float(match.group(1)) if match else None


def extract_string(pattern: re.Pattern, text: str) -> Optional[str]:
    """Extract string from text using regex"""
    match = pattern.search(text)
    return match.group(1) if match else None


def process_srt(srt_path: Path) -> List[VideoFrameMetadata]:
    """Process SRT file and extract metadata"""
    
    if not srt_path.exists():
        raise FileNotFoundError(f"File not found: {srt_path}")
    
    # Read SRT file
    with srt_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    
    frames: List[VideoFrameMetadata] = []
    
    # Extract video name from path
    video_name = srt_path.stem
    
    i = 0
    while i < len(lines):
        # Search for timecode
        time_match = TIME_RE.search(lines[i])
        if not time_match:
            i += 1
            continue
        
        h, m, s, ms = map(int, time_match.groups())
        
        # Read next block (up to 12 lines)
        block_text = "".join(lines[i:i + 12])
        
        # Extract GPS data
        latitude = extract_float(LAT_RE, block_text)
        longitude = extract_float(LON_RE, block_text)
        altitude = extract_float(ABS_ALT_RE, block_text)
        
        # Skip frame if no GPS data
        if latitude is None or longitude is None:
            i += 1
            continue
        
        # Extract date
        date_str = extract_string(DATE_RE, block_text)
        date_only = date_str.split()[0] if date_str else ""
        
        # Calculate TIME
        timestamp_ms = ((h * 60 + m) * 60 + s) * 1000 + ms
        time_str = ms_to_hms(timestamp_ms)
        
        # Create frame metadata
        frame = VideoFrameMetadata(
            comments="",
            video_name=video_name,
            altitude=altitude,
            longitude=longitude,
            latitude=latitude,
            time=time_str,
            date=date_only,
        )
        
        frames.append(frame)
        i += 1
    
    return frames


def export_to_csv(frames: List[VideoFrameMetadata], output_path: Path) -> None:
    """Export data to CSV file"""
    
    if not frames:
        raise ValueError("No frames to export")
    
    # Use csv module to properly handle quoting
    with output_path.open("w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["COMMENTS", "VIDEO NAME", "ALTITUDE", "LONGITUDE", "LATITUDE", "TIME", "DATE"])
        writer.writeheader()
        
        for frame in frames:
            writer.writerow(frame.to_dict())


def convert_srt_to_csv(srt_path: Path) -> tuple[bool, str, Optional[Path]]:
    """
    Convert SRT file to CSV.
    
    Returns:
        (success, message, output_path)
    """
    try:
        srt_path = Path(srt_path)
        
        # Validate file exists and is SRT
        if not srt_path.exists():
            return False, f"File not found: {srt_path}", None
        
        if srt_path.suffix.upper() != ".SRT":
            return False, f"File is not an SRT file: {srt_path.name}", None
        
        # Process SRT file
        frames = process_srt(srt_path)
        
        if not frames:
            return False, "No GPS data found in SRT file", None
        
        # Export to CSV in same directory
        output_path = srt_path.with_suffix(".csv")
        export_to_csv(frames, output_path)
        
        return True, f"Successfully converted {len(frames)} frames", output_path
        
    except Exception as e:
        return False, f"Error processing SRT file: {str(e)}", None
