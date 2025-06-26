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

    def generate_random_owner_ids(self):
        if len(self.owner_ids) < self.owners_num:
            self.owner_ids = self.owner_ids[:self.owners_num]
            num_to_generate = self.owners_num - len(self.owner_ids)
            new_ids = [
                "0x" + ''.join(random.choices(string.ascii_letters[:6] + string.digits, k=42))
                for _ in range(num_to_generate)
            ]
            self.owner_ids.extend(new_ids)

    def generate_random_coordinates(self):
        latitude = random.uniform(self.latitude_min, self.latitude_max)
        longtitude = random.uniform(self.longtitude_min, self.longtitude_max)
        return latitude, longtitude

    def generate_random_timestamp(self):
        random_time = self.time_start + (self.time_end - self.time_start) * random.random()
        return random_time.strftime(self.timestamp_format)

    def generate_random_detected_objects(self):
        return random.sample(self.detected_objects, k=random.randint(1, len(self.detected_objects)))

    def generate_random_license_plates(self):
        return [
            ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
            for _ in range(random.randint(1, self.license_plates_max_num))
        ]

    def generate(self, output_dir):
        random.seed(self.seed)
        self.generate_random_owner_ids()

        self.data_uuids = {
            owner_id: [str(uuid.uuid4()) for _ in range(self.each_owners_data_num)]
            for owner_id in self.owner_ids
        }

        for owner_id in self.owner_ids:
            latitude, longtitude = self.generate_random_coordinates()
            for data_uuid in self.data_uuids[owner_id]:
                timestamp = self.generate_random_timestamp()
                detected_objects = self.generate_random_detected_objects()

                if "car" in detected_objects:
                    license_plates = self.generate_random_license_plates()
                else:
                    license_plates = []

                metadata = {
                    "owner_id": owner_id,
                    "data_uuid": data_uuid,
                    "timestamp": timestamp,
                    "location": {"lat": latitude, "lon": longtitude},
                    "detected_objects": detected_objects,
                    "access_policy": "consent-required",
                    "license_plates": license_plates,
                }
                output_path = os.path.join(output_dir, f"{owner_id}_{data_uuid}.json")
                with open(output_path, "w") as f:
                    json.dump(metadata, f, indent=4)

def main():
    # Load configuration
    config_path = "config/config.json"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    with open(config_path, "r") as f:
        config = json.load(f)

    seed = config.get("seed", 42)
    generator = MetadataGenerator(seed, config)
    output_dir = config.get("output_dir", "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    generator.generate(output_dir)

if __name__ == "__main__":
    main()
