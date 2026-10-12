import argparse
import datetime as dt
import json
import pathlib

from .build import asset_json, last_complete_month, manifest_json
from .catalog import ASSETS, FX
from .fetch import fetch_monthly_closes
from .validate import validate_asset, validate_manifest


def build_site(out: pathlib.Path, fetch=fetch_monthly_closes, today: dt.date | None = None) -> dict[str, dict]:
    version = last_complete_month(today or dt.date.today())
    fetched: dict[str, dict[str, float]] = {}

    def closes(ticker: str) -> dict[str, float]:
        if ticker not in fetched:
            fetched[ticker] = fetch(ticker)
        return fetched[ticker]

    docs: dict[str, dict] = {f"prices/{a.id}.json": asset_json(a, closes(a.ticker), version) for a in ASSETS}
    docs["fx/usdkrw.json"] = asset_json(FX, closes(FX.ticker), version)
    for doc in docs.values():
        validate_asset(doc, version)

    asset_ids = [a.id for a in ASSETS]
    manifest = manifest_json(version, asset_ids)
    validate_manifest(manifest, asset_ids)
    docs["manifest.json"] = manifest

    for path, doc in docs.items():
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return docs


def main() -> None:
    parser = argparse.ArgumentParser(description="해따치고 시세 데이터 빌드")
    parser.add_argument("--out", default="site", type=pathlib.Path)
    args = parser.parse_args()
    docs = build_site(args.out)
    size = sum(p.stat().st_size for p in args.out.rglob("*.json"))
    print(f"version {docs['manifest.json']['version']}: {len(docs)} files, {size // 1024} KB")


if __name__ == "__main__":
    main()
