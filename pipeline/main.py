import argparse
import datetime as dt
import json
import pathlib

from .build import asset_json, last_complete_month, manifest_json
from .catalog import ASSETS, FX
from .clean import remove_spikes
from .fetch import fetch_monthly_closes
from .validate import validate_asset, validate_manifest


def _today() -> dt.date:
    return dt.date.today()


def build_site(
    out: pathlib.Path,
    fetch=None,
    today: dt.date | None = None,
    dropped: dict[str, list[str]] | None = None,
) -> dict[str, dict]:
    """전체 사이트를 out에 쓴다. dropped를 넘기면 id별로 제거된 튐 값의 달을 채운다."""
    fetch = fetch or fetch_monthly_closes
    version = last_complete_month(today or _today())
    fetched: dict[str, dict[str, float]] = {}

    def closes(ticker: str) -> dict[str, float]:
        if ticker not in fetched:
            fetched[ticker] = fetch(ticker)
        return fetched[ticker]

    def build(asset) -> dict:
        # 미완결 달은 버리고 나서 튐 값을 판정한다 (마지막 완결 달이 미완결 달과 비교되지 않도록)
        complete = {m: v for m, v in closes(asset.ticker).items() if m <= version}
        cleaned, drops = remove_spikes(complete)
        if drops and dropped is not None:
            dropped[asset.id] = drops
        return asset_json(asset, cleaned, version)

    docs: dict[str, dict] = {f"prices/{a.id}.json": build(a) for a in ASSETS}
    docs["fx/usdkrw.json"] = build(FX)
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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="해따치고 시세 데이터 빌드")
    parser.add_argument("--out", default="site", type=pathlib.Path)
    args = parser.parse_args(argv)
    dropped: dict[str, list[str]] = {}
    docs = build_site(args.out, dropped=dropped)
    for aid, months in dropped.items():
        print(f"{aid}: dropped {', '.join(months)}")
    size = sum(p.stat().st_size for p in args.out.rglob("*.json"))
    print(f"version {docs['manifest.json']['version']}: {len(docs)} files, {size // 1024} KB")


if __name__ == "__main__":
    main()
