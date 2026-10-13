#!/usr/bin/env python3
"""Docker-only synthetic smoke: real boot/s6 and kernel UID, no HA or provider.

Run on the CI runner with the freshly built image reference. Docker output and
container logs are captured, never printed (even on failure). Only fixed checks
are reported. The boot image is unmodified; a separate disposable container
replaces only the final CLI with an environment/UID oracle, not the wrappers,
with-contenv or s6-setuidgid. No host credentials or data are mounted.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import uuid

PYTHON = "/opt/hermes/.venv/bin/python"
TOKENS = ("SUPERVISOR_TOKEN", "HASSIO_TOKEN")


def docker(*args, check=True, timeout=90):
    result = subprocess.run(["docker", *args], capture_output=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError("docker operation failed (output withheld)")
    return result


def main(image):
    names = ["ha-boundary-" + uuid.uuid4().hex for _ in range(2)]
    with tempfile.TemporaryDirectory(prefix="ha-boundary-") as temp:
        root = pathlib.Path(temp)
        root.chmod(0o755)
        # This oracle is the ONLY substituted executable. No real CLI/model runs.
        probe = root / "probe"
        probe.write_text('''#!/opt/hermes/.venv/bin/python
import os, sys
assert os.getuid() == int(sys.argv[1])
assert os.getgid() == int(sys.argv[1])
assert not any(k in os.environ for k in ("SUPERVISOR_TOKEN", "HASSIO_TOKEN"))
assert os.environ.get("BOUNDARY_KEEP") == "synthetic-preserved"
assert sys.argv[2:] == ["", "two words", "$(not-a-command)"]
raise SystemExit(42)
''')
        probe.chmod(0o755)
        options = root / "options.json"
        options.write_text(json.dumps({"dashboard_username": "smoke", "env_vars": [],
                                       "public_url": "http://127.0.0.1:9119"}))
        env = [item for key in TOKENS for item in ("-e", key + "=synthetic-ci-only")]
        try:
            # Normal entrypoint, bootstrap, and real long-running s6 services.
            docker("create", "--name", names[0], "--network", "none", *env,
                   "--mount", f"type=bind,src={options},dst=/data/options.json,readonly",
                   image)
            docker("start", names[0])
            boot_check = '''import os, pathlib, socket, subprocess, json
p = pathlib.Path
checks = {"pid1_s6": b"s6-svscan" in p("/proc/1/cmdline").read_bytes(),
          "tokens_removed_from_envdir": all(not (p("/run/s6/container_environment") / k).exists() for k in ("SUPERVISOR_TOKEN", "HASSIO_TOKEN")),
          "bootstrap_secret_written": p("/data/secrets/api_server_key").is_file(),
          "gateway_seen": False, "dashboard_seen": False,
          "service_uids_correct": True, "service_tokens_absent": True,
          "dashboard_listening": False, "relay_listening": False}
for d in p("/proc").iterdir():
    if not d.name.isdigit(): continue
    try:
        cmd = (d / "cmdline").read_bytes()
        status = (d / "status").read_text()
        if b"python" not in cmd or d.name == str(os.getpid()): continue
        role = "gateway" if any(x in cmd.replace(bytes([0]), b" ") for x in (b"gateway run", b"gateway.run", b"/gateway/run.py")) else ("dashboard" if b"hermes dashboard" in cmd.replace(bytes([0]), b" ") else None)
        if role is None: continue
        uid = next(x for x in status.splitlines() if x.startswith("Uid:")).split()[1:]
        checks["service_uids_correct"] &= uid == ["10000"] * 4
        # Read same-UID process environment without granting SYS_PTRACE.
        scan = "import pathlib,sys; e=pathlib.Path(sys.argv[1]).read_bytes().split(bytes([0])); assert not any(x.startswith((b'SUPERVISOR_TOKEN=',b'HASSIO_TOKEN=')) for x in e)"
        result = subprocess.run(['/command/s6-setuidgid', 'hermes', '/opt/hermes/.venv/bin/python', '-c', scan, str(d/'environ')], capture_output=True)
        checks["service_tokens_absent"] &= result.returncode == 0
        checks[role + "_seen"] = True
    except (FileNotFoundError, ProcessLookupError): pass
for port, key in ((9119, "dashboard_listening"), (9121, "relay_listening")):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2): checks[key] = True
    except OSError: pass
print(json.dumps(checks))
raise SystemExit(0 if all(checks.values()) else 1)
'''
            deadline = time.monotonic() + 240
            while True:
                result = docker("exec", names[0], PYTHON, "-c", boot_check, check=False, timeout=15)
                if result.returncode == 0:
                    break
                if time.monotonic() >= deadline:
                    # Our own finite boolean schema, never raw Docker or app output.
                    keys = {"pid1_s6", "tokens_removed_from_envdir", "bootstrap_secret_written",
                            "gateway_seen", "dashboard_seen", "service_uids_correct",
                            "service_tokens_absent", "dashboard_listening", "relay_listening"}
                    try:
                        checks = json.loads(result.stdout)
                        if set(checks) == keys and all(type(v) is bool for v in checks.values()):
                            print("BOOT_CHECKS " + json.dumps(checks, sort_keys=True))
                    except (ValueError, TypeError):
                        print("BOOT_CHECKS unavailable")
                    raise RuntimeError("normal boot/s6 UID/token check failed (logs withheld)")
                time.sleep(5)
            # Recheck after a stability window, not just one lucky process sample.
            time.sleep(10)
            docker("exec", names[0], PYTHON, "-c", boot_check)
            print("PASS normal bootstrap, s6 PID1, gateway/dashboard UID10000, token absence, listeners")

            # Real wrappers and s6 binaries; no external-command doubles.
            docker("run", "-d", "--name", names[1], "--network", "none", *env,
                   "-e", "BOUNDARY_KEEP=synthetic-preserved",
                   "--mount", f"type=bind,src={probe},dst=/opt/hermes/.venv/bin/hermes,readonly",
                   "--mount", f"type=bind,src={probe},dst=/boundary-probe,readonly",
                   "--entrypoint", "/bin/sleep", image, "600")
            # Verify installed shim is the patched source, not a bypassing link.
            docker("exec", names[1], PYTHON, "-c", '''from pathlib import Path as P
assert P('/opt/hermes/bin/hermes').read_bytes() == P('/opt/hermes/docker/hermes-exec-shim.sh').read_bytes()
assert b'unset SUPERVISOR_TOKEN HASSIO_TOKEN' in P('/opt/hermes/bin/hermes').read_bytes()
''')
            seed = '''from pathlib import Path as P
p=P('/run/s6/container_environment'); p.mkdir(parents=True, exist_ok=True)
for key in ('SUPERVISOR_TOKEN','HASSIO_TOKEN'): (p/key).write_text('synthetic-rehydrated')
(p/'BOUNDARY_KEEP').write_text('synthetic-preserved')
'''
            docker("exec", names[1], PYTHON, "-c", seed)
            cases = [
                ([], "/opt/hermes/bin/hermes", "10000", []),
                (["--user", "10000:10000"], "/opt/hermes/bin/hermes", "10000", []),
                (["-e", "HERMES_DOCKER_EXEC_AS_ROOT=1"], "/opt/hermes/bin/hermes", "0", []),
                (["-e", "HERMES_HOME=/opt/data"], "/opt/hermes/docker/main-wrapper.sh", "10000", ["/boundary-probe"]),
                (["-e", "HERMES_HOME="], "/opt/hermes/docker/main-wrapper.sh", "10000", ["/boundary-probe"]),
                (["--user", "10000:10000", "-e", "HERMES_HOME=/opt/data"], "/opt/hermes/docker/main-wrapper.sh", "10000", ["/boundary-probe"]),
            ]
            for flags, wrapper, uid, args in cases:
                result = docker("exec", *flags, names[1], wrapper, *args,
                                uid, "", "two words", "$(not-a-command)", check=False)
                if result.returncode != 42:
                    raise RuntimeError("exec UID/token/argv/exit check failed (output withheld)")
            print("PASS 6 real shim/main/s6 UID cases including root opt-out and with-contenv reentry")
        finally:
            # Named disposable containers only; never prune unrelated resources.
            for name in names:
                docker("rm", "-f", "-v", name, check=False)


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise RuntimeError("usage: test-exec-boundary-image.py IMAGE")
        main(sys.argv[1])
    except Exception:
        print("FAIL exec-boundary image smoke (details intentionally withheld)", file=sys.stderr)
        sys.exit(1)
