"""Generate images with the OpenAI Images API from a job JSON file.

Job format:
{
  "project": "banatska-kuca",
  "model": "gpt-image-2",
  "defaults": {"size": "1536x1024", "quality": "high"},
  "images": [
    {"name": "hero", "prompt": "...", "size": "1536x1024"}
  ]
}
Output: output/<project>/<name>.png
"""
import base64
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

API = "https://api.openai.com/v1/images/generations"


def main(job_path: str) -> int:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("OPENAI_API_KEY secret is missing", file=sys.stderr)
        return 1

    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    project = job["project"]
    model = job.get("model", "gpt-image-2")
    defaults = job.get("defaults", {})
    out_dir = Path(__file__).resolve().parent.parent / "output" / project
    out_dir.mkdir(parents=True, exist_ok=True)

    def run(img):
        body = {
            "model": model,
            "prompt": img["prompt"],
            "size": img.get("size", defaults.get("size", "1024x1024")),
            "quality": img.get("quality", defaults.get("quality", "high")),
            "n": 1,
        }
        r = requests.post(
            API,
            headers={"Authorization": f"Bearer {key}"},
            json=body,
            timeout=600,
        )
        if r.status_code != 200:
            print(f"[FAIL] {img['name']}: {r.status_code} {r.text[:300]}")
            return False
        data = r.json()["data"][0]
        target = out_dir / f"{img['name']}.png"
        if "b64_json" in data:
            target.write_bytes(base64.b64decode(data["b64_json"]))
        else:
            target.write_bytes(requests.get(data["url"], timeout=120).content)
        print(f"[OK] {target}")
        return True

    workers = int(job.get("parallel", 4))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(run, job["images"]))
    failed = results.count(False)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
