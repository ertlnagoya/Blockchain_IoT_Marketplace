import argparse
import os
from datetime import datetime
import shutil


def extract_frame(input_path, output_dir):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    shutil.copy(input_path, output_dir)
    output_path = os.path.join(output_dir, os.path.basename(input_path))
    print(os.path.abspath(output_path))

def main():
    parser = argparse.ArgumentParser(description="Script to deploy without processing")
    parser.add_argument("--input_video", required=True, help="Path to input file")
    parser.add_argument("--output_dir", required=True, help="Output directory")
    args = parser.parse_args()

    return extract_frame(args.input_video, args.output_dir)


if __name__ == "__main__":
    main()
