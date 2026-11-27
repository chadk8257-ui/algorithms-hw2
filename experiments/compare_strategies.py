"""Compare separate chaining and linear probing at identical load factors."""

import csv
from pathlib import Path
from random import Random
from time import perf_counter_ns
from typing import NamedTuple
from xml.sax.saxutils import escape

from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable


CAPACITY = 1000
KEY_SEED = 20261127
MISS_QUERY_COUNT = 1000
TIMING_REPEATS = 3
LOAD_TENTHS = range(1, 10)


class Measurement(NamedTuple):
    load_factor: float
    key_seed: int
    entries: int
    capacity: int
    average_chain_length: float
    maximum_chain_length: int
    chain_success_comparisons: float
    chain_theoretical_success_comparisons: float
    chain_failure_comparisons: float
    chain_theoretical_failure_comparisons: float
    linear_success_comparisons: float
    linear_theoretical_success_comparisons: float
    linear_failure_comparisons: float
    linear_theoretical_failure_comparisons: float
    chain_success_lookup_ns: float
    linear_success_lookup_ns: float
    chain_failure_lookup_ns: float
    linear_failure_lookup_ns: float


def _chain_lengths(table: HashTable[int]) -> list[int]:
    lengths = []
    for bucket in table._buckets:
        length = 0
        entry = bucket
        while entry is not None:
            length += 1
            entry = entry.next
        lengths.append(length)
    return lengths


def _chain_comparisons(
    table: HashTable[int], key: str, should_exist: bool
) -> int:
    entry = table._buckets[table._index(key)]
    comparisons = 0
    while entry is not None:
        comparisons += 1
        if entry.key == key:
            if not should_exist:
                raise RuntimeError(f"expected a missing key: {key!r}")
            return comparisons
        entry = entry.next
    if should_exist:
        raise RuntimeError(f"expected an inserted key: {key!r}")
    return comparisons


def _linear_comparisons(
    table: LinearProbingHashTable[int], key: str, should_exist: bool
) -> int:
    index = table._index(key)
    for comparisons in range(1, table.capacity + 1):
        slot = table._slots[index]
        if slot is None:
            if should_exist:
                raise RuntimeError(f"expected an inserted key: {key!r}")
            return comparisons
        if hasattr(slot, "key") and slot.key == key:
            if not should_exist:
                raise RuntimeError(f"expected a missing key: {key!r}")
            return comparisons
        index = (index + 1) % table.capacity
    if should_exist:
        raise RuntimeError(f"expected an inserted key: {key!r}")
    return table.capacity


def _average_comparisons(
    table: HashTable[int] | LinearProbingHashTable[int],
    keys: list[str],
    should_exist: bool,
) -> float:
    if isinstance(table, HashTable):
        total = sum(
            _chain_comparisons(table, key, should_exist) for key in keys
        )
    else:
        total = sum(
            _linear_comparisons(table, key, should_exist) for key in keys
        )
    return total / len(keys)


def _average_lookup_ns(
    table: HashTable[int] | LinearProbingHashTable[int],
    keys: list[str],
    should_exist: bool,
) -> float:
    start = perf_counter_ns()
    for _ in range(TIMING_REPEATS):
        for key in keys:
            if (table.get(key) is not None) != should_exist:
                raise RuntimeError(f"lookup returned an incorrect result: {key!r}")
    return (perf_counter_ns() - start) / (TIMING_REPEATS * len(keys))


def _missing_keys(
    chaining: HashTable[int], linear: LinearProbingHashTable[int]
) -> list[str]:
    keys = []
    candidate = 0
    while len(keys) < MISS_QUERY_COUNT:
        key = f"missing-{candidate}"
        candidate += 1
        if key not in chaining and key not in linear:
            keys.append(key)
    return keys


