#!/usr/bin/env python3
"""Run package tests and exercise every declared installation in isolated roots."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def invoke(arguments, cwd=ROOT):
    completed = subprocess.run(arguments, cwd=cwd, capture_output=True, text=True, timeout=180)
    if completed.returncode:
        raise RuntimeError('Command failed: ' + ' '.join(str(item) for item in arguments) +
                           '\n' + completed.stdout + completed.stderr)
    return completed


def check_installations():
    with tempfile.TemporaryDirectory(prefix='agent-skills-check-') as directory:
        scratch = Path(directory)
        roots = {name: scratch / name for name in ['codex', 'claude', 'zcode']}
        options = ['--state-dir', str(scratch / 'state')]
        for platform, path in roots.items():
            options.extend([f'--{platform}-root', str(path)])
        manager = [sys.executable, str(ROOT / 'manage.py')]
        result = json.loads(invoke([*manager, 'sync', *options, '--json']).stdout)
        checked = json.loads(invoke([*manager, 'check', *options, '--json']).stdout)
        if not checked['ok']:
            raise ValueError('Installed resources do not match their source packages')
        repeat = json.loads(invoke([*manager, 'sync', *options, '--dry-run', '--json']).stdout)
        if repeat['operations']:
            raise ValueError('A repeated installation would unexpectedly change resources')
        helpers = [
            ('doc-to-html', 'scripts/md2html.py'),
            ('interaction-flow', 'scripts/render_flow.py'),
            ('spec2testplan', 'scripts/spec2testplan.py'),
            ('extract-test-points', 'scripts/testpoint_formatter.py'),
            ('generate-test-cases', 'scripts/xmind_generator.py'),
            ('test-handoff', 'scripts/render_form.py'),
        ]
        for name, relative in helpers:
            invoke([sys.executable, str(roots['codex'] / 'skills' / name / relative), '--help'])
        cases = scratch / 'cases.json'
        cases.write_text(json.dumps({'test_cases': [{
            '用例ID': 'TC-SMOKE-001', '用例标题': 'Synthetic installation check',
            '测试点ID': 'TP-SMOKE-001', '需求ID': 'REQ-SMOKE-001',
            '设计方法': 'EP', '优先级': 'P1',
            '步骤': [{'操作': 'Run the installed generator', '预期': 'Create a readable XMind file'}],
        }]}), encoding='utf-8')
        xmind = scratch / 'cases.xmind'
        invoke([sys.executable, str(roots['codex'] / 'skills/generate-test-cases/scripts/xmind_generator.py'),
                '--input', str(cases), '--output', str(xmind)])
        with zipfile.ZipFile(xmind) as archive:
            if archive.testzip() is not None or b'TC-SMOKE-001' not in archive.read('content.xml'):
                raise ValueError('Generated XMind content is invalid or missing traceability')
        return {'installations': len(checked['installations']), 'helpers': len(helpers),
                'idempotent': True, 'xmind_generated': True,
                'backup_created': bool(result['backup_id'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    suites = [
        ('manager', ROOT),
        ('doc-to-html', ROOT / 'doc2html-skill'),
        ('interaction-flow', ROOT / 'interaction-flow'),
        ('spec2testplan', ROOT / 'spec2testplan-skill'),
        ('test-handoff', ROOT / 'test-handoff'),
    ]
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'suites': []}
    try:
        for name, directory in suites:
            print('Checking ' + name + '...', flush=True)
            completed = invoke([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=directory)
            output = completed.stdout + completed.stderr
            count = re.search(r'Ran (\d+) tests?', output)
            if count is None:
                raise ValueError('No test summary was produced by ' + name)
            report['suites'].append({'name': name, 'tests': int(count.group(1)), 'passed': True})
            print('  ' + count.group(1) + ' tests passed.', flush=True)
        print('Checking isolated platform installations...', flush=True)
        report['integration'] = check_installations()
        report['tests_passed'] = sum(item['tests'] for item in report['suites'])
        report['ok'] = True
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
