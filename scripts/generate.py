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
Optional per image: "references": ["refs/photo.jpg", ...] -> uses the edits endpoint
with those images as references; "input_fidelity": "high" to keep faces/details close.
A reference inside output/<project>/ makes the image wait for that output (sequential chain).
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
EDIT_API = "https://api.openai.com/v1/images/edits"
ROOT = Path(__file__).resolve().parent.parent


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
        refs = img.get("references") or []
        if refs:
            fid = img.get("input_fidelity", defaults.get("input_fidelity"))

            def send(with_fid):
                data = {k: str(v) for k, v in body.items()}
                if with_fid and fid:
                    data["input_fidelity"] = fid
                files = [("image[]", (Path(f).name, (ROOT / f).read_bytes(), "image/jpeg" if f.lower().endswith((".jpg", ".jpeg")) else "image/png")) for f in refs]
                return requests.post(EDIT_API, headers={"Authorization": f"Bearer {key}"}, data=data, files=files, timeout=600)

            r = send(True)
            if r.status_code == 400 and fid and "input_fidelity" in r.text:
                print(f"[INFO] {img['name']}: input_fidelity not supported, retrying without it")
                r = send(False)
        else:
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

    # Images whose references point at this job's own output form a chain:
    # independent images run in parallel first, then the chain runs in listed order.
    own = f"output/{project}/"
    chained = lambda i: any(str(f).startswith(own) for f in (i.get("references") or []))
    workers = int(job.get("parallel", 4))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(run, [i for i in job["images"] if not chained(i)]))
    for img in [i for i in job["images"] if chained(i)]:
        missing = [f for f in img["references"] if not (ROOT / f).exists()]
        if missing:
            print(f"[SKIP] {img['name']}: missing {missing}")
            results.append(False)
            continue
        results.append(run(img))
    failed = results.count(False)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
