#!/usr/bin/env python3
import argparse
import base64
import json
from pathlib import Path

import requests

from process_runtime.vlm_contract import (
    build_temperature_vlm_request,
    parse_temperature_result,
)


PROMPT = """
Inspect this simulated industrial temperature display.
Read only the large current temperature value shown in degrees Celsius.
Return one JSON object with exactly these keys:
visible (boolean), temperature_c (number or null), confidence (0 to 1),
and evidence (a short description of the visible digits).
Do not infer the value from the progress bar or from prior knowledge.
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument(
        "--url", default="http://127.0.0.1:11434/api/chat"
    )
    parser.add_argument("--model", default="qwen3-vl:8b-instruct")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    encoded = base64.b64encode(args.image.read_bytes()).decode("ascii")
    response = requests.post(
        args.url,
        json=build_temperature_vlm_request(
            encoded_image=encoded,
            model=args.model,
            prompt=PROMPT,
        ),
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["message"]["content"]
    result = parse_temperature_result(content)
    rendered = json.dumps(
        {
            "model": payload.get("model"),
            "total_duration_ns": payload.get("total_duration"),
            "result": {
                "visible": result.visible,
                "temperature_c": result.temperature_c,
                "confidence": result.confidence,
                "evidence": result.evidence,
            },
        },
        indent=2,
    )
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
