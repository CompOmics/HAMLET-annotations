# HAMLET annotations

**Local release candidate — not yet published or licensed.**

Project-level experimental metadata extracted from manuscript abstracts,
available materials/methods sections, and PRIDE project descriptors and
sample/data-processing protocols. This release packages the final Qwen run
for **1,737 PRIDE projects**, with **38 fields** across three extraction agents.

The dataset includes **5,211 raw and 5,211 normalized JSON files**. Here,
“raw” means the structured agent output before ontology normalization, not
unprocessed model responses or proteomics raw data. No inference or normalization
was rerun to prepare this release. Original JSON files are preserved byte-for-byte;
only their directory layout and filenames have changed.

## Start here

```text
annotations/normalized/PXD000004/biological.json
annotations/normalized/PXD000004/technical.json
annotations/normalized/PXD000004/experimental_design.json
```

The same layout under `annotations/raw/` provides the pre-normalization records.
`metadata/dataset_manifest.tsv` indexes every project and annotation file.

Read an example with Python (no external dependencies required):

```bash
python examples/read_annotations.py
```

Create a long-form table with one row per value/evidence pair:

```bash
python scripts/export_flat_table.py --output exports/normalized.tsv
python scripts/export_flat_table.py --project PXD000004 --output exports/PXD000004.tsv
```

Unknown entries are retained. Multiple values are never combined or expanded
into speculative cross-field combinations. Nested diagnostics and agent-level
metadata are retained in JSON columns. The source JSON remains authoritative.
Legacy `[value, evidence]` pairs and singleton normalized objects from repaired
records are preserved in the originals.
`quality_control/format_exceptions.tsv` lists those fields; the exporter reads
all three formats and labels the source representation explicitly.

## What each value means

| Property | Interpretation |
|---|---|
| `value` | Original extracted value; retained even when an ontology mapping exists. |
| `evidence` | Stored supporting text. An `inferred:` prefix marks an explicitly inferred value. Evidence can be flagged or absent. |
| `is_normalized` | Whether the normalizer accepted a mapping. Absence is not equivalent to a failed mapping: some fields are not ontology-normalized. |
| `ontology_id`, `ontology_name` | Accepted mapping when `is_normalized` is true. Use these together for ontology-based analyses. |
| `similarity` | Normalization match score, not a calibrated probability of correctness. |
| `normalization_method`, `normalization_matched_text` | Recorded matching route and matched lexical form. |
| `normalization_candidate_ids` | Candidate identifiers, not necessarily accepted mappings. |
| `normalization_qc_flags` | Stored mapping warnings, retained without removing values. |
| `_confidence` | Agent-level heuristic scores, not independently calibrated accuracy estimates. |
| `_evidence_grounding_flags`, `_hallucination_flags` | Stored extraction/QC warnings. Names are pipeline identifiers, not proof that a value is wrong. |

The exact string `unknown` means that the pipeline did not provide a value.
It does not mean the property is biologically absent. A field may contain
multiple value/evidence objects. List positions in different fields do **not**
establish sample-level relationships.

`metadata/field_dictionary.tsv` defines the 38 extraction fields. Its descriptions
come from the base prompts; the effective prompts apply the retained multi-value
override, including its restrictions on inference, default counts and PRIDE scope.

## Quality and scope

- This is an automatically generated, **project-level** annotation resource,
  not manually verified ground truth or a sample-resolved SDRF.
- Values, evidence, confidence metadata and warnings are preserved. No score
  threshold or QC flag was used to remove entries during packaging.
- `quality_control/flags.tsv` is a flattened view of flags already present in
  the normalized files, with JSON pointers back to the original locations.
  It does not rerun QC and does not double-count copies of the same metadata
  in raw and normalized files.
- Format exceptions are recorded separately. They are not silently rewritten or
  treated as incorrect scientific values.
- `quality_control/project_summary.tsv` includes known/unknown counts, mapped
  entries, missing evidence and stored flag counts. “No stored flags” is **not**
  a declaration of scientific correctness or successful execution of every QC
  component.
- `quality_control/recovery_manifest.tsv` identifies the 41 agent records
  handled by targeted recovery, including their 1,800-second timeout override.
