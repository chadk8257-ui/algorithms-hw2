"""Measure separate-chaining lookup costs at increasing hash-table load factors."""

import csv
from pathlib import Path
from random import Random
from time import perf_counter_ns
from xml.sax.saxutils import escape

from src.hash_table import HashTable


CAPACITY = 256
KEY_SEED = 20261127
MISS_QUERIES_PER_BUCKET = 2
TIMING_REPEATS = 3
LOAD_QUARTERS = range(1, 17)
COLORS = {
    "measured": "#1769aa",
    "theoretical": "#e65100",
}


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


def _comparison_count(
    table: HashTable[int], key: str, should_be_present: bool
) -> int:
    entry = table._buckets[table._index(key)]
    comparisons = 0
    while entry is not None:
        comparisons += 1
        if entry.key == key:
            if not should_be_present:
                raise RuntimeError(f"expected a missing key, found {key!r}")
            return comparisons
        entry = entry.next

    if should_be_present:
        raise RuntimeError(f"expected an inserted key, did not find {key!r}")
    return comparisons


def _missing_query_keys(table: HashTable[int]) -> list[str]:
    queries = []
    for bucket_index in range(table.capacity):
        prefix = f"missing-{bucket_index}-"
        prefix_hash = table._index(prefix)
        final_code_point = (bucket_index - 31 * prefix_hash) % table.capacity

        for offset in range(MISS_QUERIES_PER_BUCKET):
            key = prefix + chr(final_code_point + offset * table.capacity)
            if table._index(key) != bucket_index or table.get(key) is not None:
                raise RuntimeError("generated miss query did not match its bucket")
            queries.append(key)
    return queries


def _average_comparisons(
    table: HashTable[int], keys: list[str], should_be_present: bool
) -> float:
    total = sum(
        _comparison_count(table, key, should_be_present) for key in keys
    )
    return total / len(keys)


def _average_lookup_ns(
    table: HashTable[int],
    keys: list[str],
    should_be_present: bool,
) -> float:
    start = perf_counter_ns()
    for _ in range(TIMING_REPEATS):
        for key in keys:
            value = table.get(key)
            if (value is not None) != should_be_present:
                raise RuntimeError(f"lookup result was incorrect for {key!r}")
    elapsed = perf_counter_ns() - start
    return elapsed / (TIMING_REPEATS * len(keys))


def _measure(load_factor: float, entries: int) -> dict[str, int | float]:
    table: HashTable[int] = HashTable(capacity=CAPACITY, max_load=None)
    rng = Random(KEY_SEED)
    inserted_keys = [f"key-{rng.getrandbits(64):016x}" for _ in range(entries)]
    for index, key in enumerate(inserted_keys):
        table.set(key, index)

    if table.capacity != CAPACITY or table.max_load is not None:
        raise RuntimeError("the experiment table must keep its fixed capacity")
    if len(table) != entries:
        raise RuntimeError("the table did not retain every inserted key")

    lengths = _chain_lengths(table)
    missing_keys = _missing_query_keys(table)
    average_successful_comparisons = _average_comparisons(
        table, inserted_keys, should_be_present=True
    )
    average_unsuccessful_comparisons = _average_comparisons(
        table, missing_keys, should_be_present=False
    )

    return {
        "load_factor": load_factor,
        "key_seed": KEY_SEED,
        "entries": entries,
        "capacity": table.capacity,
        "average_chain_length": sum(lengths) / table.capacity,
        "max_chain_length": max(lengths),
        "average_successful_comparisons": average_successful_comparisons,
        "theoretical_successful_comparisons": 1 + load_factor / 2,
        "average_unsuccessful_comparisons": average_unsuccessful_comparisons,
        "theoretical_unsuccessful_comparisons": load_factor,
        "average_successful_lookup_ns": _average_lookup_ns(
            table, inserted_keys, should_be_present=True
        ),
        "average_unsuccessful_lookup_ns": _average_lookup_ns(
            table, missing_keys, should_be_present=False
        ),
    }


