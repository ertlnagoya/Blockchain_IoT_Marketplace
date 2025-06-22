from math import ceil
import cv2
import os
import glob
import re
from collections import namedtuple, defaultdict
import random
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import json
from concurrent.futures import as_completed
import tempfile

# 画像が保存されているディレクトリ（再帰的に探索）
frames_dir = r'C:\Users\yuichiro.yasue\Downloads\mevid-v1-bbox-test\bbox_test'
output_dir = "output/"
frames_per_second = 30  # Assuming 30 FPS
output_movie_seconds = 60 * 5  # 5 minutes

BBoxInfo = namedtuple('BBoxInfo', ['pedestrian_id', 'outfit', 'camera', 'tracklet'])

def get_bbox_info(path):
    # ファイル名からBBoxInfoを抽出
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
    return bbox_infos2frames_path

# image_pathsをmovies_per_camera個に分割
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

def create_movie_from_images(movie_image_paths, video_path, frames_per_second, max_width, max_height):
    class ImagePrefetcher:
        def __init__(self, image_paths, max_width, max_height):
            self.image_paths = image_paths
            self.empty_frame = np.zeros((max_height, max_width, 3), dtype=np.uint8)  # 黒い画像を事前に生成

        def load_image(self, img_path):
            if img_path is None:
                return None, self.empty_frame, None
            img = cv2.imread(img_path)
            assert img is not None, f"Failed to load image: {img_path}"
            canvas = np.zeros((max_height, max_width, 3), dtype=np.uint8)
            h, w = img.shape[:2]
            canvas[:h, :w] = img  # 左上揃えで貼り付け
            bbox = {
                'x': 0,  # 左上揃えなのでxは0
                'y': 0,  # 左上揃えなのでyは0
                'width': w,
                'height': h
            }
            return img_path, canvas, bbox
        
        def __iter__(self):
            with ThreadPoolExecutor(max_workers=2) as executor:
                yield from executor.map(self.load_image, self.image_paths)

    # 動画ライターの初期化
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, frames_per_second, (max_width, max_height))

    person_dict = defaultdict(list)  # pedestrian_id -> [{frame, bbox}, ...]

    # 画像のプリフェッチ
    prefetcher = ImagePrefetcher(movie_image_paths, max_width, max_height)
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

    return person_dict

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
        # まず、各bbox_infoに対応する画像数を取得
        total_original_frames = sum([len(self.bbox_infos2frames_path[b]) for b in self.bbox_infos])

        # 挿入する「誰もいない」フレームの総数
        total_insert_frames = self.each_camera_output_movies_num * output_movie_seconds * frames_per_second - total_original_frames
        # gap数を「先頭」「間」「末尾」の分だけ増やす
        num_gaps_with_ends = len(self.bbox_infos) + 1
        if num_gaps_with_ends > 0 and total_insert_frames > 0:
            base = total_insert_frames // num_gaps_with_ends
            remainder = total_insert_frames % num_gaps_with_ends
            insert_lengths = [base + (1 if i < remainder else 0) for i in range(num_gaps_with_ends)]
        else:
            insert_lengths = []

        image_paths = [None] * insert_lengths[0]  # 先頭に空フレームを追加
        for i, bbox_info in enumerate(self.bbox_infos):
            image_paths.extend(self.bbox_infos2frames_path[bbox_info])
            image_paths.extend([None] * insert_lengths[i + 1])

        movies_image_paths = chunk_list(image_paths, self.each_camera_output_movies_num)
        return movies_image_paths

    def calculate_max_size(self, movies_image_paths):
        def _get_img_size(img_path):
            # 画像サイズだけ取得するためにimdecode+ファイル読み込みで高速化
            try:
                with open(img_path, 'rb') as f:
                    buf = np.frombuffer(f.read(1024 * 1024), dtype=np.uint8)  # 1MBまで読む
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
                    kwargs = {
                        "video_path": video_path,
                        "video_name": video_name,
                        "movie_image_paths": movie_image_paths,
                        "max_width": self.max_width,
                        "max_height": self.max_height,
                        "camera_id": self.camera_id,
                        "json_path": json_path
                    }
                    futures.append(executor.submit(self.process_movie, kwargs))
                try:
                    for f in futures:
                        f.result()
                    
                except KeyboardInterrupt:
                    print("KeyboardInterrupt detected. Cancelling...")
                    for f in futures:
                        f.cancel()
                    raise
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
            for file in glob.glob(os.path.join(tmp_output_dir, "*")):
                os.rename(file, os.path.join(self.output_dir, os.path.basename(file)))

    def process_movie(self, kwargs):
        video_path = kwargs['video_path']
        video_name = kwargs['video_name']
        json_path = kwargs['json_path']
        movie_image_paths = kwargs['movie_image_paths']

        person_ids = create_movie_from_images(
            movie_image_paths=movie_image_paths,
            video_path=video_path,
            frames_per_second=frames_per_second,
            max_width=self.max_width,
            max_height=self.max_height
        )
        json_data = {
            "camera_id": self.camera_id,
            "movie_id": video_name,
            "person_ids": person_ids
        }

        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2)
        print(f"Created {video_name} with {len(movie_image_paths)} frames. pedestrian count: {len(json_data)}", flush=True)


def main():
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

        # 各カメラの動画を作成
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

if __name__ == "__main__":
    main()
