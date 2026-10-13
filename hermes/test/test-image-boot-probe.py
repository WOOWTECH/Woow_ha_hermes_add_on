"""Negative controls for the image gate; no Docker or real secrets needed."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import image_boot_probe as probe


class BootGate(unittest.TestCase):
    def test_empty_secret_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'secret'
            self.assertFalse(probe.secret_nonempty(p))
            p.touch()
            self.assertFalse(probe.secret_nonempty(p))
            p.write_text('synthetic')
            self.assertTrue(probe.secret_nonempty(p))

    def test_json_health_not_spa(self):
        self.assertTrue(probe.valid_health({'status': 'ok', 'platform': 'hermes-agent'}))
        for value in ('<html>ok</html>', {}, {'status': 'ok'}, {'status': 'error', 'platform': 'hermes-agent'}):
            self.assertFalse(probe.valid_health(value))

    def test_actual_worker_identity_uid_and_marker(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for pid in ('20', '10'): (root / pid).mkdir()
            (root / '10/cmdline').write_bytes(b's6-supervise\0gateway-default\0')
            (root / '20/cmdline').write_bytes(b'python\0/opt/hermes/.venv/bin/hermes\0gateway\0run\0--replace\0')
            (root / '20/status').write_text('Uid:\t10000\t10000\t10000\t10000\nPPid:\t10\n')
            env = {'tokens_absent': True, 'supervised_child': True}
            def check(pid=20, main=30):
                return probe.worker_checks('gateway-default', pid, main, root, lambda _: env)
            self.assertTrue(all(check().values()))
            self.assertFalse(any(check(pid=0).values()))
            self.assertFalse(any(check(main=20).values()))
            env['supervised_child'] = False
            self.assertFalse(check()['identity'])
            env['supervised_child'] = True
            env['tokens_absent'] = False
            self.assertFalse(check()['tokens_absent'])
            (root / '20/status').write_text('Uid:\t0\t0\t0\t0\nPPid:\t10\n')
            self.assertFalse(check()['uid10000'])
            # Heartbeat has the same gateway/run words, but is not this service.
            (root / '10/cmdline').write_bytes(b's6-supervise\0main-hermes\0')
            self.assertFalse(check()['identity'])

    def test_heartbeat_dashboard_relay_without_gateway_fails(self):
        # Every other gate is live/healthy; only the true gateway PID is absent.
        original_worker_checks = probe.worker_checks
        def workers(role, pid, main):
            if role == 'gateway-default': return original_worker_checks(role, pid, main)
            return {'identity': True, 'uid10000': True, 'tokens_absent': True}
        with patch.object(probe, 'service_pid', side_effect=lambda role: 0 if role == 'gateway-default' else 30), \
             patch.object(probe, 'worker_checks', side_effect=workers), \
             patch.object(probe, 'gateway_health', return_value=True), \
             patch.object(probe, 'secret_nonempty', return_value=True), \
             patch.object(probe.Path, 'read_bytes', return_value=b's6-svscan'), \
             patch.object(probe.Path, 'exists', return_value=False), \
             patch.object(probe.socket, 'create_connection'):
            checks = probe.collect()
            self.assertTrue(checks['dashboard_listening'] and checks['relay_listening'])
            self.assertFalse(checks['gateway-default_identity'])
            self.assertFalse(all(checks.values()))


if __name__ == '__main__': unittest.main(verbosity=2)
