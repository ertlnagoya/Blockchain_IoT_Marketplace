# Only reads raw images; it will NOT upload anything for you
# Generate videos and corresponding metadata (JSON) to prepare for later upload or distribution
# The script traverses frames in the specified directory (with pedestrian bounding boxes), groups by camera, and creates multiple videos
# Each video gets a JSON with: camera ID + video filename + pedestrian IDs and their bounding boxes + video start/end timestamps + camera geolocation (latitude/longitude)
from math import ceil
import argparse
import cv2
import os
import glob
import re
from collections import namedtuple, defaultdict
import datetime
import random
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import json
from concurrent.futures import as_completed
import tempfile
from geopy.distance import distance
from geopy.point import Point

frames_per_second = 30  # Assuming 30 FPS
output_movie_seconds = 60 * 5  # 5 minutes

BBoxInfo = namedtuple('BBoxInfo', ['pedestrian_id', 'outfit', 'camera', 'tracklet'])

def get_bbox_info(path):
    # Extract BBoxInfo from filename
    pattern = re.compile(r'([0-9]*)O([0-9]*)C([0-9]*)T([0-9]*)F([0-9]*).jpg$', re.IGNORECASE)
    match = pattern.match(os.path.basename(path))
    if match:
        return BBoxInfo(
            pedestrian_id=match.group(1),
            outfit=match.group(2),
            camera=match.group(3),
            tracklet=match.group(4)
        )
    return None

def get_bbox_infos2frames_path(frames_dir):
    bbox_infos2frames_path = defaultdict(list)
    for root, dirs, files in os.walk(frames_dir):
        for file in files:
            bbox_info = get_bbox_info(os.path.join(root, file))
            if bbox_info is not None:
                bbox_infos2frames_path[bbox_info].append(os.path.join(root, file))
    for paths in bbox_infos2frames_path.values():
        paths.sort()
    return bbox_infos2frames_path

# Split image_paths into movies_per_camera chunks
def chunk_list(lst, n):
    avg = len(lst) // n
    rem = len(lst) % n
    chunks = []
    start = 0
    for i in range(n):
        end = start + avg + (1 if i < rem else 0)
        chunks.append(lst[start:end])
        start = end
    return chunks


def get_completed_cameras(output_dir, movies_per_camera):
    completed_cameras = set()
    camera_movie_counts = defaultdict(int)
    for file in os.listdir(output_dir):
        if file.endswith(".mp4"):
            match = re.match(r"(\d+)_movie_\d+\.mp4$", file)
            if match:
                camera_id = match.group(1)
                camera_movie_counts[camera_id] += 1
    for camera_id, count in camera_movie_counts.items():
        if count == movies_per_camera:
            completed_cameras.add(camera_id)
    return completed_cameras


def calculate_max_frames_per_camera(bbox_infos2frames_path, camera2bbox_infos):
    each_camera_frames = {}
    for camera_id, bbox_infos in camera2bbox_infos.items():
        frames_num = sum([len(bbox_infos2frames_path[bbox_info]) for bbox_info in bbox_infos])
        each_camera_frames[camera_id] = frames_num
        print(f"Camera {camera_id} has {len(bbox_infos)} movies.",
              f"with {frames_num} frames ({frames_num / frames_per_second:.2f} seconds).")
    max_frames_per_camera = max(each_camera_frames.values())    
    return max_frames_per_camera

