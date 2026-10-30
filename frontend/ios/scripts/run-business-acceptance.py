#!/usr/bin/env python3
# [Input] Existing signed xctestrun, explicit test account and optional terminal password input.
# [Output] Normal-entry iOS acceptance logs with a temporary mode-0600 test configuration.
# [Pos] Acceptance harness; no credentials enter application sources, CLI arguments or stdout.
import argparse
import getpass
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--xctestrun', required=True, type=Path)
parser.add_argument('--device', required=True)
parser.add_argument('--account', required=True)
parser.add_argument('--test', required=True, action='append')
parser.add_argument('--result', required=True, type=Path)
parser.add_argument('--password', action='store_true', help='Read password without terminal echo')
parser.add_argument('--model-alias')
parser.add_argument('--prompt')
parser.add_argument('--expected-reply')
parser.add_argument('--stop-after-first-reply', action='store_true')
parser.add_argument('--thread-id')
parser.add_argument('--previous-reply')
args = parser.parse_args()
source = args.xctestrun.resolve(strict=True)
configuration = plistlib.loads(source.read_bytes())
target = configuration['InkMemoryTests']
environment = target.setdefault('EnvironmentVariables', {})
environment['INK_DREAM_TEST_EMAIL'] = args.account
for name, value in [('MODEL_ALIAS', args.model_alias), ('PROMPT', args.prompt), ('EXPECTED_REPLY', args.expected_reply), ('THREAD_ID', args.thread_id), ('PREVIOUS_REPLY', args.previous_reply)]:
    if value is not None:
        environment['INK_DREAM_TEST_' + name] = value
if args.stop_after_first_reply:
    environment['INK_DREAM_TEST_STOP_AFTER_FIRST_REPLY'] = 'true'
if args.password:
    environment['INK_DREAM_TEST_PASSWORD'] = getpass.getpass('Dream test account password (hidden): ')
descriptor, name = tempfile.mkstemp(prefix='.ink-rn-acceptance-', suffix='.xctestrun', dir=source.parent)
temporary = Path(name)
try:
    with os.fdopen(descriptor, 'wb') as stream:
        plistlib.dump(configuration, stream)
    command = ['xcodebuild', '-xctestrun', str(temporary), '-destination', 'id=' + args.device,
               '-resultBundlePath', str(args.result), '-parallel-testing-enabled', 'NO',
               '-collect-test-diagnostics', 'never']
    command.extend('-only-testing:InkMemoryTests/' + test for test in args.test)
    command.append('test-without-building')
    raise SystemExit(subprocess.run(command).returncode)
finally:
    temporary.unlink(missing_ok=True)
