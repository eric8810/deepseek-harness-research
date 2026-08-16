"""Parse papers/cordis-spatiotemporal-composability.pdf with LlamaParse v2 REST API."""
import json
import os
import sys
import time

import httpx

API_KEY = os.environ.get("LLAMA_CLOUD_API_KEY")
if not API_KEY:
    sys.exit("LLAMA_CLOUD_API_KEY is not set")

BASE = "https://api.cloud.llamaindex.ai/api/v2/parse"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

PDF_PATH = "papers/cordis-spatiotemporal-composability.pdf"
OUT_PATH = "papers/cordis-spatiotemporal-composability.md"

with httpx.Client(timeout=httpx.Timeout(300.0)) as client:
    # 1. upload + start parse job in one multipart request
    configuration = json.dumps({"tier": "agentic", "version": "latest"})
    with open(PDF_PATH, "rb") as f:
        r = client.post(
            f"{BASE}/upload",
            headers=HEADERS,
            files={
                "file": ("cordis-spatiotemporal-composability.pdf", f, "application/pdf"),
                "configuration": (None, configuration, "application/json"),
            },
        )
    print(f"upload status: {r.status_code}")
    if r.status_code >= 400:
        sys.exit(r.text[:2000])
    job = r.json()
    job_id = job.get("id") or job.get("job", {}).get("id")
    print(f"job_id={job_id} status={job.get('status')}")

    # 2. poll until completed
    for attempt in range(180):
        r = client.get(f"{BASE}/{job_id}", headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        status = data.get("status") or data.get("job", {}).get("status")
        if attempt % 6 == 0:
            print(f"poll {attempt}: {status}")
        if status == "COMPLETED":
            break
        if status in ("FAILED", "CANCELLED"):
            sys.exit(f"job failed: {json.dumps(data)[:2000]}")
        time.sleep(5)
    else:
        sys.exit("timed out waiting for job")

    # 3. retrieve full markdown
    r = client.get(f"{BASE}/{job_id}", params={"expand": "markdown_full"}, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    markdown = data.get("markdown_full") or (data.get("result") or {}).get("markdown_full")
    if not markdown:
        sys.exit(f"markdown_full missing; keys: {sorted(data.keys())}")
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"saved {OUT_PATH}: {len(markdown)} chars")