class MovieGenerator:
    def __init__(self, camera_id, bbox_infos, bbox_infos2frames_path, output_dir, each_camera_output_movies_num, output_movie_seconds, max_width=None, max_height=None):
        self.camera_id = camera_id
        self.bbox_infos = bbox_infos
        self.bbox_infos2frames_path = bbox_infos2frames_path
        self.output_dir = output_dir
        self.each_camera_output_movies_num = each_camera_output_movies_num
        self.output_movie_seconds = output_movie_seconds
        self.max_width = max_width
        self.max_height = max_height

    def generate_movies_image_paths(self):
        # First, get the number of images for each bbox_info
        total_original_frames = sum([len(self.bbox_infos2frames_path[b]) for b in self.bbox_infos])

        # Total number of "empty" frames to insert
        total_insert_frames = self.each_camera_output_movies_num * output_movie_seconds * frames_per_second - total_original_frames
        # Increase the number of gaps to include "head", "middle", and "tail"
        num_gaps_with_ends = len(self.bbox_infos) + 1
        if num_gaps_with_ends > 0 and total_insert_frames > 0:
            base = total_insert_frames // num_gaps_with_ends
            remainder = total_insert_frames % num_gaps_with_ends
            insert_lengths = [base + (1 if i < remainder else 0) for i in range(num_gaps_with_ends)]
        else:
            insert_lengths = []

        image_paths = [None] * insert_lengths[0]  # Add empty frames at the beginning
        for i, bbox_info in enumerate(self.bbox_infos):
            image_paths.extend(self.bbox_infos2frames_path[bbox_info])
            image_paths.extend([None] * insert_lengths[i + 1])

        movies_image_paths = chunk_list(image_paths, self.each_camera_output_movies_num)
        return movies_image_paths

    def calculate_max_size(self, movies_image_paths):
        def _get_img_size(img_path):
            # To only get image size quickly, use imdecode + partial file read
            try:
                with open(img_path, 'rb') as f:
                    buf = np.frombuffer(f.read(1024 * 1024), dtype=np.uint8)  # Read up to 1MB
                img = cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
                if img is not None:
                    h, w = img.shape[:2]
                    return w, h
            except Exception:
                raise RuntimeError(f"Failed to read image size for {img_path}")

        max_width, max_height = 0, 0
        with ThreadPoolExecutor(max_workers=12) as executor:
            img_paths = []
            for movie_image_paths in movies_image_paths:
                movie_image_paths = [img_path for img_path in movie_image_paths if img_path is not None]
                img_paths.extend(movie_image_paths)
            futures = [executor.submit(_get_img_size, img_path) for img_path in img_paths]
            for i, future in enumerate(as_completed(futures)):
                try:
                    w, h = future.result()
                    if w > max_width:
                        max_width = w
                    if h > max_height:
                        max_height = h
                    if i % 3000 == 0:
                        print(f"Exploited {i} / {len(img_paths)} image sizes for camera {self.camera_id}", flush=True)
                except KeyboardInterrupt:
                    print("KeyboardInterrupt detected. Cancelling...")
                    for f in futures:
                        f.cancel()
                    raise
                except Exception as e:
                    print(f"Error processing image: {e}", flush=True)
        return max_width, max_height


    def generate_movies(self):
        movies_image_paths = self.generate_movies_image_paths()
        assert all(len(movie) == self.output_movie_seconds * frames_per_second for movie in movies_image_paths), \
            "Each movie must have the same number of frames."

        self.max_width, self.max_height = self.calculate_max_size(movies_image_paths)
        print(f"Camera {self.camera_id} max size: {self.max_width}x{self.max_height}", flush=True)

        with tempfile.TemporaryDirectory() as tmp_output_dir:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for i, movie_image_paths in enumerate(movies_image_paths):
                    video_name = f"{self.camera_id}_movie_{i}"
                    video_path = os.path.join(tmp_output_dir, f"{video_name}.mp4")
                    json_path = os.path.join(tmp_output_dir, f"{video_name}.json")
                    futures.append(executor.submit(self.create_movie_from_images, movie_image_paths, video_path, json_path))
                for f in futures:
                    video_name = f.result(timeout=None)
                    print(f"returned from future: {video_name}", flush=True)
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
            for file in glob.glob(os.path.join(tmp_output_dir, "*")):
                os.rename(file, os.path.join(self.output_dir, os.path.basename(file)))

    def create_movie_from_images(self, movie_image_paths, video_path, json_path):
        class ImagePrefetcher:
            def __init__(self, image_paths, max_width, max_height):
                self.image_paths = image_paths
                self.max_width = max_width
                self.max_height = max_height
                self.empty_frame = np.zeros((max_height, max_width, 3), dtype=np.uint8)  # Pre-generate black image

            def load_image(self, img_path):
                if img_path is None:
                    return None, self.empty_frame, None
                img = cv2.imread(img_path)
                assert img is not None, f"Failed to load image: {img_path}"
                canvas = np.zeros((self.max_height, self.max_width, 3), dtype=np.uint8)
                h, w = img.shape[:2]
                canvas[:h, :w] = img  # Paste aligned to top-left
                bbox = {
                    'x': 0,  # x is 0 because it’s aligned to top-left
                    'y': 0,  # y is 0 because it’s aligned to top-left
                    'width': w,
                    'height': h
                }
                return img_path, canvas, bbox
            
            def __iter__(self):
                with ThreadPoolExecutor(max_workers=2) as executor:
                    yield from executor.map(self.load_image, self.image_paths)

        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, frames_per_second, (self.max_width, self.max_height))

        person_dict = defaultdict(list)  # pedestrian_id -> [{frame, bbox}, ...]

        # Image prefetch
        prefetcher = ImagePrefetcher(movie_image_paths, self.max_width, self.max_height)
        for i, (img_path, img, bbox) in enumerate(prefetcher):
            if i % 3000 == 0:
                print(f"Processed {i} frames", os.path.basename(video_path), flush=True)
            out.write(img)
            if img_path is not None:
                bbox_info = get_bbox_info(img_path)
                assert bbox_info is not None, f"Failed to get BBoxInfo for {img_path}"
                person_dict[bbox_info.pedestrian_id].append(
                    {
                        'frame': i,
                        'bbox': bbox
                    }
                )

        out.release()
        json_data = {
            'camera_id': self.camera_id,
            'video_name': os.path.basename(video_path),
            "person_ids": person_dict
        }
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2)
        print(f"Created movie {video_path} with {len(movie_image_paths)} frames.", flush=True)
        return os.path.basename(video_path)

