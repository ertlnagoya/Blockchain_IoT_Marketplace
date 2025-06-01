import datetime
import random
import string
import json
import os
from datetime import datetime
import uuid
                

class MetadataGenerator:
    def __init__(self, seed, config):
        self.seed = seed
        self.owners_num = config["owners_num"]
        self.owner_ids = config["owner_ids"]
        self.each_owners_data_num = config["each_owners_data_num"]
        self.detected_objects = config["detected_objects"]
        self.timestamp_format = config["timestamp_format"]
        self.time_start = datetime.strptime(
            config["timestamp_range"]["start"], self.timestamp_format
        )
        self.time_end = datetime.strptime(
            config["timestamp_range"]["end"], self.timestamp_format
        )
        self.longtitude_min = config["longtitude_range"]["min"]
        self.longtitude_max = config["longtitude_range"]["max"]
        self.latitude_min = config["latitude_range"]["min"]
        self.latitude_max = config["latitude_range"]["max"]
        self.license_plates_max_num = config["license_plates_max_num"]

    def generate(self):
        random.seed(self.seed)  # ここでrandomのseedを初期化

        # owner_ids（イーサリアムのアドレス）を必要数生成
        if len(self.owner_ids) < self.owners_num:
            self.owner_ids = self.owner_ids[:self.owners_num]
            num_to_generate = self.owners_num - len(self.owner_ids)
            new_ids = [
                "0x" + ''.join(random.choices(string.ascii_letters[:6] + string.digits, k=42))
                for _ in range(num_to_generate)
            ]
            self.owner_ids.extend(new_ids)
        
        # 各ownerのデータのUUIDを生成
        self.data_uuids = {
            owner_id: [str(uuid.uuid4()) for _ in range(self.each_owners_data_num)]
            for owner_id in self.owner_ids
        }

        for owner_id in self.owner_ids:
            # ランダムな座標を生成
            latitude = random.uniform(self.latitude_min, self.latitude_max)
            longtitude = random.uniform(self.longtitude_min, self.longtitude_max)
            for data_uuid in self.data_uuids[owner_id]:
                print(self.time_end - self.time_start)
                # 2つの時間の間でランダムな時間を生成
                random_time = self.time_start + (self.time_end - self.time_start) * random.random()
                timestamp = random_time.strftime(self.timestamp_format)
                # ランダムな検出物体を選択
                detected_objects = random.sample(self.detected_objects, k=random.randint(1, len(self.detected_objects)))
                
                if "car" in detected_objects:
                    license_plates = []
                    for _ in range(random.randint(1, self.license_plates_max_num)):
                    # 車のナンバープレートを生成
                        license_plate = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
                        license_plates.append(license_plate)
                else:
                    license_plates = []

                # メタデータを生成
                metadata = {
                    "owner_id": owner_id,  # カメラ所有者のID（ブロックチェーン上での識別子）
                    "data_uuid": data_uuid, # カメラ所有者が動画を識別するためのID
                    "timestamp": timestamp,  # 動画の撮影日時
                    "location": {"lat": latitude, "lon": longtitude},   # カメラの座標
                    "detected_objects": detected_objects,  # 検出物体のリスト
                    "access_policy": "consent-required",  # 今回は利用しない
                    "license_plates": license_plates,  # 車のナンバープレート
                }
                print(metadata)

def main():
    # Load configuration
    config_path = "config/config.json"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    with open(config_path, "r") as f:
        config = json.load(f)

    seed = config.get("seed", 42)
    generator = MetadataGenerator(seed, config)
    generator.generate()

if __name__ == "__main__":
    main()
