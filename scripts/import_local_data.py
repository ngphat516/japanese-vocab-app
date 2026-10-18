"""Import locally converted normalized JSON files into private textbooks via the API.

Run from the project root: uv run python -m scripts.import_local_data.
Credentials and receipts are stored only in the ignored data/pdf_imports directory.
"""

import argparse
import hashlib
import json
import secrets
import time
from pathlib import Path

import httpx

TITLES = {
    "mimikara_n3": "Mimi Kara Oboeru N3 - Goi (PDF OCR)",
    "shinkanzen_goi_n3": "Shinkanzen N3 - Goi (PDF OCR)",
    "shinkanzen_kanji_n3": "Shinkanzen N3 - Kanji (từ trích xuất từ PDF)",
    "shinkanzen_dokkai_n3": "Shinkanzen N3 - Dokkai (từ trích xuất từ bài đọc)",
}


def run(directory: Path, base_url: str, only_book: str | None = None):
    directory.mkdir(parents=True, exist_ok=True)
    access_path = directory / "access.json"
    with httpx.Client(base_url=base_url, timeout=600) as client:

        def request(method, path, **kwargs):
            for _ in range(13):
                response = client.request(method, path, **kwargs)
                if response.status_code != 429:
                    response.raise_for_status()
                    return response
                print("Rate limit: waiting 10 seconds", flush=True)
                time.sleep(10)
            raise RuntimeError("Rate limit persisted; retry later")

        if access_path.exists():
            credentials = json.loads(access_path.read_text(encoding="utf-8"))
        else:
            credentials = {
                "api_url": base_url,
                "email": "local-owner@example.com",
                "password": secrets.token_urlsafe(24),
            }
            response = request(
                "POST",
                "/api/v1/auth/register",
                json={
                    "email": credentials["email"],
                    "password": credentials["password"],
                    "display_name": "Chủ dữ liệu PDF local",
                },
            )
            credentials["user_id"] = response.json()["id"]
            with access_path.open("x", encoding="utf-8") as stream:
                json.dump(credentials, stream, ensure_ascii=False, indent=2)
        tokens = request(
            "POST",
            "/api/v1/auth/login",
            json={"email": credentials["email"], "password": credentials["password"]},
        ).json()
        client.headers["Authorization"] = "Bearer " + tokens["access_token"]
        receipt_path = directory / "import_receipt.json"
        receipt = (
            json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt_path.exists()
            else {"books": {}}
        )

        def save():
            receipt_path.write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        for key, title in TITLES.items():
            if only_book and key != only_book:
                continue
            source_path = directory / f"{key}.json"
            if not source_path.exists():
                continue
            document = json.loads(source_path.read_text(encoding="utf-8"))
            rows = document["rows"]
            if not rows:
                continue
            record = receipt["books"].get(key)
            if record is None:
                book = request(
                    "POST",
                    "/api/v1/textbooks",
                    json={
                        "name": title,
                        "level": "N3",
                        "edition": "Theo bản PDF người dùng cung cấp",
                        "visibility": "private",
                        "license": "commercial source; user-provided PDF; private study",
                    },
                ).json()
                record = {
                    "id": book["id"],
                    "name": title,
                    "jobs": [],
                    "committed_rows": 0,
                    "skipped_ambiguous": [],
                    "source_sha256": document["source"]["sha256"],
                }
                receipt["books"][key] = record
                save()
            book_id = record["id"]
            chunks = []
            start = 0
            while start < len(rows):
                end = min(start + 2500, len(rows))
                while end > start:
                    payload = json.dumps(
                        {"source": document["source"], "rows": rows[start:end]}, ensure_ascii=False
                    ).encode()
                    if len(payload) < 4_500_000:
                        break
                    end = start + (end - start) // 2
                if end == start:
                    raise ValueError("One normalized row exceeds file size limit")
                chunks.append((start, end, payload))
                start = end
            for start, end, payload in chunks:
                payload_sha256 = hashlib.sha256(payload).hexdigest()
                if any(
                    j.get("payload_sha256") == payload_sha256 and j["status"] == "done"
                    for j in record["jobs"]
                ):
                    continue
                print(f"Upload {key}: rows {start + 1}..{end}", flush=True)
                job = request(
                    "POST",
                    "/api/v1/imports",
                    data={"textbook_id": str(book_id), "adapter": "normalized_json"},
                    files={"file": (key + ".json", payload, "application/json")},
                ).json()
                job_id = job["id"]
                if job["ambiguous"]:
                    pending = request(
                        "GET",
                        f"/api/v1/imports/{job_id}/rows",
                        params={"match_status": "ambiguous", "size": 100},
                    ).json()
                    while pending["items"]:
                        for row in pending["items"]:
                            exact = []
                            for word_id in row["candidate_word_ids"]:
                                word = request("GET", f"/api/v1/words/{word_id}").json()["word"]
                                if word["kanji"] == row["kanji"] and word["kana"] == row["kana"]:
                                    exact.append(word_id)
                            action = (
                                {"chosen_word_id": exact[0]}
                                if len(exact) == 1
                                else {"skipped": True}
                            )
                            request(
                                "PATCH", f"/api/v1/imports/{job_id}/rows/{row['id']}", json=action
                            )
                            if len(exact) != 1:
                                record["skipped_ambiguous"].append(
                                    {
                                        "job_id": job_id,
                                        "row_id": row["id"],
                                        "kanji": row["kanji"],
                                        "kana": row["kana"],
                                    }
                                )
                        pending = request(
                            "GET",
                            f"/api/v1/imports/{job_id}/rows",
                            params={"match_status": "ambiguous", "size": 100},
                        ).json()
                result = request("POST", f"/api/v1/imports/{job_id}/commit").json()
                if result["status"] != "done":
                    raise RuntimeError(f"Commit failed for job {job_id}")
                record["jobs"].append(
                    {
                        "id": job_id,
                        "start": start,
                        "end": end,
                        "status": "done",
                        "payload_sha256": payload_sha256,
                    }
                )
                record["committed_rows"] += end - start
                save()
                print(f"Committed {key}, job {job_id}", flush=True)
            lessons = request("GET", f"/api/v1/textbooks/{book_id}/lessons").json()
            for lesson in lessons:
                title = f"Trang PDF {lesson['number']}"
                if lesson["title"] != title:
                    request("PATCH", f"/api/v1/lessons/{lesson['id']}", json={"title": title})
            record["lessons"] = len(lessons)
            record["converted_rows"] = len(rows)
            record["visibility"] = "private"
            save()
        print("Finished private imports. Receipt:", receipt_path, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path("data/pdf_imports"))
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--book", choices=list(TITLES))
    args = parser.parse_args()
    run(args.directory, args.api, args.book)