def main():
    argparser = argparse.ArgumentParser(description="Generate movies from frames with bounding boxes.")
    argparser.add_argument('--frames_dir', type=str, required=True, help="Directory containing frames with bounding boxes.")
    argparser.add_argument('--output_dir', type=str, required=True, help="Directory to save the output movies.")

    # Directory where images are stored (recursively searched)
    frames_dir = os.path.abspath(argparser.parse_args().frames_dir)
    output_dir = os.path.abspath(argparser.parse_args().output_dir)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # bbox2frames_path[BBoxInfo] = [image_path, ...]
    bbox_infos2frames_path = get_bbox_infos2frames_path(frames_dir)
    print(f"Found {len(bbox_infos2frames_path)} movies.")

    # camera2bbox_infos[camera_id] = [BBoxInfo, ...]
    camera2bbox_infos = defaultdict(list)
    for bbox_info in bbox_infos2frames_path.keys():
        camera2bbox_infos[bbox_info.camera].append(bbox_info)
    print(f"Found {len(camera2bbox_infos)} unique cameras.")

    max_frames_per_camera = calculate_max_frames_per_camera(
        bbox_infos2frames_path=bbox_infos2frames_path,
        camera2bbox_infos=camera2bbox_infos
    )
    print(f"max_frames_per_camera: {max_frames_per_camera} frames ({max_frames_per_camera / frames_per_second:.2f} seconds).")
    each_camera_output_movies_num = ceil(max_frames_per_camera / (frames_per_second * output_movie_seconds))
    print(f"Each camera will have {each_camera_output_movies_num} output movies.")

    completed_cameras = get_completed_cameras(output_dir, each_camera_output_movies_num)

    for camera_id, bbox_infos in camera2bbox_infos.items():
        if camera_id in completed_cameras:
            print(f"Camera {camera_id} already completed. Skipping...")
            continue

        # Create videos for each camera
        print(f"Camera {camera_id} has {len(bbox_infos)} movies.")
        movie_generator = MovieGenerator(
            camera_id=camera_id,
            bbox_infos=bbox_infos,
            bbox_infos2frames_path=bbox_infos2frames_path,
            output_dir=output_dir,
            each_camera_output_movies_num=each_camera_output_movies_num,
            output_movie_seconds=output_movie_seconds
        )
        movie_generator.generate_movies()
        print(f"Finished processing camera {camera_id}.", flush=True)
    
    initial_location = Point(35.1534, 136.9668)  # Set initial location
    locations = {}
    for i, camera_id in enumerate(camera2bbox_infos.keys()):
        if i == 0:
            locations[camera_id] = initial_location
        point = distance(meters = i % 3 * 100).destination(point=initial_location, bearing=0)
        point = distance(meters = i // 3 * 100).destination(point=point, bearing=90)
        locations[camera_id] = point
    
    start_time = datetime.datetime(2025, 6, 30, 8, 0, 0)
    json_path_pattern = re.compile(r"(\d+)_movie_(\d+)\.json$")
    for json_path in glob.glob(os.path.join(output_dir, "*.json")):
        result = json_path_pattern.match(os.path.basename(json_path))
        assert result is not None, f"Failed to match JSON path: {json_path}"
        camera_id = result.group(1)
        movie_index = result.group(2)
        timestamp = start_time + datetime.timedelta(seconds=int(movie_index) * output_movie_seconds)
    
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        json_data['start_timestamp'] = timestamp.isoformat()
        json_data['end_timestamp'] = (timestamp + datetime.timedelta(seconds=output_movie_seconds)).isoformat()
        json_data['location'] = {
            'latitude': locations[camera_id].latitude,
            'longitude': locations[camera_id].longitude
        }
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2)


if __name__ == "__main__":
    main()
