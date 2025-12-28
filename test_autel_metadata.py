"""
Test script to inspect EXIF/XMP metadata from Autel Alpha drone images.
This helps identify which fields contain LOS (line of sight) data.

Usage:
    python test_autel_metadata.py <path_to_autel_image.jpg>
"""

import sys
import json
from exif_service import run_exiftool

def inspect_all_metadata(image_path):
    """
    Extracts ALL metadata from an image using ExifTool to help identify
    which fields contain gimbal/camera orientation data.
    """
    print(f"Inspecting: {image_path}")
    print("=" * 80)
    
    try:
        # Get ALL metadata in JSON format
        cp = run_exiftool(["-json", "-a", "-G", image_path])
        data = json.loads(cp.stdout)[0] if cp.stdout else {}
        
        # Print all fields (useful for discovering field names)
        print("\n📋 ALL METADATA FIELDS:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Look for potential LOS-related fields
        print("\n\n🔍 POTENTIAL LOS/GIMBAL/CAMERA FIELDS:")
        print("-" * 80)
        los_keywords = ['yaw', 'pitch', 'roll', 'gimbal', 'camera', 'orientation', 'angle', 'rotation']
        
        for key, value in data.items():
            key_lower = key.lower()
            if any(keyword in key_lower for keyword in los_keywords):
                print(f"  {key}: {value}")
        
        # Test DJI standard fields
        print("\n\n🎯 DJI STANDARD FIELDS (for comparison):")
        print("-" * 80)
        dji_fields = ['GimbalYawDegree', 'GimbalPitchDegree', 'GimbalRollDegree']
        for field in dji_fields:
            if field in data:
                print(f"  ✅ {field}: {data[field]}")
            else:
                print(f"  ❌ {field}: NOT FOUND")
        
        # Test Autel potential fields
        print("\n\n🦅 AUTEL POTENTIAL FIELDS:")
        print("-" * 80)
        autel_fields = [
            'CameraYaw', 'CameraPitch', 'CameraRoll',
            'XMP:GimbalYawDegree', 'XMP:GimbalPitchDegree', 'XMP:GimbalRollDegree',
            'FlightYawDegree', 'FlightPitchDegree', 'FlightRollDegree',
            'XMP-drone-dji:GimbalYawDegree', 'XMP-drone-dji:GimbalPitchDegree', 'XMP-drone-dji:GimbalRollDegree'
        ]
        for field in autel_fields:
            if field in data:
                print(f"  ✅ {field}: {data[field]}")
            else:
                print(f"  ❌ {field}: NOT FOUND")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_autel_metadata.py <path_to_image.jpg>")
        print("\nExample:")
        print("  python test_autel_metadata.py \"C:/path/to/autel_image.jpg\"")
        sys.exit(1)
    
    image_path = sys.argv[1]
    inspect_all_metadata(image_path)