def _measure(
    load_factor: float, keys: list[str], entries: int
) -> Measurement:
    chaining: HashTable[int] = HashTable(capacity=CAPACITY, max_load=None)
    linear: LinearProbingHashTable[int] = LinearProbingHashTable(
        capacity=CAPACITY, max_load=None
    )
    for index, key in enumerate(keys[:entries]):
        chaining.set(key, index)
        linear.set(key, index)

    if chaining.capacity != linear.capacity or len(chaining) != len(linear):
        raise RuntimeError("hash table setups do not match")
    if any(chaining.get(key) != linear.get(key) for key in keys[:entries]):
        raise RuntimeError("the two tables do not contain the same key set")

    misses = _missing_keys(chaining, linear)
    chain_lengths = _chain_lengths(chaining)
    chain_success = _average_comparisons(chaining, keys[:entries], True)
    chain_failure = _average_comparisons(chaining, misses, False)
    linear_success = _average_comparisons(linear, keys[:entries], True)
    linear_failure = _average_comparisons(linear, misses, False)
    linear_success_theory = (1 + 1 / (1 - load_factor)) / 2
    linear_failure_theory = (1 + 1 / (1 - load_factor) ** 2) / 2

    return Measurement(
        load_factor,
        KEY_SEED,
        entries,
        CAPACITY,
        sum(chain_lengths) / CAPACITY,
        max(chain_lengths),
        chain_success,
        1 + load_factor / 2,
        chain_failure,
        load_factor,
        linear_success,
        linear_success_theory,
        linear_failure,
        linear_failure_theory,
        _average_lookup_ns(chaining, keys[:entries], True),
        _average_lookup_ns(linear, keys[:entries], True),
        _average_lookup_ns(chaining, misses, False),
        _average_lookup_ns(linear, misses, False),
    )


