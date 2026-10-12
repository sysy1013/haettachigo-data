NEIGHBOR_AGREE = 1.2
SPIKE = 0.5


def remove_spikes(closes: dict[str, float]) -> tuple[dict[str, float], list[str]]:
    """이웃 두 달은 서로 비슷한데 혼자 튀는 달(소스 오류)을 뺀다. 첫·마지막 달은 유지.

    모든 판정은 원본 시계열 기준(반복 제거 아님). (정리된 사본, 제거된 달 오름차순) 반환.
    """
    months = sorted(closes)
    dropped: list[str] = []
    for i in range(1, len(months) - 1):
        a, v, b = closes[months[i - 1]], closes[months[i]], closes[months[i + 1]]
        if max(a, b) / min(a, b) <= NEIGHBOR_AGREE and abs(v / ((a + b) / 2) - 1) > SPIKE:
            dropped.append(months[i])
    skip = set(dropped)
    return {m: closes[m] for m in months if m not in skip}, dropped
