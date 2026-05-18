import csv
import io
import urllib.request
from pathlib import Path


def read_csv(source: str) -> tuple[list[str], list[dict]]:
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=30) as resp:
            text = resp.read().decode("utf-8-sig")
    else:
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"No existe el archivo: {source}")
        text = path.read_text(encoding="utf-8-sig")

    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip() for h in (reader.fieldnames or [])]
    rows = [{(k or "").strip(): (v or "") for k, v in row.items()} for row in reader]
    return headers, rows
