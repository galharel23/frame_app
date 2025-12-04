import base64
import re

def extract_platform_data_from_log(log_file_path):
    """
    Extracts platform data from a base64-encoded DJI .LOG file.
    """
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            base64_content = f.read()

        decoded_bytes = base64.b64decode(base64_content)
        decoded_text = decoded_bytes.decode('utf-8', errors='ignore')

        def extract_value(pattern, default=0.0):
            match = re.search(pattern, decoded_text)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
            return default

        return {
            "platformName": "Padam DJI",
            "platformId": None,
            "trueCourse": extract_value(r'TrueCourse\s*[:=]\s*([0-9.]+)'),
            "groundSpeed": extract_value(r'GroundSpeed\s*[:=]\s*([0-9.]+)'),
            "mslAltitude": extract_value(r'AltitudeMSL\s*[:=]\s*([0-9.]+)'),
            "platformYaw": extract_value(r'Yaw\s*[:=]\s*([0-9.\-]+)'),
            "platformPitch": extract_value(r'Pitch\s*[:=]\s*([0-9.\-]+)'),
            "platformRoll": extract_value(r'Roll\s*[:=]\s*([0-9.\-]+)')
        }

    except Exception as e:
        print(f"❌ Failed to extract platform data: {e}")
        return {
            "platformName": "Padam DJI",
            "platformId": None,
            "trueCourse": 0.0,
            "groundSpeed": 0.0,
            "mslAltitude": 0.0,
            "platformYaw": 0.0,
            "platformPitch": 0.0,
            "platformRoll": 0.0
        }
