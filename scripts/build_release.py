"""Build a local release candidate from retained textmining outputs.

Requires PyYAML. Never runs a model, edits source outputs, or contacts a service.
Refuses to replace an existing annotation tree.
"""
import argparse
import ast
import csv
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from annotation_io import entries, representation

ROOT = Path(__file__).resolve().parents[1]
RUN = 'qwen3_8_27b_abstract_methods_pride_protocols_multivalue_1737'
AGENTS = {'biological': 'BiologicalAgent', 'technical': 'TechnicalAgent',
          'experimental_design': 'ExperimentalDesignAgent'}
PROMPTS = {'biological': 'pipeline_biological.yaml', 'technical': 'pipeline_technical.yaml',
           'experimental_design': 'pipeline_experimental.yaml'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def dump(relative, data):
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def table(relative, rows, columns=None):
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns or list(rows[0]), delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)


def read_table(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def main():
    import yaml
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--textmining-root', required=True, type=Path)
    parser.add_argument('--resume', action='store_true', help='Verify/reuse identical partial copies; never overwrite annotation data.')
    args = parser.parse_args()
    source = args.textmining_root.resolve()
    if (ROOT / 'annotations').exists() and not args.resume:
        raise SystemExit('Refusing to overwrite annotations. Use a new release directory.')
    production = source / 'framework/production_outputs' / RUN
    control = source / 'final_analyses/PRIDEContextGain1737/manuscript_control_1737'
    frozen = control / 'framework'
    provenance = json.loads((control / 'provenance.json').read_text())
    definitions = {}
    # Retain base prompts AND the actual multi-value overlay logic.
    runner_path = frozen / 'docetl_pipeline/run_docetl.py'
    runner_text = runner_path.read_text()
    overrides = [node.value.value for node in ast.walk(ast.parse(runner_text))
                 if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                 and isinstance(node.value.value, str)
                 and any(isinstance(t, ast.Name) and t.id == 'override' for t in node.targets)
                 and 'MULTI-VALUE OUTPUT FORMAT' in node.value.value]
    assert len(overrides) == 1
    (ROOT / 'provenance/prompts').mkdir(parents=True, exist_ok=True)
    (ROOT / 'provenance/prompts/multivalue_overlay.txt').write_text(overrides[0])
    fields = {}
    for agent, filename in PROMPTS.items():
        config = yaml.safe_load((frozen / 'docetl_pipeline' / filename).read_text())
        op = next(op for op in config['operations'] if op['type'] == 'map')
        fields[agent] = list(op['output']['schema'])
        for field in fields[agent]:
            match = re.search(r'^\s*- ' + re.escape(field) + r':\s*(.+)$', op['prompt'], re.M)
            definitions[field] = match[1] if match else 'See retained extraction prompt.'
        effective = re.sub(r'\n\s*DEFAULT VALUE RULES:.*?(?=\n\s*MULTI-COHORT STUDIES:)',
                           '\n', op['prompt'], flags=re.S) + overrides[0]
        (ROOT / f'provenance/prompts/{agent}_effective.txt').write_text(effective)
    assert sum(map(len, fields.values())) == 38
    table('metadata/field_dictionary.tsv', [dict(agent=agent, field=field,
          definition_from_base_prompt=definitions[field], cardinality='one_or_more_entries; occasional legacy [value,evidence] pair',
          unknown_representation='[{"value":"unknown","evidence":""}]',
          scope='project-level; not a sample or raw-file assignment',
          prompt_precedence='effective prompt includes multi-value override; consult it for operative rules')
          for agent in AGENTS for field in sorted(fields[agent])])

    copied_sources = []
    # Frozen source is evidence for reproduction, not an independently runnable workflow.
    selected = [p for directory in ('docetl_pipeline', 'normalization', 'validation', 'core', 'agents')
                for p in (frozen / directory).glob('*.py') if p.name != 'integration_agent.py']
    selected += [frozen / 'docetl_pipeline' / name for name in PROMPTS.values()]
    selected += [frozen / 'configs/qwen3_8_27b_vllm.yaml',
                 frozen / 'configs/qwen3_8_27b_vllm_repair.yaml', frozen / 'config.yaml']
    for path in selected:
        relative = path.relative_to(frozen).as_posix()
        original_hash = digest(path)
        assert original_hash == provenance['frozen_hashes'][relative], relative
        dest = ROOT / 'provenance/pipeline_snapshot' / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        original = path.read_text()
        cleaned = original.replace(str(source.parent), '${HAMLET_ROOT}')
        dest.write_text(cleaned)
        copied_sources.append(dict(source_repository='CompOmics/textmining',
            source_path=path.relative_to(source).as_posix(), source_sha256=original_hash,
            release_path=dest.relative_to(ROOT).as_posix(), release_sha256=digest(dest),
            transformation='internal project prefix replaced' if original != cleaned else 'none'))
    table('provenance/pipeline_files.tsv', copied_sources)
    shutil.copyfile(ROOT / 'provenance/pipeline_snapshot/configs/qwen3_8_27b_vllm.yaml',
                    ROOT / 'provenance/model_config.yaml')
    shutil.copyfile(ROOT / 'provenance/pipeline_snapshot/configs/qwen3_8_27b_vllm_repair.yaml',
                    ROOT / 'provenance/repair_model_config.yaml')
    norm_tree = ast.parse((frozen / 'normalization/config.py').read_text())
    ontology_map = next(ast.literal_eval(node.body) for node in ast.walk(norm_tree)
                        if isinstance(node, ast.Lambda) and isinstance(node.body, ast.Dict)
                        and any(isinstance(k, ast.Constant) and k.value == 'cl' for k in node.body.keys))
    table('provenance/ontology_versions.tsv', [dict(ontology=key, configured_file=value,
          version='not_recorded_in_frozen_provenance',
          note='Configured resource; historical ontology/index snapshot identity is not verified')
          for key, value in ontology_map.items()])
    # Preserve the upstream license separately; do not select a data license.
    license_dest = ROOT / 'provenance/pipeline_snapshot/UPSTREAM_LICENSE'
    shutil.copyfile(source / 'LICENSE', license_dest)
    env_source = source / 'final_analyses/Staircase/outputs/test/qwen3_8_27b/job_940301/llm_stuff-pip-freeze.txt'
    wanted = {'docetl', 'litellm', 'torch', 'transformers', 'faiss-cpu', 'spacy',
              'negspacy', 'numpy', 'pydantic', 'PyYAML', 'jsonschema'}
    packages = {}
    for line in env_source.read_text().splitlines():
        if '==' in line:
            name, version = line.split('==', 1)
            if name in wanted: packages[name] = version
    dump('provenance/environment/recorded_host_packages.json', dict(packages=packages,
         source=env_source.relative_to(source).as_posix(), source_sha256=digest(env_source),
         caveat='Recorded host llm_stuff environment from 2026-08-25 staircase job; not a production-job or container pip freeze.'))
    performance = source / 'final_analyses/ComputationalPerformance/summary.json'
    if performance.exists():
        summary = json.loads(performance.read_text())
        dump('provenance/environment/production_compute.json', dict(
            main=summary['full_context_main'], recovery=summary['full_context_repair'],
            gpu='NVIDIA B300 SXM6 AC', allocated_cpu_units_per_task=32,
            allocated_host_ram_gib_per_task=256,
            note='Allocation time includes failed tasks/startup, not GPU kernel utilization; shard jobs were staggered.'))
    truncations = []
    for path in sorted(production.glob('shard_*/truncations.tsv')):
        for row in read_table(path):
            truncations.append(dict(shard=path.parent.name, **row))
    table('provenance/truncation_events.tsv', truncations,
          ['shard', 'pxd', 'model', 'removed_tokens', 'from_agent'])

    repair_rows = read_table(source / 'repair_inputs/qwen3_8_27b_protocols_multivalue_1737_missing/task_manifest.tsv')
    repairs = {}
    recovery = []
    for row in repair_rows:
        agent = next(k for k, v in AGENTS.items() if v == row['agent_dir'])
        merge = json.loads((production / 'repair_status_protocols_multivalue' / f"merge-task_{row['task_id']}.json").read_text())
        assert merge['status'] == 'merged'
        for pxd in row['pxd_ids'].split(','):
            repairs[pxd, agent] = row['task_id']
            recovery.append(dict(pxd=pxd, agent=agent, original_shard=row['original_shard'],
                repair_task=row['task_id'], timeout_seconds=1800, merge_status=merge['status']))
    assert len(recovery) == 41
    table('quality_control/recovery_manifest.tsv', recovery)

    original_inputs = {r['pxd']: r for r in read_table(source / 'docetl_inputs_abstract_methods_pride_protocols/manifest.tsv')}
    with (control / 'input_manifest.csv').open() as handle:
        recorded_hashes = {r['pxd']: r['source_sha256'] for r in csv.DictReader(handle)}
    source_files, dataset_rows, input_rows, qc_rows, flags, formats = [], [], [], [], [], []
    totals = Counter()
    annotation_bytes = 0
    seen = set()
    for shard in sorted(production.glob('shard_*')):
        for bio in sorted((shard / 'BiologicalAgent').glob('*.json')):
            pxd = bio.name.split('_')[0]
            assert re.fullmatch(r'PXD\d{6}', pxd) and pxd not in seen
            seen.add(pxd)
            project_stats = Counter()
            outpaths = {}
            for tier in ('raw', 'normalized'):
                for agent, directory in AGENTS.items():
                    parent = shard / directory if tier == 'raw' else shard / 'NormalizedAgent' / directory
                    matches = list(parent.glob(f'{pxd}_*.json'))
                    assert len(matches) == 1, (pxd, agent, tier)
                    path = matches[0]
                    data = path.read_bytes()
                    assert str(source.parent).encode() not in data, f'Internal path in {path}'
                    record = json.loads(data)
                    assert {k for k in record if not k.startswith('_')} == set(fields[agent]), path
                    dest = ROOT / 'annotations' / tier / pxd / f'{agent}.json'
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if dest.exists():
                        assert dest.read_bytes() == data, f'Refusing to overwrite different data: {dest}'
                    else:
                        dest.write_bytes(data)
                    sha = hashlib.sha256(data).hexdigest()
                    assert digest(dest) == sha
                    rel = dest.relative_to(ROOT).as_posix()
                    outpaths[f'{tier}_{agent}'] = rel
                    source_files.append(dict(pxd=pxd, tier=tier, agent=agent,
                        source_path=path.relative_to(source).as_posix(), source_sha256=sha,
                        release_path=rel, release_sha256=sha, bytes=len(data)))
                    annotation_bytes += len(data)
                    for field in fields[agent]:
                        if representation(record[field]) != 'object_list':
                            formats.append(dict(pxd=pxd, tier=tier, agent=agent, field=field,
                                representation=representation(record[field]), annotation_path=rel))
                    if tier != 'normalized':
                        continue
                    for key in ('_evidence_grounding_flags', '_hallucination_flags'):
                        for index, flag in enumerate(record.get(key, [])):
                            flags.append(dict(pxd=pxd, agent=agent, field=flag.get('field', '') if isinstance(flag, dict) else '',
                                entry_index='', category=key, flag_json=json.dumps(flag, ensure_ascii=False),
                                annotation_path=rel, json_pointer=f'/{key}/{index}'))
                            project_stats[key] += 1
                    for field in fields[agent]:
                        for index, entry in enumerate(entries(record[field])):
                            assert isinstance(entry.get('value'), str) and isinstance(entry.get('evidence'), str)
                            project_stats['entries'] += 1
                            if entry['value'].strip().lower() == 'unknown':
                                project_stats['unknown_entries'] += 1
                            else:
                                project_stats['known_entries'] += 1
                                if not entry['evidence'].strip(): project_stats['known_entries_without_evidence'] += 1
                                if entry['evidence'].lower().startswith('inferred:'): project_stats['inferred_entries'] += 1
                            if entry.get('is_normalized') is True: project_stats['mapped_entries'] += 1
                            for n, flag in enumerate(entry.get('normalization_qc_flags', [])):
                                pointer = f'/{field}' if isinstance(record[field], dict) else f'/{field}/{index}'
                                flags.append(dict(pxd=pxd, agent=agent, field=field, entry_index=index,
                                    category='normalization_qc_flags', flag_json=json.dumps(flag, ensure_ascii=False),
                                    annotation_path=rel, json_pointer=f'{pointer}/normalization_qc_flags/{n}'))
                                project_stats['normalization_qc_flags'] += 1
            count_flags = sum(project_stats[k] for k in ('_evidence_grounding_flags', '_hallucination_flags', 'normalization_qc_flags'))
            meta = original_inputs[pxd]
            input_path = source / 'docetl_inputs_abstract_methods_pride_protocols' / f'{pxd}.txt'
            input_hash = digest(input_path)
            assert input_hash == recorded_hashes[pxd], f'Input hash changed: {pxd}'
            input_rows.append(dict(pxd=pxd, input_sha256=input_hash,
                abstract_source_label=meta['abstract_source'], has_abstract=meta['has_abstract'],
                has_methods=meta['has_methods'], has_pride_properties=meta['includes_pride_properties'],
                has_pride_sample_processing=meta['includes_pride_sample_processing'],
                has_pride_data_processing=meta['includes_pride_data_processing'],
                abstract_chars=meta['abstract_chars'], methods_chars=meta['methods_chars'],
                pride_properties_chars=meta['pride_properties_chars'],
                pride_sample_processing_chars=meta['pride_sample_processing_chars'],
                pride_data_processing_chars=meta['pride_data_processing_chars'],
                source_url=f'https://www.ebi.ac.uk/pride/archive/projects/{pxd}',
                manuscript_text_distributed=False))
            repaired = [a for a in AGENTS if (pxd, a) in repairs]
            dataset_rows.append(dict(pxd=pxd, shard=shard.name, completion_status='complete_3_raw_3_normalized',
                qc_summary='flags_present' if count_flags else 'no_stored_flags',
                stored_flag_count=count_flags, repaired_agents=';'.join(repaired),
                publication_identifiers='', publication_identifier_status='not_in_retained_input_manifest',
                **outpaths))
            qc_rows.append(dict(pxd=pxd, stored_flags=count_flags,
                **{k: project_stats[k] for k in ('entries', 'known_entries', 'unknown_entries', 'mapped_entries',
                   'inferred_entries', 'known_entries_without_evidence', '_evidence_grounding_flags',
                   '_hallucination_flags', 'normalization_qc_flags')}))
            totals.update(project_stats)
    assert len(seen) == 1737
    table('metadata/dataset_manifest.tsv', sorted(dataset_rows, key=lambda r: r['pxd']))
    table('provenance/input_manifest.tsv', sorted(input_rows, key=lambda r: r['pxd']))
    table('provenance/annotation_files.tsv', source_files)
    table('quality_control/project_summary.tsv', sorted(qc_rows, key=lambda r: r['pxd']))
    table('quality_control/flags.tsv', flags)
    table('quality_control/format_exceptions.tsv', formats,
          ['pxd', 'tier', 'agent', 'field', 'representation', 'annotation_path'])
    # Keep all fields, including optional normalization diagnostics, without imposing a score cutoff.
    entry_properties = {key: {'type': 'string'} for key in ('value', 'evidence', 'ontology_id', 'ontology_name',
        'normalization_method', 'normalization_matched_text', 'synonym_scope')}
    entry_properties.update(is_normalized={'type': 'boolean'}, similarity={'type': 'number'})
    entry_properties.update({key: {'type': 'array'} for key in ('normalization_candidate_ids',
                             'normalization_qc_flags', 'ontology_taxon_constraints')})
    defs = {'entry': {'type': 'object', 'required': ['value', 'evidence'],
                     'properties': entry_properties, 'additionalProperties': False}}
    for agent, names in fields.items():
        props = {name: {'oneOf': [
            {'type': 'array', 'minItems': 1, 'items': {'$ref': '#/$defs/entry'}},
            {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': {'type': 'string'}},
            {'$ref': '#/$defs/entry'}
        ]} for name in names}
        props.update(_confidence={'type': 'object'}, _evidence_grounding_flags={'type': 'array'},
                     _hallucination_flags={'type': 'array'})
        defs[agent] = {'type': 'object', 'required': names, 'properties': props, 'additionalProperties': False}
    dump('metadata/annotation_schema.json', {'$schema': 'https://json-schema.org/draft/2020-12/schema',
        'title': 'HAMLET project-level agent annotations, release candidate 0.1.0', '$defs': defs,
        'oneOf': [{'$ref': '#/$defs/' + agent} for agent in AGENTS]})
    dump('provenance/release.json', dict(status='local_release_candidate_not_published', version='0.1.0-rc1',
        built_at=datetime.now(timezone.utc).isoformat(), source_repository='https://github.com/CompOmics/textmining',
        source_run=RUN, projects=len(seen), raw_files=len(seen)*3, normalized_files=len(seen)*3,
        annotation_bytes=annotation_bytes, fields=fields, totals=dict(totals),
        model='Qwen/Qwen3.8-27B', model_snapshot='1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0',
        precision='BF16', vllm_version='0.27.1', gpus_per_server=1, gpu='NVIDIA B300 SXM6 AC',
        tensor_parallel_size=1, max_model_len=65536, gpu_memory_utilization=0.70,
        main_timeout_seconds=600, repair_timeout_seconds=1800, main_array='960300', repair_array='961580',
        frozen_source_commit=provenance['framework_commit'],
        frozen_source_caveat='Retained manuscript-control copy identified as the production pipeline; not a contemporaneous per-request snapshot of every production job.',
        recovered_agent_records=len(recovery), repaired_projects=len({r['pxd'] for r in recovery}),
        legacy_format_fields=len(formats),
        transformations='Annotation JSON copied byte-for-byte; agent filenames standardized; no values filtered or re-normalized.',
        publication_blockers=['Choose data and code licenses and confirm evidence excerpt redistribution.',
          'Confirm citation authors and archival DOI.', 'Historical ontology/index versions are not recorded.',
          'Publication identifiers not populated from the retained input manifest.']))
    print(json.dumps({'projects':len(seen), 'annotation_files':len(source_files),
                     'annotation_bytes':annotation_bytes, 'flags':len(flags), 'totals':dict(totals)}, indent=2))


if __name__ == '__main__':
    main()
