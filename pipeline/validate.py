import math
import re

from .build import month_end

CATEGORIES = {"kr_stock", "us_stock", "crypto", "commodity", "fx"}
CURRENCIES = {"KRW", "USD"}
MAX_JUMP = 0.9
_REQUIRED = ("id", "name", "category", "currency", "listedFrom", "prices")
_YM = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ValidationError(Exception):
    pass


def _is_price(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0


def validate_asset(doc: dict, version: str) -> None:
    missing = [k for k in _REQUIRED if k not in doc]
    if missing:
        raise ValidationError(f"{doc.get('id', '?')}: missing {missing}")
    aid = doc["id"]
    if doc["category"] not in CATEGORIES:
        raise ValidationError(f"{aid}: bad category {doc['category']!r}")
    if doc["currency"] not in CURRENCIES:
        raise ValidationError(f"{aid}: bad currency {doc['currency']!r}")

    prices = doc["prices"]
    if len(prices) < 2:
        raise ValidationError(f"{aid}: need at least 2 prices")
    months = [row[0] for row in prices]
    if not all(isinstance(m, str) and _YM.match(m) for m in months):
        raise ValidationError(f"{aid}: bad month format")
    if any(a >= b for a, b in zip(months, months[1:])):
        raise ValidationError(f"{aid}: months not strictly ascending")
    if doc["listedFrom"] != months[0]:
        raise ValidationError(f"{aid}: listedFrom {doc['listedFrom']} != {months[0]}")
    if not all(_is_price(row[1]) for row in prices):
        raise ValidationError(f"{aid}: non-positive or non-numeric price")
    if months[-1] != version:
        raise ValidationError(f"{aid}: latest month {months[-1]} != {version}")

    change = prices[-1][1] / prices[-2][1] - 1
    if abs(change) > MAX_JUMP:
        raise ValidationError(f"{aid}: latest month changed {change:+.0%}")


def validate_manifest(doc: dict, asset_ids: list[str]) -> None:
    version = doc.get("version")
    if not isinstance(version, str) or not _YM.match(version):
        raise ValidationError(f"manifest: bad version {version!r}")
    if doc.get("baseDate") != month_end(version):
        raise ValidationError(f"manifest: baseDate {doc.get('baseDate')!r} != {month_end(version)}")
    if doc.get("assets") != asset_ids:
        raise ValidationError("manifest: asset list mismatch")
