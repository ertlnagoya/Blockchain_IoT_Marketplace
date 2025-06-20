import cv2
import os
import glob
import re
from collections import namedtuple, defaultdict
import random
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# 画像が保存されているディレクトリ（再帰的に探索）
frames_dir = r'C:\Users\yuichiro.yasue\Downloads\mevid-v1-bbox-test\bbox_test'
output_dir = "output/"
frames_per_second = 30  # Assuming 30 FPS
movies_per_camera = 10  # Assuming we want to create 10 movies per camera

BBoxInfo = namedtuple('BBoxInfo', ['pedestrian_id', 'outfit', 'camera', 'tracklet'])

def get_bbox_infos2frames_path(frames_dir):
    pattern = re.compile(r'([0-9]*)O([0-9]*)C([0-9]*)T([0-9]*)F([0-9]*).jpg$', re.IGNORECASE)

    bbox_infos2frames_path = defaultdict(list)
    for root, dirs, files in os.walk(frames_dir):
        for file in files:
            match = pattern.match(file)
            if not match: continue
            bbox_info = BBoxInfo(
                pedestrian_id=match.group(1),
                outfit=match.group(2),
                camera=match.group(3),
                tracklet=match.group(4)
            )
            bbox_infos2frames_path[bbox_info].append(os.path.join(root, file))

    return bbox_infos2frames_path


def calculate_max_size(camera_id, bbox_infos2frames_path):
    def _get_img_size(img_path):
        img = cv2.imread(img_path)
        if img is not None:
            h, w = img.shape[:2]
            return w, h
        return 0, 0
    
    # camera_idに対応する画像パスを取得
    img_paths = []
    for bbox_info in bbox_infos2frames_path:
        if bbox_info.camera != camera_id:
            continue
        img_paths.extend(bbox_infos2frames_path[bbox_info])

    max_width, max_height = 0, 0
    with ThreadPoolExecutor() as executor:
        for w, h in executor.map(_get_img_size, img_paths):
            if w > max_width:
                max_width = w
            if h > max_height:
                max_height = h
    return max_width, max_height

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

def create_movie_from_images(movie_image_paths, video_path, camera_id, bbox_infos2frames_path, frames_per_second):
    max_width, max_height = calculate_max_size(camera_id, bbox_infos2frames_path)

    # 動画ライターの初期化
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, frames_per_second, (max_width, max_height))

    for img_path in movie_image_paths:
        if img_path is None:
            # 「誰もいない」フレームを生成（黒い画像）
            empty_frame = np.zeros((max_height, max_width, 3), dtype=np.uint8)
            out.write(empty_frame)
        else:
            img = cv2.imread(img_path)
            if img is not None:
                # サイズを揃える
                img_resized = cv2.resize(img, (max_width, max_height))
                out.write(img_resized)

    out.release()


def main():
    # bbox2frames_path[BBoxInfo] = [image_path, ...]
    bbox_infos2frames_path = get_bbox_infos2frames_path(frames_dir)
    print(f"Found {len(bbox_infos2frames_path)} movies.")

    # camera2bbox_infos[camera_id] = [BBoxInfo, ...]
    camera2bbox_infos = defaultdict(list)
    for bbox_info, frames in bbox_infos2frames_path.items():
        camera2bbox_infos[bbox_info.camera].append(bbox_info)
    print(f"Found {len(camera2bbox_infos)} unique cameras.")

    each_camera_frames = {}
    for camera_id, bbox_infos in camera2bbox_infos.items():
        frames_num = sum([len(bbox_infos2frames_path[bbox_info]) for bbox_info in bbox_infos])
        each_camera_frames[camera_id] = frames_num
        print(f"Camera {camera_id} has {len(bbox_infos)} movies.",
              f"with {frames_num} frames ({frames_num / frames_per_second:.2f} seconds).")
    max_frames_per_camera = max(each_camera_frames.values())    
    print(f"max_frames_per_camera: {max_frames_per_camera} frames ({max_frames_per_camera / frames_per_second:.2f} seconds).")


    for camera_id, bbox_infos in camera2bbox_infos.items():
        # 各カメラの動画を作成
        print(f"Camera {camera_id} has {len(bbox_infos)} movies.")

        # 既存のbbox_infoの間に「誰もいない」フレームを挿入してmax_frames_per_cameraまで伸長
        # まず、各bbox_infoに対応する画像数を取得
        total_original_frames = sum([len(bbox_infos2frames_path[b]) for b in bbox_infos])

        # 挿入する「誰もいない」フレームの総数
        total_insert_frames = max_frames_per_camera - total_original_frames
        # gap数を「先頭」「間」「末尾」の分だけ増やす
        num_gaps_with_ends = len(bbox_infos) + 1
        if num_gaps_with_ends > 0 and total_insert_frames > 0:
            base = total_insert_frames // num_gaps_with_ends
            remainder = total_insert_frames % num_gaps_with_ends
            insert_lengths = [base + (1 if i < remainder else 0) for i in range(num_gaps_with_ends)]
        else:
            insert_lengths = []
        
        image_paths = [[None] * insert_lengths[0]]  # 先頭に空フレームを追加
        for i, bbox_info in enumerate(bbox_infos):
            image_paths.extend(bbox_infos2frames_path[bbox_info])
            image_paths.extend([None] * insert_lengths[i + 1])

        
        movies_image_paths = chunk_list(image_paths, movies_per_camera)

        # 各動画を並列で作成
        def process_movie(args):
            i, movie_image_paths = args
            if not movie_image_paths:
                return
            video_name = f"{camera_id}_movie_{i}.mp4"
            video_path = os.path.join(output_dir, video_name)
            create_movie_from_images(
                movie_image_paths,
                video_path,
                camera_id,
                bbox_infos2frames_path,
                frames_per_second
            )
            print(f"Created {video_name} with {len(movie_image_paths)} frames.")

        with ThreadPoolExecutor() as executor:
            executor.map(process_movie, enumerate(movies_image_paths))


if __name__ == "__main__":
    main()
