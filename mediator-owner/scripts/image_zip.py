import argparse
import os
import shutil
import json
import cv2


def extract_frame(movie_path, json_data, output_dir):
    if not os.path.exists(movie_path):
        raise FileNotFoundError(f"Input file not found: {movie_path}")

    # Extract, for each person_id, the frame with the largest bounding box area from the JSON data
    person2frame = {}
    for person_id in json_data["person_ids"]:
        frame_max_area = None
        bbox_max_area = 0
        for frame_dict in json_data["person_ids"][person_id]:
            area = frame_dict["bbox"]["width"] * frame_dict["bbox"]["height"]
            if area > bbox_max_area:
                bbox_max_area = area
                frame_max_area = frame_dict["frame"]
        if frame_max_area is not None:
            person2frame[person_id] = frame_max_area
    
    # Open the video file
    capture = cv2.VideoCapture(movie_path)
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open the video file: {movie_path}")
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    # Save the frames in person2frame to a temporary directory
    movie_name_without_ext = os.path.splitext(os.path.basename(movie_path))[0]
    temp_dir = os.path.join(output_dir, movie_name_without_ext)
    os.makedirs(temp_dir, exist_ok=True)
    for person_id, frame_number in person2frame.items():
        assert 0 <= frame_number < frame_count, f"Frame number {frame_number} exceeds total frame count {frame_count}."
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = capture.read()
        assert ret, f"Failed to read frame {frame_number}."
        output_frame_path = os.path.join(temp_dir, f"{person_id}_frame_{frame_number}.jpg")
        cv2.imwrite(output_frame_path, frame)

    # Zip the temporary directory
    zip_path = shutil.make_archive(os.path.join(output_dir, movie_name_without_ext), 'zip', root_dir=temp_dir)
    zip_relative_path = os.path.relpath(zip_path, start="/app")
    print(zip_relative_path)

    # Delete the temporary directory
    # shutil.rmtree(temp_dir)


def main():
    parser = argparse.ArgumentParser(description="Script to bundle images containing people into a zip")
    parser.add_argument("--input_video", required=True, help="Path to input file")
    parser.add_argument("--output_dir", required=True, help="Output directory")
    args = parser.parse_args()

    movie_path = args.input_video
    if not os.path.exists(movie_path):
        raise FileNotFoundError(f"Input file not found: {movie_path}")
    if not movie_path.lower().endswith('.mp4'):
        raise ValueError(f"Input file must be in MP4 format: {movie_path}")

    json_path = os.path.join(os.path.dirname(movie_path), os.path.splitext(os.path.basename(movie_path))[0] + ".json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Corresponding JSON file not found: {json_path}")
    # Read JSON
    with open(json_path, 'r') as f:
        json_data = json.load(f)

    return extract_frame(movie_path, json_data, args.output_dir)


if __name__ == "__main__":
    main()
