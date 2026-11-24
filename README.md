# ai-image-gen

OpenAI image generation (gpt-image-2) via GitHub Actions. Nothing runs or is stored on a local machine.

- Key: repository secret `OPENAI_API_KEY` (Settings, Secrets and variables, Actions). Never in code, chat or logs.
- Jobs: `jobs/<project>.json` (format in `scripts/generate.py`).
- Run: push a new or changed job file to `main`, or dispatch manually with `job_file`.
- Output: `output/<project>/<name>.png`, committed back by the workflow.
- Reference images: put them in `refs/` and add `"references": [...]` (and optionally `"input_fidelity": "high"`) to an image; it then uses the edits endpoint.
- Depth maps: `"depth": true` on an image, or `"depth_extra": [paths]` on the job, writes `<name>-depth.png` (Depth Anything V2, near = white).
