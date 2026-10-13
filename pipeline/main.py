import argparse
import datetime as dt
import json
import pathlib

from .build import asset_json, last_complete_month, manifest_json
from .catalog import ASSETS, FX
from .clean import remove_spikes
from .fetch import fetch_monthly_closes
from .latest import build_latest, fetch_latest_close
from .validate import validate_asset, validate_manifest


def _today() -> dt.date:
    return dt.date.today()


def build_site(
    out: pathlib.Path,
    fetch=None,
    today: dt.date | None = None,
    dropped: dict[str, list[str]] | None = None,
    latest_fetch=None,
    latest_failed: list[str] | None = None,
) -> dict[str, dict]:
    """전체 사이트를 out에 쓴다. dropped를 넘기면 id별로 제거된 튐 값의 달을 채운다.
    latest_fetch를 넘기면 일봉 최신가로 latest.json도 만든다(환율 실패 시 생략)."""
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

    if latest_fetch is not None:
        month_end = {d["id"]: d["prices"][-1][1] for d in docs.values() if "prices" in d}
        latest = build_latest(ASSETS, FX, month_end, latest_fetch, latest_failed)
        if latest is not None:
            docs["latest.json"] = latest

    for path, doc in docs.items():
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return docs


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="해따치고 시세 데이터 빌드")
    parser.add_argument("--out", default="site", type=pathlib.Path)
    parser.add_argument("--with-latest", action="store_true", help="일봉 최신가 latest.json 포함")
    args = parser.parse_args(argv)
    dropped: dict[str, list[str]] = {}
    failed: list[str] = []
    docs = build_site(
        args.out,
        dropped=dropped,
        latest_fetch=fetch_latest_close if args.with_latest else None,
        latest_failed=failed,
    )
    for aid, months in dropped.items():
        print(f"{aid}: dropped {', '.join(months)}")
    if args.with_latest:
        latest = docs.get("latest.json")
        if latest is None:
            print("latest: skipped (usdkrw unavailable)")
        else:
            print(f"latest {latest['asOf']}: {len(latest['prices'])}/{len(ASSETS)} prices")
        if failed:
            print(f"latest: omitted {', '.join(failed)}")
    size = sum(p.stat().st_size for p in args.out.rglob("*.json"))
    print(f"version {docs['manifest.json']['version']}: {len(docs)} files, {size // 1024} KB")


if __name__ == "__main__":
    main()