- The production dataset contains all 1,737 projects, including PXD001017.
  The separate PRIDE-only comparison's exclusion of that project does not
  remove it from this production release.
- Draft SDRFs and sample/raw-file assignments are not distributed here.

## Inputs and provenance

`provenance/input_manifest.tsv` records prepared-input hashes, available
sections, original abstract-source labels and links to PRIDE projects. The
`abstract_source_label` is retained as recorded; a PRIDE-labelled abstract
block should not automatically be interpreted as a publisher abstract.
Publication identifiers were not included in the retained input manifest and
are explicitly marked as unpopulated rather than guessed.

Full manuscripts, prepared input text and PRIDE API response dumps are omitted.
**Annotation evidence excerpts are retained and need a redistribution review
before public release.** Input hashing verifies provenance but does not establish
that every input token reached the model; inspect any retained truncation events.

The final run used `Qwen/Qwen3.8-27B`, BF16, vLLM 0.27.1, one B300 per server,
tensor parallelism 1, a 65,536-token maximum sequence length and 0.70 GPU-memory
utilization. `provenance/model_config.yaml` retains the standard request
configuration; `repair_model_config.yaml` retains the recovery override.

The frozen pipeline source was recovered from the retained manuscript-control
copy documented as using the production pipeline. Its source commit and file
hashes are recorded. This is **not a contemporaneous per-request snapshot of
every production job**. The snapshot is for inspection and reproduction in the
main codebase, not an independently installed workflow. Generic defaults inside
the snapshot are overridden by the production configuration and command-line
settings; they are not evidence that another model generated this dataset.

`provenance/prompts/` contains both the multi-value override and reconstructed
effective prompts. Their document placeholders are unfilled; they contain no
manuscript inputs. Base YAML prompts and the runner that applies the override
are retained in `provenance/pipeline_snapshot/`.

`provenance/ontology_versions.tsv` lists the 19 configured ontology resources.
Historical ontology/index versions were **not recorded in the frozen provenance**;
they are marked as unknown. No current resource version has been substituted as
if it were the original one. Model files, ontology files and indices are omitted.

## Validation

Python 3.10 or newer is sufficient for the release utilities. Reading/exporting
needs only the standard library. Validation additionally needs `jsonschema`;
rebuilding needs `PyYAML`.

```bash
python -m pip install -r requirements.txt
python scripts/validate_release.py
```

Validation checks the complete project/file inventory, the JSON Schema, equality
with recorded source hashes, QC pointers and release payload checksums. It is
structural/integrity validation, **not scientific validation of extracted claims**.

To intentionally refresh payload checksums after editing release files:

```bash
python scripts/checksums.py --write
```

Do not refresh checksums merely to silence an unexplained mismatch.
Git metadata, Python caches and generated `exports/` are excluded. Source
annotation hashes are retained independently in `provenance/annotation_files.tsv`.

## Repository contents

```text
metadata/             Dataset manifest, field dictionary, schema and checksums
annotations/          Raw and normalized project annotations
quality_control/      Stored flags, project summaries and recovery manifest
provenance/           Input hashes, settings, source hashes and frozen prompts/code
scripts/              Build, validate, checksum and export utilities
examples/             Minimal annotation-reading example
```

The main extraction codebase is `https://github.com/CompOmics/textmining`.
Exploratory analyses, benchmark development runs, caches, containers and full
cluster logs are deliberately excluded from this dataset repository.

## Before publishing

1. Approve licenses for the dataset and code; replace the `LICENSE` notice and
   retain any required third-party attribution.
2. Review redistribution of evidence excerpts. No manuscript redistribution
   permission is implied by their presence in this local candidate.
3. Confirm the author list in `CITATION.cff`, the release version and archival DOI.
4. Decide whether to enrich publication identifiers and recover missing ontology
   snapshot provenance, or document those omissions in the public release.
5. Validate the frozen release, create an archive and publish it to the chosen
   repository/archive service. No remote repository is configured automatically.

`CHANGELOG.md` records intentional changes. Published releases should be versioned;
do not silently overwrite annotation values in an existing release.
