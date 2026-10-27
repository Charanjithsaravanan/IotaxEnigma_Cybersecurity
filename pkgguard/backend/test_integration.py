"""Regression tests for backend-to-sandbox model adaptation."""

import asyncio
import os
import unittest
from unittest.mock import patch

from backend.main import run_member1_sandbox, run_member2_verdict
from shared.schemas import BehavioralFingerprint, ClaimedIntent


class BackendIntegrationTests(unittest.TestCase):
    def test_real_sandbox_result_is_adapted_to_shared_fingerprint(self):
        result = {
            "behavioral_fingerprint": {
                "install_time": {
                    "network_calls": ["198.51.100.99:80"],
                    "files_touched": ["/root/.ssh/id_rsa"],
                    "env_vars_read": ["AWS_SECRET_ACCESS_KEY"],
                    "subprocesses_spawned": ["/bin/sh -c id"],
                },
                "import_time": {
                    "network_calls": [],
                    "files_touched": [],
                    "env_vars_read": [],
                    "subprocesses_spawned": [],
                },
            }
        }
        with patch.dict(os.environ, {"USE_MOCK_MODULES": "false"}):
            with patch("sandbox.runner.run_sandbox", return_value=result):
                fingerprint = asyncio.run(
                    run_member1_sandbox("pypi", "example")
                )

        self.assertEqual(
            fingerprint.install_time.files_touched,
            ["/root/.ssh/id_rsa"],
        )

    def test_real_verdict_is_adapted_to_shared_verdict(self):
        claimed = ClaimedIntent(summary="String utility")
        actual = BehavioralFingerprint.model_validate({
            "install_time": {
                "network_calls": ["198.51.100.99:80"],
                "files_touched": ["/root/.ssh/id_rsa"],
                "env_vars_read": ["AWS_SECRET_ACCESS_KEY"],
                "subprocesses_spawned": [],
            },
            "import_time": {},
        })
        with patch.dict(os.environ, {"USE_MOCK_MODULES": "false"}):
            verdict = asyncio.run(run_member2_verdict(claimed, actual))

        self.assertEqual(verdict.verdict, "malicious")
        self.assertEqual(verdict.risk_score, 100)


if __name__ == "__main__":
    unittest.main()