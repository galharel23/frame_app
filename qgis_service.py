import os
import json
import math
import shutil

def prepare_data_for_qgis(session_dir: str) -> None:
    """
    Creates TO_QGIS folder in the session dir containing .jpg + .json + .jpw for each valid image.
    """
    output_dir = os.path.join(session_dir, "output")
    to_qgis_dir = os.path.join(session_dir, "TO_QGIS")
    os.makedirs(to_qgis_dir, exist_ok=True)

    if not os.path.isdir(output_dir):
        print(f"Output dir not found: {output_dir}")
        return

    for file in os.listdir(output_dir):
        if file.lower().endswith('.json'):
            json_path = os.path.join(output_dir, file)

            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    image_file_name = data['BasicData']['imageFile']
            except Exception as e:
                print(f" Failed reading JSON {file}: {e}")
                continue

            image_path = os.path.join(session_dir, image_file_name)
            if not os.path.exists(image_path):
                print(f" Image not found for JSON: {image_file_name}")
                continue

            create_jpw_from_json(json_path)

            jpw_file_name = os.path.splitext(image_file_name)[0] + ".jpw"
            jpw_path = os.path.join(output_dir, jpw_file_name)
            if not os.path.exists(jpw_path):
                print(f" JPW file not created for: {image_file_name}")
                continue

            try:
                shutil.copy2(image_path, os.path.join(to_qgis_dir, image_file_name))
                shutil.copy2(json_path, os.path.join(to_qgis_dir, file))
                shutil.copy2(jpw_path, os.path.join(to_qgis_dir, jpw_file_name))
                print(f" Copied {image_file_name}, {file}, and {jpw_file_name} to TO_QGIS")
            except Exception as e:
                print(f" Failed copying files to TO_QGIS: {e}")

# helper method
# used in prepare_data_for_qgis
def create_jpw_from_json(json_filepath: str) -> None:
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {json_filepath} was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: File {json_filepath} is not a valid JSON.")
        return

    try:
        image_file = data['BasicData']['imageFile']
        width_pixels = data['BasicData']['width']
        height_pixels = data['BasicData']['height']
        resolution_meters_per_pixel = data['BasicData']['resolution']
        center_lat = data['CameraPosition']['gpsLatitude']
        center_lon = data['CameraPosition']['gpsLongitude']
    except KeyError as e:
        print(f"Error: JSON structure is invalid. Missing key: {e}")
        return

    lat_radians = math.radians(center_lat)
    meters_per_deg_lon = 111320 * math.cos(lat_radians)
    A = resolution_meters_per_pixel / meters_per_deg_lon

    meters_per_deg_lat = 111320
    E = -resolution_meters_per_pixel / meters_per_deg_lat

    B = 0.0
    D = 0.0

    offset_x_deg = (width_pixels / 2) * A
    offset_y_deg = (height_pixels / 2) * abs(E)
    C = center_lon - offset_x_deg
    F = center_lat + offset_y_deg

    jpw_filename = os.path.splitext(image_file)[0] + '.jpw'
    jpw_filepath = os.path.join(os.path.dirname(json_filepath), jpw_filename)

    jpw_content = f"{A}\n{D}\n{B}\n{E}\n{C}\n{F}"

    try:
        with open(jpw_filepath, 'w', encoding='utf-8') as f:
            f.write(jpw_content)
        print(f"JPW file created successfully: {jpw_filepath}")
    except IOError as e:
        print(f"Error writing JPW file: {e}")
