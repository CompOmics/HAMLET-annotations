"""Export one row per annotation entry without collapsing multiple values.

The JSON remains authoritative. Nested diagnostics are retained as JSON columns.
"""
import argparse
import csv
import json
import sys
from pathlib import Path
from annotation_io import entries as read_entries, representation

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tier', choices=['raw', 'normalized'], default='normalized')
    parser.add_argument('--project', help='Optional PXD accession')
    parser.add_argument('--output', type=Path, help='Output TSV; otherwise stdout')
    args = parser.parse_args()
    if args.project and not __import__('re').fullmatch(r'PXD\d{6}', args.project):
        parser.error('Expected PXD followed by six digits')
    columns = ['pxd', 'agent', 'field', 'entry_index', 'value', 'evidence', 'is_normalized',
               'ontology_id', 'ontology_name', 'similarity', 'normalization_method',
               'entry_json', 'agent_metadata_json', 'source_representation', 'annotation_path']
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        handle = args.output.open('x', newline='')  # Never overwrite an existing export.
    else:
        handle = sys.stdout
    try:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter='\t')
        writer.writeheader()
        pattern = f'{args.project or "PXD*"}/*.json'
        for path in sorted((ROOT / 'annotations' / args.tier).glob(pattern)):
            record = json.loads(path.read_text())
            metadata = {key: value for key, value in record.items() if key.startswith('_')}
            for field, entries in record.items():
                if field.startswith('_'):
                    continue
                for index, entry in enumerate(read_entries(entries)):
                    row = {key: entry.get(key, '') for key in columns}
                    row.update(pxd=path.parent.name, agent=path.stem, field=field, entry_index=index,
                               entry_json=json.dumps(entry, ensure_ascii=False),
                               agent_metadata_json=json.dumps(metadata, ensure_ascii=False),
                               source_representation=representation(entries),
                               annotation_path=path.relative_to(ROOT).as_posix())
                    writer.writerow(row)
    finally:
        if args.output:
            handle.close()


if __name__ == '__main__':
    main()
