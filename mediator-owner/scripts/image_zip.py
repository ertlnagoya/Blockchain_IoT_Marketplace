import argparse
import os
import shutil
import json
import cv2


def extract_frame(movie_path, json_data, output_dir):
    if not os.path.exists(movie_path):
        raise FileNotFoundError(f"入力ファイルが見つかりません: {movie_path}")

    # JSONデータからperson_idごとに最大の面積を持つフレームを抽出
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
    
    # 動画ファイルを開く
    capture = cv2.VideoCapture(movie_path)
    if not capture.isOpened():
        raise RuntimeError(f"動画ファイルを開くことができません: {movie_path}")
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    # person2frameのフレームを一時ディレクトリに保存
    movie_name_without_ext = os.path.splitext(os.path.basename(movie_path))[0]
    temp_dir = os.path.join(output_dir, movie_name_without_ext)
    os.makedirs(temp_dir, exist_ok=True)
    for person_id, frame_number in person2frame.items():
        assert 0 <= frame_number < frame_count, f"フレーム番号 {frame_number} は動画のフレーム数 {frame_count} を超えています。"
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = capture.read()
        assert ret, f"フレーム {frame_number} を読み込むことができませんでした。"
        output_frame_path = os.path.join(temp_dir, f"{person_id}_frame_{frame_number}.jpg")
        cv2.imwrite(output_frame_path, frame)

    # 一時ディレクトリをzipにまとめる
    tmp = shutil.make_archive(os.path.join(output_dir, movie_name_without_ext), 'zip', root_dir=temp_dir)
    print(f"フレームを抽出し、zipにまとめました: {tmp}")

    # 一時ディレクトリを削除
    # shutil.rmtree(temp_dir)


def main():
    parser = argparse.ArgumentParser(description="人が映った画像をzipにまとめるスクリプト")
    parser.add_argument("--input_video", required=True, help="入力ファイルのパス")
    parser.add_argument("--output_dir", required=True, help="出力ディレクトリ")
    args = parser.parse_args()

    movie_path = args.input_video
    if not os.path.exists(movie_path):
        raise FileNotFoundError(f"入力ファイルが見つかりません: {movie_path}")
    if not movie_path.lower().endswith('.mp4'):
        raise ValueError(f"入力ファイルはMP4形式でなければなりません: {movie_path}")

    json_path = os.path.join(os.path.dirname(movie_path), os.path.splitext(os.path.basename(movie_path))[0] + ".json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"対応するJSONファイルが見つかりません: {json_path}")
    # 拡張子を確認
    with open(json_path, 'r') as f:
        json_data = json.load(f)

    return extract_frame(movie_path, json_data, args.output_dir)


if __name__ == "__main__":
    main()
