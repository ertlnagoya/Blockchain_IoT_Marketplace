"""
IPFSにデータを格納し，CIDを記録する
"""

import os
import subprocess
import json

def main():
    jsons_dir = "output"
    for json_file in os.listdir(jsons_dir):
        if not json_file.endswith(".json"):
            continue
        json_path = os.path.join(jsons_dir, json_file)
        # curlコマンドを実行
        result = subprocess.run(
            [
                "curl",
                "-X", "POST",
                "http://localhost:5001/api/v0/add",
                "-F", f"file=@{json_path}"
            ],
            capture_output=True,
            text=True
        )
        # 結果をdictに変換
        if result.returncode == 0:
            response_dict = json.loads(result.stdout)
        else:
            response_dict = {"error": result.stderr}
        cid = response_dict.get("Hash")
        print(response_dict)

if __name__ == "__main__":
    main()
