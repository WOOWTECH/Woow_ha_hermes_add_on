"""Verify the reviewed host adapter is complete, pinned and untampered."""
import ast
import hashlib
import json
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
vendor=root/'vendor/paseo'
pin=json.loads((vendor/'PROVENANCE.json').read_text())
assert pin['repository']=='https://github.com/WOOWTECH/hermes-paseo-plugin'
assert pin['commit']=='7b9c88d032672f688c88df222e384ce3bc1af2f2'
assert pin['version']=='0.1.5-rc.3'
assert set(pin['sha256'])=={'dashboard_control.py','profile_lifecycle.py','resource_limits.py','hermes'}
for name,digest in pin['sha256'].items():
 data=(vendor/name).read_bytes()
 assert hashlib.sha256(data).hexdigest()==digest,name+' differs from reviewed source'
 if name.endswith('.py'):ast.parse(data)
assert 'MIT License' in (vendor/'LICENSE').read_text()
dockerfile=(root/'Dockerfile').read_text()
assert 'COPY --chmod=0555 vendor/paseo/hermes /opt/hermes/.venv/bin/hermes' in dockerfile
assert 'vendor/paseo/dashboard_control.py vendor/paseo/profile_lifecycle.py vendor/paseo/resource_limits.py /opt/hermes-paseo-dashboard-control/' in dockerfile
assert 'HERMES_PASEO_INGRESS_ORIGIN' in (vendor/'dashboard_control.py').read_text()
docs=(root/'DOCS.md').read_text()
assert '7b9c88d032672f688c88df222e384ce3bc1af2f2 --enable' in docs
assert '84e0c41ce91594908a53c91fcff09123ca92f626 --enable' in docs
assert '0.11.2-r3-523d451cc096' in docs
for command in re.findall(r'hermes plugins install WOOWTECH/hermes-(?:paseo|omnigent)-plugin[^\n`]*',docs):
 assert '--force' not in command
print('Paseo host provenance and packaging: ok')
