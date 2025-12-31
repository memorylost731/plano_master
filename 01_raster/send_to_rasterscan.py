#!/usr/bin/env python3
import os
import sys
import json
import time
import requests

DEFAULT_ENDPOINT = "https://backend.rasterscan.com/raster-to-vector-raw"

RETRY_STATUS = {408, 429, 500, 502, 503, 504}

def send_plan(image_path: str) -> dict:
    api_key = os.environ.get("RASTERSCAN_API_KEY")
    if not api_key:
        raise SystemExit("ERROR: RASTERSCAN_API_KEY env var is not set.")

    endpoint = os.environ.get("RASTERSCAN_ENDPOINT", DEFAULT_ENDPOINT)

    headers = {"x-api-key": api_key}

    # Backoff: 2,4,8,16,32 (seconds)
    for attempt in range(1, 6):
        try:
            with open(image_path, "rb") as f:
                files = {"image": (os.path.basename(image_path), f)}
                r = requests.post(endpoint, headers=headers, files=files, timeout=180)

            # Success
            if r.ok:
                return r.json()

            # Retry-able errors
            if r.status_code in RETRY_STATUS:
                body_preview = (r.text or "").strip()
                if len(body_preview) > 300:
                    body_preview = body_preview[:300] + "..."
                print(
                    f"[attempt {attempt}/5] HTTP {r.status_code} from RasterScan. "
                    f"Will retry. Body: {body_preview}"
                )
                time.sleep(2 ** attempt)
                continue

            # Non-retry errors (401 etc.)
            body_preview = (r.text or "").strip()
            raise SystemExit(
                f"ERROR: RasterScan returned HTTP {r.status_code}. Body: {body_preview}"
            )

        except requests.Timeout:
            print(f"[attempt {attempt}/5] Timeout talking to RasterScan. Retrying...")
            time.sleep(2 ** attempt)
        except requests.RequestException as e:
            print(f"[attempt {attempt}/5] Network error: {e}. Retrying...")
            time.sleep(2 ** attempt)

    raise SystemExit("ERROR: RasterScan kept failing after retries. Try later or switch backend.")

def main(inp: str, outp: str):
    data = send_plan(inp)
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"OK: wrote {outp}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: send_to_rasterscan.py <image_or_pdf_path> <output.json>")
    main(sys.argv[1], sys.argv[2])
