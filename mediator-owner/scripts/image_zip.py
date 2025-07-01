import argparse
import os
import shutil
import json


def extract_frame(movie_path, json_data, output_dir):
    if not os.path.exists(movie_path):
        raise FileNotFoundError(f"入力ファイルが見つかりません: {movie_path}")
    shutil.copy(movie_path, output_dir)
    output_path = os.path.join(output_dir, os.path.basename(movie_path))
    print(os.path.abspath(output_path))

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
