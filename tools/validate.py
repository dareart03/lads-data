"""Check the merged files against the JSON Schemas in schemas/.

Run it after merge.py. It exits with an error code if anything is wrong, so
the GitHub Actions workflow can use it to reject a bad pull request.

Usage:
    python tools/merge.py
    python tools/validate.py
"""
import sys

from jsonschema import Draft202012Validator

from common import REPO_ROOT, load_json

SCHEMAS = REPO_ROOT / "schemas"
DIST = REPO_ROOT / "tools" / "dist" / "data"

# merged file -> (schema file, field that names a record in messages,
#                 whether names must be unique in the file)
FILES = {
    "memories.json": ("memory.schema.json", "name", True),
    "banners.json": ("banner.schema.json", "name", True),
    "achievements.json": ("achievement.schema.json", "title", True),
    # recurring events legitimately repeat their name (one row per period)
    "events.json": ("events.schema.json", "name", False),
    "rotations.json": ("rotations.schema.json", None, False),
    # single documents (one object, not a list of records)
    "upgrade_costs.json": ("upgrade_costs.schema.json", None, False),
    "icons.json": ("icons.schema.json", None, False),
}
MAX_ERRORS_PER_FILE = 20


def check_file(data_file, schema_file, label_field, unique_names):
    data = load_json(DIST / data_file)
    if data is None:
        return [f"{data_file}: not found (run merge.py first)"]
    validator = Draft202012Validator(load_json(SCHEMAS / schema_file))
    problems = []
    # rotations.json is one document, not a list of records
    records = data if isinstance(data, list) else [data]
    for index, record in enumerate(records):
        if isinstance(record, dict) and label_field:
            label = record.get(label_field, f"record #{index}")
        else:
            label = data_file
        for error in validator.iter_errors(record):
            where = ".".join(str(p) for p in error.path) or "(record)"
            problems.append(f"{data_file}: '{label}' {where}: {error.message}")
    # names must be unique inside one file
    if unique_names and isinstance(data, list):
        names = [r.get(label_field) for r in data if isinstance(r, dict)]
        for name in sorted({n for n in names if names.count(n) > 1}):
            problems.append(f"{data_file}: duplicate {label_field} '{name}'")
    print(f"{data_file}: {len(records)} record(s), {len(problems)} problem(s)")
    return problems


def main():
    all_problems = []
    for data_file, (schema_file, label_field, unique_names) in FILES.items():
        all_problems += check_file(data_file, schema_file, label_field, unique_names)
    if all_problems:
        print(f"\n{len(all_problems)} problem(s):")
        for line in all_problems[:MAX_ERRORS_PER_FILE * len(FILES)]:
            print("  -", line)
        sys.exit(1)
    print("\nAll files are valid.")


if __name__ == "__main__":
    main()
