# ai-image-gen

OpenAI image generation (gpt-image-2) via GitHub Actions. Nothing runs or is stored on a local machine.

- Key: repository secret `OPENAI_API_KEY` (Settings, Secrets and variables, Actions). Never in code, chat or logs.
- Jobs: `jobs/<project>.json` (format in `scripts/generate.py`).
- Run: push a new or changed job file to `main`, or dispatch manually with `job_file`.
- Output: `output/<project>/<name>.png`, committed back by the workflow.
