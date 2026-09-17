"""Read one project's normalized annotations; standard library only."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
project = 'PXD000004'
record = json.loads((root / 'annotations/normalized' / project / 'biological.json').read_text())
for entry in record['tissue']:
    print('Extracted:', entry['value'])
    if entry.get('is_normalized') is True:
        print('Mapped:', entry.get('ontology_id'), entry.get('ontology_name'))
    else:
        print('No accepted ontology mapping; do not substitute a candidate ID.')
    print('Evidence:', entry['evidence'])
    print('Normalization flags:', entry.get('normalization_qc_flags', []))
