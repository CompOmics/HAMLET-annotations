# HAMLET annotations

**Local release candidate — not yet published or licensed.**

Project-level experimental metadata for **1,737 PRIDE projects**, extracted
from manuscript abstracts, available methods sections, and PRIDE descriptors
and processing protocols using Qwen.

The release covers **38 fields** across biological, technical and
experimental-design agents: **5,211 raw and 5,211 normalized JSON files**.
“Raw” means structured output before ontology normalization, not proteomics
raw data. Original annotations are preserved byte-for-byte.

## Contents

```text
annotations/          Raw and normalized annotations, organized by PXD
metadata/             Project manifest, field dictionary, schema and checksums
quality_control/      Stored flags, summaries, format exceptions and recovery records
provenance/           Input hashes, model settings, frozen prompts and pipeline source
scripts/              Validation and export utilities
examples/             Minimal annotation-reading example
```

For each project, `annotations/normalized/PXD000004/` contains
`biological.json`, `technical.json` and `experimental_design.json`.
The same layout under `annotations/raw/` contains pre-normalization outputs.

## Quick start

Reading and exporting require only Python's standard library:

```bash
python examples/read_annotations.py
python scripts/export_flat_table.py --output exports/normalized.tsv
```

The exporter writes one row per value/evidence pair, preserves unknowns and
diagnostics, and handles the legacy formats retained in repaired records.
JSON remains the authoritative representation.

## Interpreting annotations

- `value` is the extracted term; `evidence` contains its supporting text.
  An `inferred:` prefix identifies an inferred value.
- When `is_normalized` is true, use `ontology_id` and `ontology_name` for
  the accepted mapping. Candidate IDs are not accepted mappings.
- `unknown` means no value was provided, not biological absence.
- Similarity and confidence scores are not calibrated probabilities.
  QC flags are warnings, not automatic grounds for removing values.

Multiple values are allowed, but list positions across fields do **not**
establish sample-level relationships. These are automated project annotations,
not manually verified ground truth or sample-resolved SDRFs. Packaging did not
filter values or rerun extraction, normalization or QC.

## Provenance and validation

The production run used `Qwen/Qwen3.8-27B`, BF16 and vLLM 0.27.1, with
one B300 per server. Settings, input hashes, frozen prompts and recovery records
are retained; see [provenance notes](provenance/README.md) for details and
limitations, including missing historical ontology versions.

Full manuscripts, model weights, ontology indices, caches and exploratory runs
are excluded. Evidence excerpts remain in the annotations.

To verify file inventory, schemas, source hashes, QC references and checksums:

```bash
python -m pip install -r requirements.txt
python scripts/validate_release.py
```

These checks establish structural integrity, not scientific correctness.
The extraction codebase is [CompOmics/textmining](https://github.com/CompOmics/textmining).

## Before publication

Confirm the dataset/code licenses, review evidence-excerpt redistribution, and
complete the author list and archival citation in `CITATION.cff`.
Publication identifiers and historical ontology versions remain documented gaps.
No remote repository or public release has been configured.
