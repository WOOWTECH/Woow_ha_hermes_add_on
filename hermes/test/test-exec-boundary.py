"""Real /bin/sh regression tests; only external commands/files are sandbox doubles.

--unpatched runs the same security assertions against the captured upstream source
and MUST fail. No real environment, credentials, s6 service or agent is used.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ADDON = Path(__file__).resolve().parent.parent
FIXTURES = ADDON / "test/fixtures/exec-boundary"
UNPATCHED = "--unpatched" in sys.argv
if UNPATCHED:
    sys.argv.remove("--unpatched")
HASHES = {
    "hermes-exec-shim.sh": "57637e73c8db76aa84a38e4a2edb1b155bfd86a2e89a8d4c38c4546ee1175985",
    "main-wrapper.sh": "d01d7ece5198f79496cf8ce64552665699995f0bf2cabbac78205b6b1779fb9b",
}
TOKENS = ("SUPERVISOR_TOKEN", "HASSIO_TOKEN")


def load_patch():
    spec = importlib.util.spec_from_file_location("boundary_patch", ADDON / "patches/ha-exec-boundary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# All executables are outside the shell-under-test. The s6 double models only
# argv/exec and environment handoff, NOT actual kernel UID/capability changes.
HELPER = r'''
import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
with open(os.environ["EVENTS"], "a") as f:
    f.write(json.dumps({"name": name, "argv": sys.argv[1:], "env": dict(os.environ)}) + "\n")
if name == "with-contenv":
    for key in ("SUPERVISOR_TOKEN", "HASSIO_TOKEN"):
        os.environ[key] = "sentinel-rehydrated-not-a-secret"
    os.environ["HERMES_HOME"] = os.environ["TEST_DATA"]
    os.execvp(sys.argv[1], sys.argv[1:])
if name == "s6-setuidgid":
    assert sys.argv[1] == "hermes"
    os.environ["TEST_UID"] = "10000"
    os.execvp(sys.argv[2], sys.argv[2:])
sys.exit(int(os.environ["TEST_EXIT"]))
'''


class ShellBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.data = self.root / "data"
        self.data.mkdir()
        self.venv = self.root / "hermes/.venv/bin"
        self.venv.mkdir(parents=True)
        (self.venv / "activate").write_text(":\n")
        for name in ("with-contenv", "s6-setuidgid", "hermes", "agent-probe"):
            target = self.bin / name
            target.write_text(f"#!{sys.executable}\n" + HELPER)
            target.chmod(0o755)
        shutil.copy2(self.bin / "hermes", self.venv / "hermes")
        (self.bin / "id").write_text('#!/bin/sh\nif [ "$2" = hermes ]; then echo 10000; else echo "$TEST_UID"; fi\n')
        (self.bin / "id").chmod(0o755)
        self.scripts = {}
        for name, digest in HASHES.items():
            source = (FIXTURES / name).read_text()
            self.assertEqual(hashlib.sha256(source.encode()).hexdigest(), digest)
            if not UNPATCHED:
                source = load_patch().patched_source(name, source)
            # Relocate filesystem dependencies only; keep the entire real shell
            # control flow, conditions, quoting, exec and exit statements intact.
            source = source.replace("/opt/hermes", str(self.root / "hermes"))
            source = source.replace("/opt/data", str(self.data))
            source = source.replace("/command/", str(self.bin) + "/")
            target = self.root / name
            target.write_text(source)
            self.scripts[name] = target
            subprocess.run(["/bin/sh", "-n", str(target)], check=True)

    def run_shell(self, name, uid="0", args=(), optout="", reenter=False,
                  ready=False, tokens=True, code=37, missing=None):
        events_path = self.root / "events.jsonl"
        events_path.unlink(missing_ok=True)
        env = {
            "PATH": f"{self.bin}:/usr/bin:/bin", "HOME": "/root",
            "TEST_UID": uid, "TEST_DATA": str(self.data), "TEST_EXIT": str(code),
            "EVENTS": str(events_path), "OPENAI_API_KEY": "provider-sentinel",
            "CUSTOM_SETTING": "keep spaces; $literal", "HERMES_DOCKER_EXEC_AS_ROOT": optout,
        }
        if not reenter:
            env["HERMES_HOME"] = str(self.data)
        if ready:
            env["HERMES_MAIN_WRAPPER_ENV_READY"] = "1"
        if tokens:
            env.update({key: "sentinel-input-not-a-secret" for key in TOKENS})
        if missing:
            missing.unlink()
        result = subprocess.run(["/bin/sh", str(self.scripts[name]), *args], env=env,
                                cwd=self.root, capture_output=True, text=True, timeout=5)
        events = [json.loads(line) for line in events_path.read_text().splitlines()] if events_path.exists() else []
        return result, events

    def assert_handoff(self, result, events, args, names, code=37, main=False):
        self.assertEqual(result.returncode, code, result.stderr)
        self.assertEqual([e["name"] for e in events], names)
        self.assertEqual(events[-1]["argv"], list(args))
        for event in events:
            for key in TOKENS:
                self.assertNotIn(key, event["env"], event["name"])
            self.assertEqual(event["env"]["OPENAI_API_KEY"], "provider-sentinel")
            self.assertEqual(event["env"]["CUSTOM_SETTING"], "keep spaces; $literal")
        if main:
            self.assertNotIn("HERMES_MAIN_WRAPPER_ENV_READY", events[-1]["env"])
        self.assertEqual(result.stdout, "")

    def test_shim_root_and_nonroot(self):
        args = ("chat", "", "two words", "*;$HOME", "--query=x")
        for uid in ("0", "10000", "12345"):
            with self.subTest(uid=uid):
                result, events = self.run_shell("hermes-exec-shim.sh", uid=uid, args=args)
                self.assert_handoff(result, events, args, ["s6-setuidgid", "hermes"] if uid == "0" else ["hermes"])
                self.assertEqual(events[-1]["env"]["HOME"], str(self.data) if uid == "0" else "/root")

    def test_shim_root_optout(self):
        for value in ("1", "true", "TRUE", "True", "yes", "YES", "Yes", "false", "0"):
            with self.subTest(value=value):
                result, events = self.run_shell("hermes-exec-shim.sh", optout=value)
                drop = value in ("false", "0")
                self.assert_handoff(result, events, (), ["s6-setuidgid", "hermes"] if drop else ["hermes"])
                self.assertEqual(events[-1]["env"]["HOME"], str(self.data) if drop else "/root")

    def test_shim_failures_preserved(self):
        result, events = self.run_shell("hermes-exec-shim.sh", missing=self.bin / "s6-setuidgid")
        self.assertEqual(result.returncode, 126)
        self.assertEqual(events, [])
        result, events = self.run_shell("hermes-exec-shim.sh", missing=self.venv / "hermes")
        self.assertEqual(result.returncode, 127)
        self.assertEqual(events, [])

    def test_main_routes_root_nonroot_and_reentry(self):
        for uid in ("0", "10000"):
            for reenter in (False, True):
                for args in ((), ("agent-probe", "", "two words", "*;$HOME"), ("chat", "--query", "a b")):
                    with self.subTest(uid=uid, reenter=reenter, args=args):
                        result, events = self.run_shell("main-wrapper.sh", uid=uid, args=args, reenter=reenter)
                        executable = bool(args and args[0] == "agent-probe")
                        names = (["with-contenv"] if reenter else []) + (["s6-setuidgid"] if uid == "0" else [])
                        self.assert_handoff(result, events, args[1:] if executable else args,
                                            names + ["agent-probe" if executable else "hermes"], main=True)
                        self.assertEqual(events[-1]["env"]["HOME"], str(self.data))

    def test_main_reentry_guard(self):
        result, events = self.run_shell("main-wrapper.sh", reenter=True, ready=True)
        self.assert_handoff(result, events, (), ["s6-setuidgid", "hermes"], main=True)

    def test_main_without_with_contenv(self):
        result, events = self.run_shell("main-wrapper.sh", reenter=True, missing=self.bin / "with-contenv")
        self.assert_handoff(result, events, (), ["s6-setuidgid", "hermes"], main=True)

    def test_main_rejects_arbitrary_uid(self):
        result, events = self.run_shell("main-wrapper.sh", uid="12345")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(events, [])
        self.assertIn("not supported", result.stderr)

    def test_absent_tokens_and_exit_codes(self):
        for name in HASHES:
            for code in (0, 1, 42, 126, 127):
                with self.subTest(name=name, code=code):
                    result, events = self.run_shell(name, tokens=False, code=code)
                    self.assert_handoff(result, events, (), ["s6-setuidgid", "hermes"], code=code)


@unittest.skipIf(UNPATCHED, "red phase exercises original shell only")
class PatchContract(unittest.TestCase):
    def test_hashes_and_patch_validation(self):
        patch = load_patch()
        for name in HASHES:
            source = (FIXTURES / name).read_text()
            updated = patch.patched_source(name, source)
            patch.check_source(name, updated)
            self.assertEqual(patch.patched_source(name, updated), updated)
            subprocess.run(["/bin/sh", "-n"], input=updated, text=True, check=True)
            for bad in (source + "# drift\n", source.replace("set -e", "set -e\nset -e"),
                        source.replace("set -e", "set -u"), updated.replace("unset SUPERVISOR_TOKEN HASSIO_TOKEN", ":", 1)):
                with self.subTest(name=name, bad=bad[-40:]):
                    with self.assertRaises(ValueError):
                        patch.patched_source(name, bad)
            with self.assertRaises(ValueError):
                patch.check_source(name, source)

    def test_cli_preflight_and_reentry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in HASHES:
                shutil.copy2(FIXTURES / name, root / name)
            cmd = [sys.executable, str(ADDON / "patches/ha-exec-boundary.py"), "--directory", directory]
            second = root / "main-wrapper.sh"
            second.write_text(second.read_text() + "# drift\n")
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual((root / "hermes-exec-shim.sh").read_bytes(), (FIXTURES / "hermes-exec-shim.sh").read_bytes())
            shutil.copy2(FIXTURES / second.name, second)
            second.chmod(0o755)
            for args in ([], [], ["--check"]):
                subprocess.run(cmd + args, check=True, capture_output=True)
                self.assertEqual(second.stat().st_mode & 0o777, 0o755)

    def test_build_and_bootstrap_contract(self):
        dockerfile = (ADDON / "Dockerfile").read_text()
        self.assertIn("python3 /tmp/woow-own-patches/ha-exec-boundary.py", dockerfile)
        self.assertIn("ha-exec-boundary.py --check", dockerfile)
        init = (ADDON / "rootfs/etc/cont-init.d/00-woow-options").read_text()
        self.assertLess(init.index("http://supervisor/network/info"), init.index('rm -f "$ENVDIR/SUPERVISOR_TOKEN"'))
        self.assertLess(init.index("http://supervisor/addons/self/options"), init.index('rm -f "$ENVDIR/SUPERVISOR_TOKEN"'))


if __name__ == "__main__":
    unittest.main(verbosity=2)