def _svg_panel(
    x: int,
    y: int,
    width: int,
    height: int,
    title: str,
    series: list[tuple[str, list[float], str]],
    load_factors: list[float],
) -> list[str]:
    left = x + 58
    top = y + 42
    plot_width = width - 78
    plot_height = height - 102
    bottom = top + plot_height
    maximum = max(value for _, values, _ in series for value in values)
    y_max = max(1.0, maximum * 1.15)
    svg = [
        f'<text x="{x}" y="{y + 20}" class="panel-title">{escape(title)}</text>'
    ]

    for tick in range(5):
        value = y_max * tick / 4
        tick_y = bottom - plot_height * tick / 4
        svg.append(
            f'<line x1="{left}" y1="{tick_y:.1f}" '
            f'x2="{left + plot_width}" y2="{tick_y:.1f}" class="grid"/>'
        )
        svg.append(
            f'<text x="{left - 8}" y="{tick_y + 4:.1f}" '
            f'text-anchor="end" class="tick">{value:.1f}</text>'
        )

    svg.extend(
        [
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/>',
            f'<line x1="{left}" y1="{bottom}" '
            f'x2="{left + plot_width}" y2="{bottom}" class="axis"/>',
        ]
    )

    x_tick_values = (0.25, 1.0, 2.0, 3.0, 4.0)
    for value in x_tick_values:
        point_index = round((value - load_factors[0]) / 0.25)
        tick_x = left + plot_width * point_index / (len(load_factors) - 1)
        svg.append(
            f'<text x="{tick_x:.1f}" y="{bottom + 18}" '
            f'text-anchor="middle" class="tick">{value:g}</text>'
        )

    for series_index, (label, values, color) in enumerate(series):
        points = []
        for index, value in enumerate(values):
            point_x = left + plot_width * index / (len(values) - 1)
            point_y = bottom - plot_height * value / y_max
            points.append(f"{point_x:.1f},{point_y:.1f}")
        svg.append(
            f'<polyline points="{" ".join(points)}" '
            f'stroke="{color}" class="series"/>'
        )
        legend_x = left + (width - 100) * series_index / max(1, len(series) - 1)
        legend_y = y + height - 14
        svg.extend(
            [
                f'<line x1="{legend_x}" y1="{legend_y - 4}" '
                f'x2="{legend_x + 20}" y2="{legend_y - 4}" stroke="{color}" '
                'class="series"/>',
                f'<text x="{legend_x + 26}" y="{legend_y}" '
                f'class="legend">{escape(label)}</text>',
            ]
        )
    return svg


def _write_svg(rows: list[dict[str, int | float]], output_path: Path) -> None:
    load_factors = [float(row["load_factor"]) for row in rows]
    chart_series = [
        (
            "Successful lookups — comparisons/query",
            [
                (
                    "Measured",
                    [float(row["average_successful_comparisons"]) for row in rows],
                    COLORS["measured"],
                ),
                (
                    "Theory",
                    [
                        float(row["theoretical_successful_comparisons"])
                        for row in rows
                    ],
                    COLORS["theoretical"],
                ),
            ],
        ),
        (
            "Unsuccessful lookups — comparisons/query",
            [
                (
                    "Measured",
                    [
                        float(row["average_unsuccessful_comparisons"])
                        for row in rows
                    ],
                    COLORS["measured"],
                ),
                (
                    "Theory",
                    [
                        float(row["theoretical_unsuccessful_comparisons"])
                        for row in rows
                    ],
                    COLORS["theoretical"],
                ),
            ],
        ),
        (
            "Successful get() — ns/query",
            [
                (
                    "Measured",
                    [
                        float(row["average_successful_lookup_ns"]) for row in rows
                    ],
                    COLORS["measured"],
                )
            ],
        ),
        (
            "Unsuccessful get() — ns/query",
            [
                (
                    "Measured",
                    [
                        float(row["average_unsuccessful_lookup_ns"]) for row in rows
                    ],
                    COLORS["measured"],
                )
            ],
        ),
    ]

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="760" '
        'viewBox="0 0 1100 760">',
        "<style>",
        "text{font-family:Arial,sans-serif;fill:#222}",
        ".title{font-size:22px;font-weight:bold}",
        ".panel-title{font-size:15px;font-weight:bold}",
        ".tick,.legend{font-size:11px}",
        ".grid{stroke:#ddd;stroke-width:1}",
        ".axis{stroke:#555;stroke-width:1}",
        ".series{fill:none;stroke-width:2.5}",
        "</style>",
        '<text x="550" y="32" text-anchor="middle" class="title">'
        "Separate chaining vs. load factor</text>",
    ]
    positions = ((65, 65), (565, 65), (65, 405), (565, 405))
    for (title, series), (x, y) in zip(chart_series, positions):
        svg.extend(_svg_panel(x, y, 450, 300, title, series, load_factors))
    svg.extend(
        [
            '<text x="550" y="750" text-anchor="middle" class="tick">'
            f"Load factor (entries / fixed capacity of {CAPACITY})</text>",
            "</svg>",
        ]
    )
    output_path.write_text("\n".join(svg) + "\n", encoding="utf-8")


def main() -> None:
    rows = []
    for quarter in LOAD_QUARTERS:
        load_factor = quarter / 4
        entries = CAPACITY * quarter // 4
        row = _measure(load_factor, entries)
        rows.append(row)
        print(
            f"load={load_factor:.2f} entries={entries} "
            f"avg_success={row['average_successful_comparisons']:.3f} "
            f"max_chain={row['max_chain_length']}"
        )

    output_directory = Path(__file__).resolve().parent
    csv_path = output_directory / "probe_results.csv"
    svg_path = output_directory / "probe_results.svg"
    columns = [
        "load_factor",
        "key_seed",
        "entries",
        "capacity",
        "average_chain_length",
        "max_chain_length",
        "average_successful_comparisons",
        "theoretical_successful_comparisons",
        "average_unsuccessful_comparisons",
        "theoretical_unsuccessful_comparisons",
        "average_successful_lookup_ns",
        "average_unsuccessful_lookup_ns",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file, fieldnames=columns, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    _write_svg(rows, svg_path)

    print(f"CSV: {csv_path}")
    print(f"SVG: {svg_path}")


if __name__ == "__main__":
    main()
