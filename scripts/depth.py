"""Depth maps (Depth Anything V2) for images of a job.

Job keys used:
  "depth": true on an image  -> output/<project>/<name>-depth.png
  "depth_extra": ["refs/x.jpg", ...] -> output/<project>/<stem>-depth.png
Depth map: grayscale, near = white, same size as the source image.
Exits 0 without loading the model when the job asks for no depth maps.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(job_path: str) -> int:
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    project = job["project"]
    out_dir = ROOT / "output" / project
    todo = [(out_dir / f"{i['name']}.png", out_dir / f"{i['name']}-depth.png") for i in job.get("images", []) if i.get("depth")]
    todo += [(ROOT / f, out_dir / f"{Path(f).stem}-depth.png") for f in job.get("depth_extra", [])]
    todo = [(s, d) for s, d in todo if s.exists()]
    if not todo:
        print("no depth maps requested")
        return 0

    import numpy as np
    from PIL import Image
    from transformers import pipeline

    model = job.get("depth_model", "depth-anything/Depth-Anything-V2-Base-hf")
    pipe = pipeline("depth-estimation", model=model, device="cpu")
    out_dir.mkdir(parents=True, exist_ok=True)
    for src, dst in todo:
        im = Image.open(src).convert("RGB")
        res = pipe(im)
        d = np.array(res["predicted_depth"].squeeze(), dtype=np.float32) if hasattr(res["predicted_depth"], "squeeze") else np.array(res["depth"], dtype=np.float32)
        d = (d - d.min()) / max(1e-6, d.max() - d.min())
        Image.fromarray((d * 255).astype("uint8")).resize(im.size, Image.BICUBIC).save(dst)
        print(f"[OK] {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
