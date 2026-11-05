#!/usr/bin/env python3
"""Manage local skill payloads without merging their Git repositories."""

import argparse
import ast
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import uuid


RECEIPT = '.skill-manager.json'
IGNORED = {'.git', '.idea', '.DS_Store', '__pycache__', '_vendor', '.venv', 'node_modules'}
MANAGER = 'local-agent-skills'


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def relative_path(value, allow_dot=False):
    path = PurePosixPath(value)
    if not isinstance(value, str) or path.is_absolute() or '..' in path.parts or (str(path) == '.' and not allow_dot):
        raise ValueError(f'Expected a relative resource path: {value!r}')
    return Path(str(path))


def skill_name(path):
    entry = path / 'SKILL.md'
    if not entry.is_file() or entry.is_symlink():
        return None
    text = entry.read_text(encoding='utf-8')
    frontmatter = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
    if not frontmatter:
        return None
    match = re.search(r'(?m)^name:\s*[\'\"]?([a-z0-9][a-z0-9-]*)[\'\"]?\s*$', frontmatter.group(1))
    return match.group(1) if match else None


def disk_files(root, ignore=()):
    result = {}
    if not root.is_dir():
        return result
    for directory, folders, files in os.walk(root, followlinks=False):
        for name in folders:
            if (Path(directory) / name).is_symlink() and name not in IGNORED:
                result[str((Path(directory) / name).relative_to(root))] = '<symlink>'
        folders[:] = sorted(name for name in folders if name not in IGNORED and not (Path(directory) / name).is_symlink())
        for name in sorted(files):
            if name in IGNORED or name in ignore or name.endswith(('.pyc', '.pyo')):
                continue
            path = Path(directory) / name
            result[str(path.relative_to(root))] = '<symlink>' if path.is_symlink() else sha256(path)
    return result


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + '.pending-' + uuid.uuid4().hex)
    try:
        pending.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)


