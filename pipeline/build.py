import calendar
import datetime as dt

from .catalog import Asset


def last_complete_month(today: dt.date) -> str:
    prev = today.replace(day=1) - dt.timedelta(days=1)
    return f"{prev.year:04d}-{prev.month:02d}"


def month_end(ym: str) -> str:
    year, month = map(int, ym.split("-"))
    return f"{ym}-{calendar.monthrange(year, month)[1]:02d}"


def asset_json(asset: Asset, closes: dict[str, float], last_month: str) -> dict:
    months = sorted(m for m in closes if m <= last_month)
    if not months:
        raise ValueError(f"{asset.id}: no prices up to {last_month}")
    return {
        "id": asset.id,
        "name": asset.name,
        "category": asset.category,
        "currency": asset.currency,
        "listedFrom": months[0],
        "prices": [[m, round(closes[m], 6)] for m in months],
    }


def manifest_json(last_month: str, asset_ids: list[str]) -> dict:
    return {"version": last_month, "baseDate": month_end(last_month), "assets": asset_ids}
