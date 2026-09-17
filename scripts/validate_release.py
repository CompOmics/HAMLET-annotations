"""Validate the local release (requires jsonschema); no network or model calls."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def main():
    import jsonschema
    release = json.loads((ROOT / 'provenance/release.json').read_text())
    schema = json.loads((ROOT / 'metadata/annotation_schema.json').read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    validators = {agent: jsonschema.Draft202012Validator({**schema, 'oneOf': [{'$ref': '#/$defs/' + agent}]})
                  for agent in release['fields']}
    manifest = rows(ROOT / 'metadata/dataset_manifest.tsv')
    assert len(manifest) == release['projects'] == len({r['pxd'] for r in manifest})
    expected = set()
    for row in manifest:
        for tier in ('raw', 'normalized'):
            for agent in release['fields']:
                relative = row[f'{tier}_{agent}']
                assert relative == f"annotations/{tier}/{row['pxd']}/{agent}.json"
                expected.add(relative)
    actual = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'annotations').rglob('*.json')}
    assert actual == expected, ('Annotation inventory mismatch', len(actual), len(expected))
    provenance = rows(ROOT / 'provenance/annotation_files.tsv')
    assert {r['release_path'] for r in provenance} == expected and len(provenance) == len(expected)
    records = {}
    for row in provenance:
        path = ROOT / row['release_path']
        assert not path.is_symlink()
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == row['source_sha256'] == row['release_sha256']
        record = json.loads(data)
        validators[row['agent']].validate(record)
        records[row['release_path']] = record
    for row in rows(ROOT / 'quality_control/flags.tsv'):
        value = records[row['annotation_path']]
        for part in row['json_pointer'].lstrip('/').split('/'):
            value = value[int(part)] if isinstance(value, list) else value[part.replace('~1', '/').replace('~0', '~')]
        assert value == json.loads(row['flag_json'])
    from checksums import check
    check()
    print(f"PASS: {len(manifest):,} projects, {len(expected):,} annotation files; schema, source hashes, QC references and release checksums verified.")


if __name__ == '__main__':
    main()
