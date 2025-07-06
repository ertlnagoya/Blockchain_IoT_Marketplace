import argparse
import os
from datetime import datetime
import shutil


def extract_frame(input_path, output_dir):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")
    shutil.copy(input_path, output_dir)
    output_path = os.path.join(output_dir, os.path.basename(input_path))
    print(os.path.abspath(output_path))

def main():
    parser = argparse.ArgumentParser(description="加工せずにデプロイするためのスクリプト")
    parser.add_argument("--input_video", required=True, help="入力ファイルのパス")
    parser.add_argument("--output_dir", required=True, help="出力ディレクトリ")
    args = parser.parse_args()

    return extract_frame(args.input_video, args.output_dir)


if __name__ == "__main__":
    main()
