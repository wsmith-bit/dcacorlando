"""Standardize the driving-directions <ol> on every hvac-repair/fl/*/*/index.html page
onto the generic, non-fabricated fallback text already live on 13 of the 61 pages:

    Head toward {City}, FL from the nearest major highway
    Follow GPS navigation for precise turn-by-turn directions
    Arrive in {City}, FL

Replaces hand-written turn-by-turn text with invented street names. Does not touch the
"I-75:" label above the list, the "Get Detailed Directions" link, or the Maps embed --
those need real per-city routing data (later, API-driven work), not this interim pass.

Usage:
    python scripts/standardize_directions_fallback.py --dry-run [file ...]
    python scripts/standardize_directions_fallback.py [file ...]

With no file arguments, operates on every hvac-repair/fl/*/*/index.html page.
"""
import argparse
import glob
import re

HEADING_RE = re.compile(r"\U0001F4CD Directions to ([^,]+), FL")
OL_RE = re.compile(
    r'(<ol style="font-size:0\.9rem;color:#64748b;line-height:1\.7;margin:0;'
    r'padding-left:1\.5rem;">)(.*?)(</ol>)',
    re.DOTALL,
)

FALLBACK_TEMPLATE = (
    "\n              \n"
    '              <li style="margin-bottom:0.5rem;">Head toward {city}, FL from the nearest major highway</li>\n'
    '              <li style="margin-bottom:0.5rem;">Follow GPS navigation for precise turn-by-turn directions</li>\n'
    '              <li style="margin-bottom:0.5rem;">Arrive in {city}, FL</li>\n'
    "            "
)


def process(path, dry_run):
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    heading_match = HEADING_RE.search(content)
    if not heading_match:
        raise ValueError(f"{path}: could not find directions heading for city name")
    city = heading_match.group(1)

    ol_match = OL_RE.search(content)
    if not ol_match:
        raise ValueError(f"{path}: could not find directions <ol> block")

    new_inner = FALLBACK_TEMPLATE.format(city=city)
    already_correct = ol_match.group(2) == new_inner

    new_content = OL_RE.sub(
        lambda m: m.group(1) + new_inner + m.group(3), content, count=1
    )
    changed = new_content != content

    if dry_run:
        status = "already standardized" if already_correct else "WOULD CHANGE"
        print(f"{path}: {status} (city={city})")
    elif changed:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_content)

    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()

    paths = args.files or sorted(glob.glob("hvac-repair/fl/*/*/index.html"))

    changed_count = 0
    for path in paths:
        if process(path, args.dry_run):
            changed_count += 1

    print(f"\n{'Would change' if args.dry_run else 'Changed'} {changed_count}/{len(paths)} files")


if __name__ == "__main__":
    main()
