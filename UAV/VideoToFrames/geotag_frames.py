import argparse
import os
import re
import subprocess
from datetime import datetime

# ---------------- Step 1: Extract Frames from Video ---------------- #
def extract_frames(video_path, output_folder, fps=1):
    """Extract frames from video using FFmpeg."""
    os.makedirs(output_folder, exist_ok=True)
    frame_pattern = os.path.join(output_folder, "frame_%04d.jpg")
    command = f'ffmpeg -i "{video_path}" -vf "fps={fps}" "{frame_pattern}"'
    subprocess.run(command, shell=True)
    print("✅ Frames extracted successfully!")

# ---------------- Step 2: Parse SRT Metadata ---------------- #
def parse_srt(srt_file):
    """Extract timestamps and GPS coordinates from SRT file."""
    gps_data = []
    with open(srt_file, "r", encoding="utf-8") as file:
        srt_content = file.read()

    matches = re.findall(r"(\d+:\d+:\d+,\d+).*?\[latitude: ([\d\.\-]+)] \[longitude: ([\d\.\-]+)] \[altitude: ([\d\.\-]+)]", srt_content)

    for match in matches:
        timestamp = datetime.strptime(match[0], "%H:%M:%S,%f")
        latitude, longitude, altitude = map(float, match[1:])
        gps_data.append((timestamp, latitude, longitude, altitude))

    return gps_data

# ---------------- Step 3: Geotag JPEGs with ExifTool ---------------- #
def geotag_image_exiftool(image_path, latitude, longitude, altitude):
    """Embed GPS metadata using ExifTool for Windows compatibility."""
    command = [
        r"C:\ExifTool\exiftool-13.25_64\exiftool.exe",
        f"-GPSLatitude={latitude}",
        f"-GPSLongitude={longitude}",
        f"-GPSAltitude={altitude}",
        "-overwrite_original",
        image_path
    ]
    subprocess.run(command, shell=True)
    print(f"✅ Geotagged EXIF GPS Metadata: {image_path}")

# ---------------- Step 4: Convert JPEGs to GeoTIFF with GDAL ---------------- #
def convert_to_geotiff(image_path, output_path, latitude, longitude):
    """Convert a JPEG to a properly georeferenced GeoTIFF."""
    command = f'gdal_translate -a_srs EPSG:4326 -gcp 0 0 {latitude} {longitude} -of GTiff "{image_path}" "{output_path}"'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(f"✅ GDAL Output: {result.stdout}")
    print(f"🛑 GDAL Error (if any): {result.stderr}")

# ---------------- Step 5: Apply GPS Metadata to GeoTIFF ---------------- #
def geotag_geotiff_exiftool(image_path, latitude, longitude, altitude):
    """Embed GPS metadata into the final GeoTIFF to ensure full compatibility."""
    command = [
        r"C:\ExifTool\exiftool-13.25_64\exiftool.exe",
        f"-GPSLatitude={latitude}",
        f"-GPSLongitude={longitude}",
        f"-GPSAltitude={altitude}",
        "-overwrite_original",
        image_path
    ]
    subprocess.run(command, shell=True)
    print(f"✅ Final Geotagging Applied to GeoTIFF: {image_path}")

# ---------------- Master Function: Extract, Geotag, Convert ---------------- #
def main(video_path, srt_file, output_folder):
    print("🔄 Extracting frames...")
    extract_frames(video_path, output_folder)

    print("🔄 Parsing SRT metadata...")
    gps_data = parse_srt(srt_file)

    print("🔄 Processing images...")
    frame_files = sorted([f for f in os.listdir(output_folder) if f.endswith(".jpg")])

    for frame_file, (timestamp, lat, lon, alt) in zip(frame_files, gps_data):
        frame_path = os.path.join(output_folder, frame_file)
        
        # Geotag JPEGs with GPS metadata
        geotag_image_exiftool(frame_path, lat, lon, alt)

        # Convert to GeoTIFF for GeoDeep processing
        geotiff_path = os.path.join(output_folder, frame_file.replace(".jpg", ".tif"))
        convert_to_geotiff(frame_path, geotiff_path, lat, lon)

        # Apply final GPS metadata fix to GeoTIFF
        geotag_geotiff_exiftool(geotiff_path, lat, lon, alt)

    print(" Process complete! GeoTIFFs are fully ready for GeoDeep.")

# ---------------- Main Execution ---------------- #
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract frames, geotag using SRT metadata, and convert to GeoTIFF.")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("srt_file", help="Path to the SRT file")
    parser.add_argument("output_folder", help="Path to save extracted frames and GeoTIFFs")

    args = parser.parse_args()
    main(args.video_path, args.srt_file, args.output_folder)