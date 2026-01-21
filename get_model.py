#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict
from urllib.request import urlopen, Request


BASE_DIR = Path("~/.cache/robocrew/tts").expanduser()

# Hardcoded Onyx voice models by language.
# Replace the model names and URLs below with the exact ones you want.
MODELS: Dict[str, Dict[str, Dict[str, str]]] = {
	"en": {
		"model_name": "en_GB-southern_english_female-low",
		"files": {
			"en_GB-southern_english_female-low.onnx": (
				"https://huggingface.co/rhasspy/piper-voices/resolve/main/"
				"en/en_GB/southern_english_female/low/"
				"en_GB-southern_english_female-low.onnx"
			),
			"en_GB-southern_english_female-low.onnx.json": (
				"https://huggingface.co/rhasspy/piper-voices/resolve/main/"
				"en/en_GB/southern_english_female/low/"
				"en_GB-southern_english_female-low.onnx.json"
			),
		},
	},
	"pl": {
		"model_name": "pl_PL-meski_wg_glos-medium",
		"files": {
			"pl_PL-meski_wg_glos-medium.onnx": (
				"https://huggingface.co/WitoldG/polish_piper_models/resolve/main/"
				"pl_PL-meski_wg_glos-medium.onnx"
			),
			"pl_PL-meski_wg_glos-medium.onnx.json": (
				"https://huggingface.co/WitoldG/polish_piper_models/resolve/main/"
				"pl_PL-meski_wg_glos-medium.onnx.json"
			),
		},
	},
}


def download_file(url: str, dest_path: Path) -> None:
	dest_path.parent.mkdir(parents=True, exist_ok=True)
	tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")

	request = Request(url, headers={"User-Agent": "tts-robot/1.0"})
	with urlopen(request) as response, open(tmp_path, "wb") as out_file:
		total = response.headers.get("Content-Length")
		total_size = int(total) if total and total.isdigit() else None
		downloaded = 0

		while True:
			chunk = response.read(1024 * 1024)
			if not chunk:
				break
			out_file.write(chunk)
			downloaded += len(chunk)
			if total_size:
				percent = downloaded * 100 // total_size
				sys.stdout.write(f"\r  {dest_path.name}: {percent}%")
				sys.stdout.flush()

	if total_size:
		sys.stdout.write("\n")
	tmp_path.replace(dest_path)


def ensure_language_model(language: str) -> Path:
	if language not in MODELS:
		available = ", ".join(sorted(MODELS.keys()))
		raise SystemExit(f"Unknown language '{language}'. Available: {available}")

	model_info = MODELS[language]
	model_dir = BASE_DIR / language / model_info["model_name"]
	model_dir.mkdir(parents=True, exist_ok=True)

	model_path: Path | None = None
	for filename, url in model_info["files"].items():
		file_path = model_dir / filename
		if filename.endswith(".onnx"):
			model_path = file_path
		if file_path.exists() and file_path.stat().st_size > 0:
			print(f"✓ Found {file_path}")
			continue
		if not url.startswith("https://huggingface.co/"):
			raise SystemExit(
				f"Invalid or placeholder URL for {filename}. Update MODELS in get_model.py."
			)
		print(f"⬇ Downloading {filename} ...")
		download_file(url, file_path)
		print(f"✓ Saved to {file_path}")

	if model_path is None:
		raise SystemExit("No .onnx model file configured for this language.")

	return model_path


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Ensure Onyx voice model files exist in ~/.cache/robocrew/tts/"
	)
	parser.add_argument(
		"--lang",
		required=True,
		help="Language code to download (must exist in MODELS).",
	)
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	model_dir = ensure_language_model(args.lang)
	print(f"Model ready in: {model_dir}")


if __name__ == "__main__":
	main()
