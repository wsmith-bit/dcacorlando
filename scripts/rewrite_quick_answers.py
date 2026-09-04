"""Rewrite the Quick Answer paragraph on every hvac-repair/fl/*/*/index.html page.

Replaces the templated two-sentence skeleton (fixed opener + fixed parts-lead-time
closer, city name swapped in) with one of 12 structurally distinct paragraph shapes,
assigned per county via a stable round-robin so cities in the same county don't share
a shape unless the county has more cities than shapes (12).

Usage:
    python scripts/rewrite_quick_answers.py --dry-run [file ...]
    python scripts/rewrite_quick_answers.py [file ...]

With no file arguments, operates on every hvac-repair/fl/*/*/index.html page.
"""
import argparse
import glob
import re
import sys
import zlib
from collections import defaultdict

HEADING_RE = re.compile(r"\U0001F4CD Directions to ([^,]+), FL")
EYEBROW_RE = re.compile(r'<span class="eyebrow">Proudly Serving [^&]+&amp; ([A-Za-z ]+)</span>')
HIDDEN_RE = re.compile(
    r'(<div class="quick-answer" style="display:none;" id="quick-answer" aria-hidden="true">'
    r'<p class="text-slate-700">)(.*?)(</p></div>)',
    re.DOTALL,
)
BODY_RE = re.compile(
    r'(<div class="qa-body"><p class="text-slate-700">)(.*?)(</p></div>)',
    re.DOTALL,
)

SHAPES = [
    "HVAC Repair in {city}, {county} County starts with a technician diagnosing the issue on site, scoping the repair, and pricing it before any work begins. Special-order parts are the only thing that can extend that timeline, depending on component type and supplier stock.",
    "A technician diagnoses the issue on site and confirms pricing before work starts on HVAC Repair in {city}. Ordered or specialty parts are the exception — they push the timeline out depending on what's in stock.",
    "Need HVAC Repair in {city}? A technician inspects the system first, then locks in the scope and price before touching anything. The only variable is parts — special-order components can add to that timeline.",
    "Homeowners and businesses across {county} County, including {city}, get a diagnosis, a defined repair scope, and a confirmed price before HVAC Repair work starts. Specialty parts are the one factor that can extend that timeline, depending on availability.",
    "The process for HVAC Repair in {city} is simple: on-site diagnosis, scope confirmed, price locked in, then the work starts. Specialty or back-ordered parts are the exception, adding time based on supplier stock.",
    "DC/AC Air Conditioning And Heating diagnoses HVAC Repair issues in {city} on site and confirms the price before starting work. When a part must be special-ordered, the wait depends on component type and current supplier stock.",
    "If your system in {city} needs HVAC Repair, expect an on-site diagnosis and a confirmed price before work begins. Only special-order parts change that timeline, and that depends on supplier availability.",
    "Expect a straightforward process for HVAC Repair in {city}, {county} County: diagnosis, scope, and price — all confirmed before work starts. Lead time only shifts if a part needs to be special-ordered.",
    "In {city}, {county} County, a technician evaluates the HVAC system on site before any repair work is scoped or priced — nothing starts until you've approved the estimate. The exception is special-order parts, which extend the timeline.",
    "Before repair work begins in {city}, expect an on-site diagnosis and a locked-in price. Parts that have to be special-ordered are the only variable, and that depends on what's currently in stock.",
    "{city} customers get the same process every time: technician diagnoses on site, scope gets defined, price gets confirmed, then work starts. Only special-order parts change the timeline.",
    "Repairing HVAC systems in {city} starts with an honest, on-site diagnosis — followed by a defined scope and a price you approve before anything else happens. Special-order parts are the sole reason that timeline would stretch.",
]


def extract_city_county(text, path):
    m = HEADING_RE.search(text)
    if not m:
        raise ValueError(f"{path}: could not find directions heading for city name")
    city = m.group(1)

    m = EYEBROW_RE.search(text)
    if not m:
        raise ValueError(f"{path}: could not find eyebrow tag for county name")
    county = m.group(1).strip()

    return city, county


def assign_shapes(city_county_pairs):
    """city_county_pairs: list of (path, city, county). Returns {path: shape_index}."""
    by_county = defaultdict(list)
    for path, city, county in city_county_pairs:
        by_county[county].append((path, city))

    assignment = {}
    for county, entries in by_county.items():
        entries = sorted(entries, key=lambda e: e[1])  # sort by city name
        seed = zlib.crc32(county.encode("utf-8"))
        order = list(range(len(SHAPES)))
        # deterministic shuffle of shape order, seeded per county
        rng_state = seed
        for i in range(len(order) - 1, 0, -1):
            rng_state = (rng_state * 1103515245 + 12345) & 0x7FFFFFFF
            j = rng_state % (i + 1)
            order[i], order[j] = order[j], order[i]

        for idx, (path, city) in enumerate(entries):
            shape_idx = order[idx % len(order)]
            assignment[path] = shape_idx

    return assignment


def render(shape_idx, city, county):
    return SHAPES[shape_idx].format(city=city, county=county)


def process(path, dry_run, shape_idx, city, county):
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    new_text = render(shape_idx, city, county)

    hidden_match = HIDDEN_RE.search(content)
    body_match = BODY_RE.search(content)
    if not hidden_match or not body_match:
        raise ValueError(f"{path}: could not find both quick-answer blocks")

    old_hidden = hidden_match.group(2)
    old_body = body_match.group(2)

    new_content = HIDDEN_RE.sub(lambda m: m.group(1) + new_text + m.group(3), content, count=1)
    new_content = BODY_RE.sub(lambda m: m.group(1) + new_text + m.group(3), new_content, count=1)

    changed = new_content != content

    if dry_run:
        print(f"\n=== {path} (shape {shape_idx + 1}) ===")
        print(f"OLD: {old_hidden[:120]}...")
        print(f"NEW: {new_text}")
    elif changed:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_content)

    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()

    paths = args.files or sorted(glob.glob("hvac-repair/fl/*/*/index.html")) + ["index.html"]

    city_county_pairs = []
    texts = {}
    for path in paths:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        texts[path] = text
        city, county = extract_city_county(text, path)
        city_county_pairs.append((path, city, county))

    assignment = assign_shapes(city_county_pairs)

    changed_count = 0
    for path, city, county in city_county_pairs:
        shape_idx = assignment[path]
        if process(path, args.dry_run, shape_idx, city, county):
            changed_count += 1

    print(f"\n{'Would change' if args.dry_run else 'Changed'} {changed_count}/{len(paths)} files")


if __name__ == "__main__":
    main()
