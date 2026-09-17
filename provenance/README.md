# Provenance notes

`release.json` identifies the source run, model snapshot and retained framework
commit. `annotation_files.tsv` records both original and release paths/hashes;
the original paths are relative to the textmining repository, not a cluster mount.

`pipeline_snapshot/` is a copy of the retained production-pipeline source from
the manuscript-control experiment. Every selected source file was checked against
that experiment's recorded SHA-256 hash before copying. Cluster project prefixes,
where present in code or comments, were replaced with `${HAMLET_ROOT}`. Original
and release hashes and transformations are recorded in `pipeline_files.tsv`.
The upstream license is retained in the snapshot. Its generic defaults are not
the production command-line/model settings; consult the explicit model configs.

`prompts/*_effective.txt` reconstruct the map-operation prompt by applying the
frozen runner's default-rule removal and multi-value overlay. They are not filled
per-paper prompts or raw API requests. The runner and base YAML remain available
to inspect the transformation, schema overrides and request construction.

`input_manifest.tsv` contains section-availability metadata and hashes, verified
against the retained source-comparison input hashes. It does not redistribute
inputs. `truncation_events.tsv` retains any recorded main-shard truncation events;
an empty event table is not proof that no unlogged preprocessing occurred.

`ontology_versions.tsv` honestly marks unavailable historical snapshot versions.
It enumerates configured resources, not evidence that every resource contributed
an accepted mapping. Candidate mappings and ambiguity diagnostics remain in JSON.

`environment/recorded_host_packages.json` is explicitly dated to the retained
staircase environment snapshot, not asserted to be the exact later production
environment. `environment/production_compute.json` summarizes the production
and repair allocation accounting, excluding input preparation and index building.
