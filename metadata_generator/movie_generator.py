import cv2
import os
import glob
import re

# 画像が保存されているディレクトリ（再帰的に探索）
frames_dir = r'C:\Users\yuichiro.yasue\Downloads\mevid-v1-bbox-test\bbox_test'

# Cで始まり、数字が続き、330が含まれるディレクトリ内の画像ファイルを再帰的に取得

image_paths = []
pattern = re.compile(r'.*C330T.*.jpg$', re.IGNORECASE)

for root, dirs, files in os.walk(frames_dir):
    for file in files:
        if file.lower().endswith('.jpg'):
            full_path = os.path.join(root, file)
            if pattern.match(file):
                print(full_path)  # デバッグ用
                image_paths.append(full_path)

image_paths = sorted(image_paths)

if not image_paths:
    raise ValueError("frames/ ディレクトリに画像が見つかりません。")

# 最初の画像のサイズを取得
first_frame = cv2.imread(image_paths[0])
height, width = first_frame.shape[:2]

# 動画ファイルの出力設定
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('output.mp4', fourcc, 30.0, (width, height))

# 1分間(=60秒)の動画を作成するために必要なフレーム数
max_frames = 30 * 60  # 30fps * 60秒 = 1800フレーム

# すべての画像の最大幅・高さを取得
max_width, max_height = width, height
for img_path in image_paths[:max_frames]:
    img = cv2.imread(img_path)
    if img is not None:
        h, w = img.shape[:2]
        if w > max_width:
            max_width = w
        if h > max_height:
            max_height = h

# 動画ファイルの出力設定を最大サイズに合わせて再作成
out.release()
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('output.mp4', fourcc, 30.0, (max_width, max_height))

for i, img_path in enumerate(image_paths):
    if i >= max_frames:
        break
    img = cv2.imread(img_path)
    if img is None:
        print(f"画像の読み込みに失敗: {img_path}")
        continue
    # サイズが異なる場合はpadding（左上寄せ）
    h, w = img.shape[:2]
    if w != max_width or h != max_height:
        top = 0
        bottom = max_height - h
        left = 0
        right = max_width - w
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0,0,0])
    out.write(img)

out.release()
print("動画ファイル output.mp4 を作成しました。")