def _svg_panel(
    x: int,
    y: int,
    title: str,
    series: list[tuple[str, list[float], str]],
    load_factors: list[float],
) -> list[str]:
    width = 430
    height = 250
    left = x + 52
    top = y + 34
    plot_width = width - 68
    plot_height = height - 86
    bottom = top + plot_height
    maximum = max(value for _, values, _ in series for value in values)
    y_max = max(1.0, maximum * 1.12)
    svg = [
        f'<text x="{x}" y="{y + 18}" class="panel-title">{escape(title)}</text>'
    ]

    for tick in range(5):
        value = y_max * tick / 4
        tick_y = bottom - plot_height * tick / 4
        svg.append(
            f'<line x1="{left}" y1="{tick_y:.1f}" '
            f'x2="{left + plot_width}" y2="{tick_y:.1f}" class="grid"/>'
        )
        svg.append(
            f'<text x="{left - 7}" y="{tick_y + 4:.1f}" '
            f'text-anchor="end" class="tick">{value:.1f}</text>'
        )

    svg.extend(
        [
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/>',
            f'<line x1="{left}" y1="{bottom}" '
            f'x2="{left + plot_width}" y2="{bottom}" class="axis"/>',
        ]
    )
    for index, load in enumerate(load_factors):
        if index % 2 == 0:
            tick_x = left + plot_width * index / (len(load_factors) - 1)
            svg.append(
                f'<text x="{tick_x:.1f}" y="{bottom + 16}" '
                f'text-anchor="middle" class="tick">{load:.1f}</text>'
            )

    for index, (label, values, color) in enumerate(series):
        points = []
        for point_index, value in enumerate(values):
            point_x = left + plot_width * point_index / (len(values) - 1)
            point_y = bottom - plot_height * value / y_max
            points.append(f"{point_x:.1f},{point_y:.1f}")
        svg.append(
            f'<polyline points="{" ".join(points)}" '
            f'stroke="{color}" class="series"/>'
        )
        legend_y = y + height - 8 + (index // 2) * 13
        legend_x = x + (index % 2) * 205
        svg.extend(
            [
                f'<line x1="{legend_x}" y1="{legend_y - 4}" '
                f'x2="{legend_x + 18}" y2="{legend_y - 4}" '
                f'stroke="{color}" class="series"/>',
                f'<text x="{legend_x + 23}" y="{legend_y}" '
                f'class="legend">{escape(label)}</text>',
            ]
        )
    return svg


def _write_svg(rows: list[Measurement], path: Path) -> None:
    loads = [row.load_factor for row in rows]
    comparison_series = (
        ("Chain measured", "#1769aa", "chain_success_comparisons"),
        ("Chain theory", "#64a6d9", "chain_theoretical_success_comparisons"),
        ("Linear measured", "#c62828", "linear_success_comparisons"),
        ("Linear theory", "#ef7777", "linear_theoretical_success_comparisons"),
    )

    def series_for(fields: tuple[tuple[str, str, str], ...]):
        return [
            (label, [float(getattr(row, field)) for row in rows], color)
            for label, color, field in fields
        ]

    success_series = series_for(comparison_series)
    failure_fields = (
        ("Chain measured", "#1769aa", "chain_failure_comparisons"),
        ("Chain theory", "#64a6d9", "chain_theoretical_failure_comparisons"),
        ("Linear measured", "#c62828", "linear_failure_comparisons"),
        ("Linear theory", "#ef7777", "linear_theoretical_failure_comparisons"),
    )
    timing_success = (
        ("Chaining", "#1769aa", "chain_success_lookup_ns"),
        ("Linear probing", "#c62828", "linear_success_lookup_ns"),
    )
    timing_failure = (
        ("Chaining", "#1769aa", "chain_failure_lookup_ns"),
        ("Linear probing", "#c62828", "linear_failure_lookup_ns"),
    )

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="650" '
        'viewBox="0 0 1000 650">',
        "<style>",
        "text{font-family:Arial,sans-serif;fill:#222}",
        ".title{font-size:21px;font-weight:bold}",
        ".panel-title{font-size:14px;font-weight:bold}",
        ".tick,.legend{font-size:10px}",
        ".grid{stroke:#ddd;stroke-width:1}",
        ".axis{stroke:#555;stroke-width:1}",
        ".series{fill:none;stroke-width:2}",
        "</style>",
        '<text x="500" y="28" text-anchor="middle" class="title">'
        "Chaining vs. linear probing</text>",
    ]
    panels = (
        (30, 45, "Successful search — comparisons/query", success_series),
        (
            520,
            45,
            "Unsuccessful search — comparisons/query",
            series_for(failure_fields),
        ),
        (
            30,
            350,
            "Successful lookup — ns/query",
            series_for(timing_success),
        ),
        (
            520,
            350,
            "Unsuccessful lookup — ns/query",
            series_for(timing_failure),
        ),
    )
    for x, y, title, series in panels:
        svg.extend(_svg_panel(x, y, title, series, loads))
    svg.extend(
        [
            '<text x="500" y="640" text-anchor="middle" class="tick">'
            f"Load factor (entries / {CAPACITY} buckets)</text>",
            "</svg>",
        ]
    )
    path.write_text("\n".join(svg) + "\n", encoding="utf-8")


def main() -> None:
    random = Random(KEY_SEED)
    keys = [f"key-{random.getrandbits(64):016x}" for _ in range(CAPACITY)]
    rows = []
    for tenths in LOAD_TENTHS:
        load_factor = tenths / 10
        entries = CAPACITY * tenths // 10
        row = _measure(load_factor, keys, entries)
        rows.append(row)
        print(
            f"load={load_factor:.1f} chain={row.chain_success_comparisons:.3f}/"
            f"{row.chain_failure_comparisons:.3f} "
            f"linear={row.linear_success_comparisons:.3f}/"
            f"{row.linear_failure_comparisons:.3f}"
        )

    output_directory = Path(__file__).resolve().parent
    csv_path = output_directory / "strategy_comparison.csv"
    svg_path = output_directory / "strategy_comparison.svg"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(Measurement._fields)
        writer.writerows(rows)
    _write_svg(rows, svg_path)
    print(f"CSV: {csv_path}")
    print(f"SVG: {svg_path}")


if __name__ == "__main__":
    main()