def remove_owned(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


class Workspace:
    def __init__(self, manifest, roots=None, state_dir=None):
        self.manifest_path = Path(manifest).resolve()
        self.root = self.manifest_path.parent
        self.config = load_json(self.manifest_path)
        if self.config.get('schema_version') != 1:
            raise ValueError('Unsupported manifest schema_version')
        self.skills = self.config['skills']
        self.repositories = self.config['repositories']
        self.state = Path(state_dir).expanduser().absolute() if state_dir else self.root / '.state'
        self.roots = {}
        self.git_cache = {}
        for name, platform in self.config['platforms'].items():
            override = (roots or {}).get(name)
            environment = platform.get('environment')
            value = override or (os.environ.get(environment) if environment else None) or platform['default_root']
            self.roots[name] = Path(value).expanduser().absolute()
        for name, definition in self.skills.items():
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', name):
                raise ValueError(f'Invalid skill name: {name}')
            self.source(name)
            for platform in definition['platforms']:
                if platform not in self.roots:
                    raise ValueError(f'Unknown platform for {name}: {platform}')

    def repository(self, name):
        key = self.skills[name]['repository']
        path = self.root / relative_path(self.repositories[key]['path'])
        if path.resolve().parent != self.root.resolve():
            raise ValueError(f'Repository must be a direct workspace child: {path}')
        return path

    def source(self, name):
        repository = self.repository(name)
        source = repository / relative_path(self.skills[name]['source'], allow_dot=True)
        if not source.resolve().is_relative_to(repository.resolve()):
            raise ValueError(f'Skill source escapes its repository: {source}')
        return source

    def git_info(self, name):
        repository = self.repository(name)
        key = str(repository)
        if key not in self.git_cache:
            def run(*arguments, optional=False):
                result = subprocess.run(['git', '-C', str(repository), *arguments],
                                        capture_output=True, text=True)
                if result.returncode and not optional:
                    raise ValueError(f'Cannot read Git state in {repository}: {result.stderr.strip()}')
                return result.stdout.strip()
            self.git_cache[key] = {
                'repository': self.skills[name]['repository'],
                'commit': run('rev-parse', 'HEAD'),
                'branch': run('rev-parse', '--abbrev-ref', 'HEAD'),
                'dirty': bool(run('status', '--porcelain=v1')),
                'remote': run('config', '--get', 'remote.origin.url', optional=True),
            }
        return self.git_cache[key]

    def payload(self, name, platform):
        definition, source = self.skills[name], self.source(name)
        if platform not in definition['platforms']:
            raise ValueError(f'{name} does not support {platform}')
        if skill_name(source) != name:
            raise ValueError(f'SKILL.md does not declare {name}: {source}')
        files = {}
        for resource in definition['resources']:
            resource = {'source': resource, 'target': resource} if isinstance(resource, str) else resource
            if platform not in resource.get('platforms', definition['platforms']):
                continue
            origin = source / relative_path(resource['source'])
            target = relative_path(resource['target'])
            if not origin.exists() or origin.is_symlink() or not origin.resolve().is_relative_to(source.resolve()):
                raise ValueError(f'Missing or unsafe resource: {origin}')
            members = sorted(origin.rglob('*')) if origin.is_dir() else [origin]
            for member in members:
                relative = member.relative_to(origin) if origin.is_dir() else Path('.')
                if any(part in IGNORED for part in relative.parts) or member.name.endswith(('.pyc', '.pyo')):
                    continue
                if member.is_symlink():
                    raise ValueError(f'Symbolic links are not installed as skill resources: {member}')
                if not member.is_file():
                    continue
                destination = str(target / relative)
                if destination in files:
                    raise ValueError(f'Duplicate payload destination: {destination}')
                files[destination] = member
        return files

    def selection(self, names, platform='all', dependencies=False):
        names = list(names or self.skills)
        unknown = set(names) - set(self.skills)
        if unknown:
            raise ValueError('Unknown skills: ' + ', '.join(sorted(unknown)))
        ordered, visiting = [], set()
        def add(name):
            if name in visiting:
                raise ValueError(f'Dependency cycle involving {name}')
            if name in ordered:
                return
            visiting.add(name)
            if dependencies:
                for dependency in self.skills[name].get('dependencies', []):
                    add(dependency['name'])
            visiting.remove(name)
            ordered.append(name)
        for name in names:
            add(name)
        result = []
        for name in ordered:
            for target in self.skills[name]['platforms']:
                if platform == 'all' or target == platform:
                    result.append((name, target))
        if not result:
            raise ValueError('No selected skills support the requested platform')
        return result

    def target(self, name, platform):
        return self.roots[platform] / 'skills' / name

    def ignored_markers(self, name):
        marker = self.skills[name].get('compatibility_marker', {})
        return {RECEIPT, marker.get('path', '')}

    def legacy_status(self, name, platform):
        if platform != 'codex' or not self.skills[name].get('codex_legacy'):
            return {}
        files = {key: sha256(path) for key, path in self.payload(name, platform).items() if key != 'SKILL.md'}
        root = self.roots[platform]
        legacy = root / 'prompts/doc-to-html'
        prompt = root / 'prompts/doc-to-html.md'
        agents = root / 'AGENTS.md'
        entry = self.source(name) / 'codex/doc-to-html.prompt.md'
        content = agents.read_text() if agents.is_file() else ''
        updater = ast.parse((self.source(name) / 'scripts/update_codex_agents.py').read_text())
        block = next((ast.literal_eval(node.value) for node in updater.body
                      if isinstance(node, ast.Assign) and any(isinstance(item, ast.Name) and item.id == 'BLOCK' for item in node.targets)), '')
        managed_block = bool(block and block in content and content.count('<!-- doc-to-html:start -->') == 1
                             and content.count('<!-- doc-to-html:end -->') == 1)
        return {
            'resources_match': not legacy.is_symlink() and disk_files(legacy) == files,
            'prompt_matches': prompt.is_file() and not prompt.is_symlink() and sha256(prompt) == sha256(entry),
            'agents_entry_present': managed_block,
        }

    def status(self, name, platform):
        payload = {key: sha256(path) for key, path in self.payload(name, platform).items()}
        target = self.target(name, platform)
        record = None
        differences = {'missing': [], 'modified': [], 'unexpected': []}
        if target.is_symlink():
            state = 'symlink'
        elif not target.exists():
            state = 'missing'
        elif not target.is_dir() or skill_name(target) != name:
            state = 'foreign'
        else:
            installed = disk_files(target, self.ignored_markers(name))
            differences = {
                'missing': sorted(set(payload) - set(installed)),
                'modified': sorted(key for key in set(payload) & set(installed) if payload[key] != installed[key]),
                'unexpected': sorted(set(installed) - set(payload)),
            }
            receipt = target / RECEIPT
            try:
                record = load_json(receipt) if receipt.is_file() else None
            except (ValueError, OSError):
                record = None
            if installed != payload:
                state = 'different'
            elif record is None:
                state = 'unrecorded'
            elif record.get('manager') != MANAGER or record.get('name') != name or record.get('files') != payload:
                state = 'record_stale'
            else:
                state = 'ok'
        info = dict(self.git_info(name))
        legacy = self.legacy_status(name, platform)
        if state == 'ok' and legacy and not all(legacy.values()):
            state = 'legacy_different'
        return {
            'name': name, 'platform': platform, 'target': str(target), 'status': state,
            'source': info, 'payload_sha256': fingerprint(payload),
            'installed_source': record.get('source') if record else None, 'legacy': legacy, 'differences': differences,
        }

    def dependency_report(self, selection):
        result = []
        for name, platform in selection:
            for dependency in self.skills[name].get('dependencies', []):
                dependency_name = dependency['name']
                state = self.status(dependency_name, platform)['status']
                result.append({'skill': name, 'platform': platform, **dependency,
                               'status': state, 'available': state in {'ok', 'unrecorded', 'record_stale'}})
        return result

    def validate_target(self, target, name=None):
        if target.is_symlink():
            raise ValueError(f'Refusing to replace a symbolic link: {target}')
        resolved = target.resolve()
        for repository in self.repositories.values():
            source = (self.root / relative_path(repository['path'])).resolve()
            if resolved == source or resolved in source.parents or source in resolved.parents:
                raise ValueError(f'Installation target overlaps a source repository: {target}')
        if name and target.exists() and (not target.is_dir() or skill_name(target) != name):
            raise ValueError(f'Existing destination is not the expected skill {name}: {target}')

    def marker(self, name, files):
        definition = self.skills[name].get('compatibility_marker')
        if not definition:
            return None
        version = definition.get('version')
        if 'version_file' in definition:
            tree = ast.parse((self.source(name) / relative_path(definition['version_file'])).read_text())
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == definition['version_constant'] for target in node.targets):
                    version = ast.literal_eval(node.value)
                    break
            if version is None:
                raise ValueError(f'Cannot read installer version for {name}')
        record = {'name': name, 'version': version}
        if definition.get('installer'):
            record.update(installer=definition['installer'], installedAt=timestamp())
        if definition.get('file_hashes'):
            record['files'] = files
        return definition['path'], record

    def agents_content(self, name):
        source = self.source(name) / 'scripts/update_codex_agents.py'
        spec = importlib.util.spec_from_file_location('skill_workspace_agents_updater', source)
        module = importlib.util.module_from_spec(spec)
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous
        target = self.roots['codex'] / 'AGENTS.md'
        with tempfile.TemporaryDirectory(prefix='skill-agents-') as directory:
            copy = Path(directory) / 'AGENTS.md'
            if target.exists():
                copy.write_bytes(target.read_bytes())
            module.update_agents(copy)
            return copy.read_bytes()

    def plan(self, selection):
        operations = []
        for name, platform in selection:
            state = self.status(name, platform)
            target = self.target(name, platform)
            self.validate_target(target, name)
            info = self.git_info(name)
            if state['status'] == 'ok' and state['installed_source'] == info:
                continue
            files = self.payload(name, platform)
            operations.append({'name': name, 'platform': platform, 'target': target,
                               'kind': 'directory', 'files': files, 'receipt': True, 'reason': state['status']})
            if platform == 'codex' and self.skills[name].get('codex_legacy'):
                root = self.roots[platform]
                legacy_files = {key: value for key, value in files.items() if key != 'SKILL.md'}
                operations.append({'name': name, 'platform': platform, 'target': root / 'prompts/doc-to-html',
                                   'kind': 'directory', 'files': legacy_files, 'receipt': False, 'reason': 'legacy resources'})
                operations.append({'name': name, 'platform': platform, 'target': root / 'prompts/doc-to-html.md',
                                   'kind': 'file', 'data': (self.source(name) / 'codex/doc-to-html.prompt.md').read_bytes(), 'reason': 'legacy prompt'})
                operations.append({'name': name, 'platform': platform, 'target': root / 'AGENTS.md',
                                   'kind': 'file', 'data': self.agents_content(name), 'reason': 'managed AGENTS entry'})
        targets = set()
        for operation in operations:
            target = operation['target']
            self.validate_target(target)
            if operation['kind'] == 'file' and target.exists() and not target.is_file():
                raise ValueError(f'Expected a regular file: {target}')
            if target.resolve() in targets:
                raise ValueError(f'Duplicate installation destination: {target}')
            targets.add(target.resolve())
        ordered_targets = sorted(targets)
        for index, target in enumerate(ordered_targets):
            if any(target in other.parents or other in target.parents for other in ordered_targets[index + 1:]):
                raise ValueError('Installation destinations must not overlap')
        return operations

    def build(self, operation):
        target = operation['target']
        target.parent.mkdir(parents=True, exist_ok=True)
        if operation['kind'] == 'absent':
            return None
        if operation.get('restore_from'):
            origin = operation['restore_from']
            if operation['kind'] == 'directory':
                stage = Path(tempfile.mkdtemp(prefix=f'.{target.name}-stage-', dir=target.parent))
                shutil.copytree(origin, stage, dirs_exist_ok=True, symlinks=True)
            else:
                descriptor, filename = tempfile.mkstemp(prefix=f'.{target.name}-stage-', dir=target.parent)
                os.close(descriptor)
                stage = Path(filename)
                shutil.copy2(origin, stage)
            return stage
        if operation['kind'] == 'file':
            descriptor, filename = tempfile.mkstemp(prefix=f'.{target.name}-stage-', dir=target.parent)
            os.close(descriptor)
            stage = Path(filename)
            stage.write_bytes(operation['data'])
            stage.chmod((target.stat().st_mode & 0o777) if target.exists() else 0o644)
            return stage
        stage = Path(tempfile.mkdtemp(prefix=f'.{target.name}-stage-', dir=target.parent))
        try:
            stage.chmod((target.stat().st_mode & 0o777) if target.exists() else 0o755)
            hashes = {}
            for relative, origin in operation['files'].items():
                destination = stage / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origin, destination)
                hashes[relative] = sha256(origin)
                if sha256(destination) != hashes[relative]:
                    raise ValueError(f'Source changed while staging: {origin}')
            cache = self.skills[operation['name']].get('runtime_cache')
            if cache:
                candidates = [self.source(operation['name']) / cache, target / cache]
                runtime = next((path for path in candidates if path.is_dir() and not path.is_symlink()), None)
                if runtime:
                    shutil.copytree(runtime, stage / cache, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
            if operation.get('receipt'):
                marker = self.marker(operation['name'], hashes)
                if marker:
                    write_json(stage / marker[0], marker[1])
                write_json(stage / RECEIPT, {
                    'schema_version': 1, 'manager': MANAGER, 'name': operation['name'],
                    'platform': operation['platform'], 'installed_at': timestamp(),
                    'source': self.git_info(operation['name']),
                    'payload_sha256': fingerprint(hashes), 'files': hashes,
                })
            operation['expected_hashes'] = hashes
            return stage
        except BaseException:
            remove_owned(stage)
            raise

    @contextmanager
    def lock(self):
        self.state.mkdir(parents=True, exist_ok=True)
        with (self.state / 'manager.lock').open('a') as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ValueError('Another skill manager operation is running') from error
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def transaction(self, operations, kind='sync', restores=None):
        if not operations:
            return {'changed': [], 'backup_id': None}
        run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex[:6]
        backup = self.state / 'backups' / run_id
        backup.mkdir(parents=True, mode=0o700)
        journal = {'schema_version': 1, 'id': run_id, 'kind': kind, 'restores': restores,
                   'state': 'preparing', 'created_at': timestamp(), 'entries': []}
        staged, installed = [], []
        try:
            for index, operation in enumerate(operations):
                target = operation['target']
                self.validate_target(target)
                existed = target.exists()
                saved = backup / str(index)
                if existed:
                    if target.is_dir():
                        shutil.copytree(target, saved, symlinks=True)
                    else:
                        shutil.copy2(target, saved)
                journal['entries'].append({
                    'target': str(target), 'platform': operation['platform'], 'name': operation['name'],
                    'kind': 'directory' if existed and target.is_dir() else 'file' if existed else 'absent',
                    'backup': str(index) if existed else None,
                })
                write_json(backup / 'backup.json', journal)
                stage = self.build(operation)
                staged.append((operation, stage))
            for operation, stage in staged:
                if operation.get('expected_hashes') is not None:
                    current = {key: sha256(path) for key, path in operation['files'].items()}
                    if current != operation['expected_hashes']:
                        raise ValueError(f'Source changed during installation: {operation["name"]}')
            journal['state'] = 'applying'
            write_json(backup / 'backup.json', journal)
            for operation, stage in staged:
                target = operation['target']
                self.validate_target(target)
                stash = target.with_name(f'.{target.name}-previous-{uuid.uuid4().hex}') if target.exists() else None
                if stash is not None:
                    target.rename(stash)
                installed.append((target, stash))
                if stage is not None:
                    stage.rename(target)
            journal['state'] = 'complete'
            write_json(backup / 'backup.json', journal)
        except BaseException:
            for target, stash in reversed(installed):
                remove_owned(target)
                if stash is not None and stash.exists():
                    stash.rename(target)
            journal['state'] = 'rolled_back'
            write_json(backup / 'backup.json', journal)
            raise
        finally:
            for _, stage in staged:
                if stage is not None and stage.exists():
                    remove_owned(stage)
        for _, stash in installed:
            if stash is not None and stash.exists():
                remove_owned(stash)
        return {'changed': [str(operation['target']) for operation in operations], 'backup_id': run_id}

    def allowed_targets(self):
        targets = {self.target(name, platform) for name, definition in self.skills.items() for platform in definition['platforms']}
        if any(item.get('codex_legacy') for item in self.skills.values()):
            root = self.roots['codex']
            targets.update({root / 'prompts/doc-to-html', root / 'prompts/doc-to-html.md', root / 'AGENTS.md'})
        return targets

    def restore_plan(self, run_id):
        if not re.fullmatch(r'[A-Za-z0-9-]+', run_id):
            raise ValueError('Invalid backup identifier')
        backup = self.state / 'backups' / run_id
        journal = load_json(backup / 'backup.json')
        if journal.get('state') != 'complete':
            raise ValueError('Only completed transactions can be restored')
        operations = []
        for entry in journal['entries']:
            target = Path(entry['target'])
            if target not in self.allowed_targets():
                raise ValueError(f'Backup target is outside this configuration: {target}')
            self.validate_target(target)
            if target.is_dir() and 'skills' == target.parent.name and skill_name(target) != entry['name']:
                raise ValueError(f'Refusing to restore over another skill: {target}')
            operation = {key: entry[key] for key in ['name', 'platform', 'kind']}
            operation['target'] = target
            if entry['kind'] != 'absent':
                saved = backup / relative_path(entry['backup'])
                if not saved.exists() or saved.is_symlink():
                    raise ValueError(f'Backup payload is missing or unsafe: {saved}')
                operation['restore_from'] = saved
            operations.append(operation)
        return operations


def printable_plan(operations):
    return [{key: str(operation[key]) for key in ['name', 'platform', 'target', 'kind']}
            for operation in operations]


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ['list', 'status', 'check', 'install', 'update', 'sync', 'restore']:
        subparser = commands.add_parser(command)
        subparser.add_argument('--manifest', type=Path, default=Path(__file__).resolve().with_name('skills.json'))
        subparser.add_argument('--state-dir', type=Path)
        subparser.add_argument('--json', action='store_true')
        for platform in ['codex', 'claude', 'zcode']:
            subparser.add_argument(f'--{platform}-root', type=Path)
        if command != 'restore':
            subparser.add_argument('skills', nargs='*')
            subparser.add_argument('--platform', choices=['all', 'codex', 'claude', 'zcode'], default='all')
        else:
            subparser.add_argument('backup_id')
        if command in ['install', 'update', 'sync', 'restore']:
            subparser.add_argument('--dry-run', action='store_true')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        workspace = Workspace(args.manifest, {name: getattr(args, name + '_root') for name in ['codex', 'claude', 'zcode']}, args.state_dir)
        result, failed = {}, False
        if args.command == 'restore':
            if args.dry_run:
                result = {'dry_run': True, 'operations': printable_plan(workspace.restore_plan(args.backup_id))}
            else:
                with workspace.lock():
                    result = workspace.transaction(workspace.restore_plan(args.backup_id), 'restore', args.backup_id)
        elif args.command == 'list':
            names = list(dict.fromkeys(name for name, _ in workspace.selection(args.skills, args.platform)))
            result = {'skills': [{'name': name, 'repository': workspace.skills[name]['repository'],
                                  'source': str(workspace.source(name)), 'platforms': workspace.skills[name]['platforms'],
                                  'dependencies': workspace.skills[name].get('dependencies', [])} for name in names]}
        elif args.command in ['status', 'check']:
            selection = workspace.selection(args.skills, args.platform)
            reports = [workspace.status(name, platform) for name, platform in selection]
            dependencies = workspace.dependency_report(selection)
            failed = any(item['status'] != 'ok' for item in reports) or any(item['kind'] == 'required' and not item['available'] for item in dependencies)
            result = {'workspace': str(workspace.root), 'generated_at': timestamp(), 'ok': not failed,
                      'installations': reports, 'dependencies': dependencies}
        else:
            selection = workspace.selection(args.skills, args.platform, dependencies=True)
            if args.dry_run:
                result = {'dry_run': True, 'operations': printable_plan(workspace.plan(selection))}
            else:
                with workspace.lock():
                    result = workspace.transaction(workspace.plan(selection))
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif 'installations' in result:
            print(f'{"SKILL":24} {"PLATFORM":8} {"STATUS":18} {"SOURCE":14} TARGET')
            for item in result['installations']:
                source = item['source']['commit'][:9] + ('+dirty' if item['source']['dirty'] else '')
                print(f'{item["name"]:24} {item["platform"]:8} {item["status"]:18} {source:14} {item["target"]}')
            for item in result['dependencies']:
                print(f'Dependency: {item["skill"]} -> {item["name"]} ({item["platform"]}, {item["kind"]}, {item["status"]})')
        elif 'skills' in result:
            for item in result['skills']:
                print(f'{item["name"]:24} {item["repository"]:26} {", ".join(item["platforms"])}')
        elif 'operations' in result:
            for item in result['operations']:
                print(f'DRY RUN {item["name"]} [{item["platform"]}]: {item["target"]}')
            if not result['operations']:
                print('No changes needed.')
        else:
            for target in result['changed']:
                print(f'Updated: {target}')
            print(f'Backup: {result["backup_id"]}' if result['backup_id'] else 'No changes needed.')
        return 1 if args.command == 'check' and failed else 0
    except (ValueError, OSError, KeyError, TypeError, SyntaxError) as error:
        if args.json:
            print(json.dumps({'error': str(error)}, ensure_ascii=False))
        else:
            print(f'Error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
