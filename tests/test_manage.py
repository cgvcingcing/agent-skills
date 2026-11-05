"""Exercise updates and recovery using disposable repositories and agent roots."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('local_skill_manager', PROJECT / 'manage.py')
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='skill-manager-test-')
        self.root = Path(self.temporary.name)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.roots = {name: self.root / name for name in ['codex', 'claude', 'zcode']}
        self.config = {
            'schema_version': 1, 'repositories': {},
            'platforms': {name: {'default_root': str(path)} for name, path in self.roots.items()},
            'skills': {},
        }
        for name in ['alpha', 'beta']:
            source = self.workspace / name
            source.mkdir()
            (source / 'SKILL.md').write_text(f'---\nname: {name}\ndescription: Test skill\n---\n\nTest.\n')
            (source / 'scripts').mkdir()
            (source / 'scripts/run.py').write_text('print("original")\n')
            (source / '.gitignore').write_text('__pycache__/\nscripts/_vendor/\n')
            self.initialize_repository(source)
            self.config['repositories'][name] = {'path': name, 'url': 'https://example.invalid/' + name}
            self.config['skills'][name] = {
                'repository': name, 'source': '.', 'platforms': ['codex', 'claude'],
                'resources': ['SKILL.md', 'scripts'],
            }
        self.manifest = self.workspace / 'skills.json'
        self.save_manifest()

    def tearDown(self):
        self.temporary.cleanup()

    def initialize_repository(self, source):
        for arguments in [
            ['init', '-q'], ['add', '.'],
            ['-c', 'user.name=Skill Manager Tests', '-c', 'user.email=tests@example.invalid', 'commit', '-qm', 'Fixture'],
            ['remote', 'add', 'origin', 'https://example.invalid/' + source.name],
        ]:
            subprocess.run(['git', '-C', str(source), *arguments], check=True, capture_output=True)

    def save_manifest(self):
        self.manifest.write_text(json.dumps(self.config))

    def context(self):
        return manager.Workspace(self.manifest, self.roots)

    def sync(self, names=None, platform='codex'):
        workspace = self.context()
        with workspace.lock():
            return workspace.transaction(workspace.plan(workspace.selection(names, platform, dependencies=True)))

    def test_install_is_complete_and_second_sync_is_empty(self):
        result = self.sync(['alpha'])
        target = self.roots['codex'] / 'skills/alpha'
        self.assertEqual('ok', self.context().status('alpha', 'codex')['status'])
        receipt = manager.load_json(target / manager.RECEIPT)
        self.assertEqual(receipt['files'], manager.disk_files(target, {manager.RECEIPT}))
        self.assertNotIn(str(self.root), json.dumps(receipt))
        self.assertTrue(result['backup_id'])
        self.assertEqual([], self.sync(['alpha'])['changed'])

    def test_preview_does_not_create_state_or_agent_directories(self):
        workspace = self.context()
        plan = workspace.plan(workspace.selection(['alpha'], 'codex'))
        self.assertEqual(1, len(plan))
        self.assertFalse(workspace.state.exists())
        self.assertFalse(self.roots['codex'].exists())

    def test_source_and_installed_modifications_are_detected(self):
        self.sync(['alpha'])
        source = self.workspace / 'alpha/scripts/run.py'
        source.write_text('print("new source")\n')
        self.assertEqual('different', self.context().status('alpha', 'codex')['status'])
        self.sync(['alpha'])
        target = self.roots['codex'] / 'skills/alpha/scripts/run.py'
        self.assertEqual(source.read_text(), target.read_text())
        self.assertTrue(self.context().status('alpha', 'codex')['installed_source']['dirty'])
        target.write_text('print("edited installation")\n')
        self.assertEqual('different', self.context().status('alpha', 'codex')['status'])

    def test_update_backup_and_restore_preserve_local_installation_edits(self):
        self.sync(['alpha'])
        target = self.roots['codex'] / 'skills/alpha/scripts/run.py'
        target.write_text('print("local content to preserve")\n')
        result = self.sync(['alpha'])
        self.assertEqual('print("original")\n', target.read_text())
        workspace = self.context()
        with workspace.lock():
            restored = workspace.transaction(workspace.restore_plan(result['backup_id']), 'restore', result['backup_id'])
        self.assertEqual('print("local content to preserve")\n', target.read_text())
        self.assertTrue(restored['backup_id'])

    def test_restore_removes_installations_that_were_initially_absent(self):
        result = self.sync(['alpha'])
        workspace = self.context()
        workspace.transaction(workspace.restore_plan(result['backup_id']), 'restore', result['backup_id'])
        self.assertFalse((self.roots['codex'] / 'skills/alpha').exists())

    def test_failed_second_replacement_rolls_back_all_targets(self):
        self.sync(['alpha', 'beta'])
        for name in ['alpha', 'beta']:
            (self.workspace / name / 'scripts/run.py').write_text('print("updated")\n')
        original = Path.rename
        failure = {'triggered': False}
        def rename(path, target):
            if path.name.startswith('.beta-stage-') and not failure['triggered']:
                failure['triggered'] = True
                raise OSError('Injected replacement failure')
            return original(path, target)
        workspace = self.context()
        with mock.patch.object(Path, 'rename', rename):
            with self.assertRaisesRegex(OSError, 'Injected'):
                workspace.transaction(workspace.plan(workspace.selection(['alpha', 'beta'], 'codex')))
        self.assertTrue(failure['triggered'])
        for name in ['alpha', 'beta']:
            target = self.roots['codex'] / 'skills' / name / 'scripts/run.py'
            self.assertEqual('print("original")\n', target.read_text())
        self.assertFalse(list(self.roots['codex'].rglob('*stage-*')))
        self.assertFalse(list(self.roots['codex'].rglob('*previous-*')))

    def test_unrelated_directory_is_never_overwritten(self):
        target = self.roots['codex'] / 'skills/alpha'
        target.mkdir(parents=True)
        (target / 'notes.txt').write_text('Keep me')
        workspace = self.context()
        with self.assertRaisesRegex(ValueError, 'not the expected skill'):
            workspace.plan(workspace.selection(['alpha'], 'codex'))
        self.assertEqual('Keep me', (target / 'notes.txt').read_text())

    def test_symbolic_link_target_is_never_replaced(self):
        target = self.roots['codex'] / 'skills/alpha'
        target.parent.mkdir(parents=True)
        target.symlink_to(self.workspace / 'alpha', target_is_directory=True)
        workspace = self.context()
        with self.assertRaisesRegex(ValueError, 'symbolic link'):
            workspace.plan(workspace.selection(['alpha'], 'codex'))
        self.assertTrue(target.is_symlink())

    def test_dependency_selection_and_status(self):
        self.config['skills']['beta']['dependencies'] = [{'name': 'alpha', 'kind': 'recommended'}]
        self.save_manifest()
        workspace = self.context()
        selection = workspace.selection(['beta'], 'codex', dependencies=True)
        self.assertEqual([('alpha', 'codex'), ('beta', 'codex')], selection)
        dependency = workspace.dependency_report([('beta', 'codex')])[0]
        self.assertFalse(dependency['available'])
        self.sync(['beta'])
        self.assertTrue(self.context().dependency_report([('beta', 'codex')])[0]['available'])

    def test_missing_resource_fails_before_any_installation(self):
        (self.workspace / 'beta/SKILL.md').unlink()
        workspace = self.context()
        with self.assertRaisesRegex(ValueError, 'SKILL.md'):
            workspace.plan(workspace.selection(['alpha', 'beta'], 'codex'))
        self.assertFalse(self.roots['codex'].exists())

    def test_runtime_cache_is_preserved_but_not_part_of_content_identity(self):
        self.config['skills']['alpha']['runtime_cache'] = 'scripts/_vendor'
        self.save_manifest()
        cache = self.workspace / 'alpha/scripts/_vendor'
        cache.mkdir()
        (cache / 'runtime.py').write_text('runtime = True\n')
        self.sync(['alpha'])
        installed = self.roots['codex'] / 'skills/alpha/scripts/_vendor/runtime.py'
        self.assertEqual('runtime = True\n', installed.read_text())
        installed.write_text('runtime = "locally cached"\n')
        self.assertEqual('ok', self.context().status('alpha', 'codex')['status'])

    def test_payload_mapping_and_platform_specific_resources(self):
        source = self.workspace / 'alpha'
        (source / 'reference.md').write_text('Shared reference')
        (source / 'metadata.yaml').write_text('name: Alpha\n')
        self.config['skills']['alpha']['resources'] += [
            {'source': 'reference.md', 'target': 'references/mapped.md'},
            {'source': 'metadata.yaml', 'target': 'agents/openai.yaml', 'platforms': ['codex']},
        ]
        self.save_manifest()
        self.sync(['alpha'], platform='all')
        codex = self.roots['codex'] / 'skills/alpha'
        claude = self.roots['claude'] / 'skills/alpha'
        self.assertTrue((codex / 'agents/openai.yaml').is_file())
        self.assertFalse((claude / 'agents/openai.yaml').exists())
        self.assertEqual('Shared reference', (claude / 'references/mapped.md').read_text())

    def test_source_directory_cannot_be_an_installation_target(self):
        roots = dict(self.roots, codex=self.workspace)
        workspace = manager.Workspace(self.manifest, roots)
        with self.assertRaisesRegex(ValueError, 'overlaps a source'):
            workspace.validate_target(self.workspace / 'alpha')

    def test_source_escape_is_rejected(self):
        self.config['skills']['alpha']['resources'].append('../beta/SKILL.md')
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'relative resource path'):
            self.context().payload('alpha', 'codex')

    def test_restore_rejects_tampered_target_paths(self):
        result = self.sync(['alpha'])
        workspace = self.context()
        path = workspace.state / 'backups' / result['backup_id'] / 'backup.json'
        journal = manager.load_json(path)
        journal['entries'][0]['target'] = str(self.root / 'unrelated')
        manager.write_json(path, journal)
        with self.assertRaisesRegex(ValueError, 'outside this configuration'):
            workspace.restore_plan(result['backup_id'])

    def add_doc_fixture(self):
        source = self.workspace / 'doc-repository'
        (source / 'scripts').mkdir(parents=True)
        (source / 'codex').mkdir()
        (source / 'SKILL.md').write_text('---\nname: doc-to-html\ndescription: Test\n---\n')
        (source / 'codex/doc-to-html.prompt.md').write_text('Legacy entry\n')
        (source / 'scripts/md2html.py').write_text('print("renderer")\n')
        shutil.copy2(PROJECT / 'doc2html-skill/scripts/update_codex_agents.py', source / 'scripts/update_codex_agents.py')
        self.initialize_repository(source)
        self.config['repositories']['doc-repository'] = {'path': source.name}
        self.config['skills']['doc-to-html'] = {
            'repository': 'doc-repository', 'source': '.', 'platforms': ['codex'],
            'resources': ['SKILL.md', 'scripts/md2html.py'], 'codex_legacy': True,
        }
        self.save_manifest()

    def test_doc_legacy_entries_preserve_global_rules_and_restore(self):
        self.add_doc_fixture()
        agents = self.roots['codex'] / 'AGENTS.md'
        agents.parent.mkdir()
        agents.write_text('Existing user rules.\n')
        result = self.sync(['doc-to-html'])
        self.assertTrue(agents.read_text().startswith('Existing user rules.\n'))
        self.assertIn('<!-- doc-to-html:start -->', agents.read_text())
        self.assertEqual('ok', self.context().status('doc-to-html', 'codex')['status'])
        self.assertEqual([], self.sync(['doc-to-html'])['changed'])
        workspace = self.context()
        workspace.transaction(workspace.restore_plan(result['backup_id']), 'restore', result['backup_id'])
        self.assertEqual('Existing user rules.\n', agents.read_text())
        self.assertFalse((self.roots['codex'] / 'prompts/doc-to-html.md').exists())

    def test_incomplete_managed_agents_block_prevents_all_changes(self):
        self.add_doc_fixture()
        agents = self.roots['codex'] / 'AGENTS.md'
        agents.parent.mkdir()
        agents.write_text('Existing rules.\n<!-- doc-to-html:start -->\n')
        workspace = self.context()
        with self.assertRaises(ValueError):
            workspace.plan(workspace.selection(['doc-to-html'], 'codex'))
        self.assertFalse((self.roots['codex'] / 'skills').exists())
        self.assertEqual('Existing rules.\n<!-- doc-to-html:start -->\n', agents.read_text())

    def test_cli_check_exit_status_and_json(self):
        arguments = ['python3', str(PROJECT / 'manage.py'), 'check', '--manifest', str(self.manifest), '--platform', 'codex', '--json']
        result = subprocess.run(arguments, capture_output=True, text=True)
        self.assertEqual(1, result.returncode)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.sync()
        result = subprocess.run(arguments, capture_output=True, text=True)
        self.assertEqual(0, result.returncode)
        self.assertTrue(json.loads(result.stdout)['ok'])


if __name__ == '__main__':
    unittest.main()
