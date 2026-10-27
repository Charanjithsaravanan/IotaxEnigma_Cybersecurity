"""Offline smoke tests for the Member 2 analysis engine."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_engine.analyzer import (
    BehavioralFingerprint,
    ClaimedIntent,
    evaluate_mismatch,
    extract_claimed_intent,
)


class Member2AnalyzerTests(unittest.TestCase):
    def setUp(self):
        llm_env = patch.dict(
            os.environ, {"GEMINI_API_KEY": "", "OLLAMA_MODEL": ""}
        )
        llm_env.start()
        self.addCleanup(llm_env.stop)

    def test_benign_string_utility(self):
        claimed = extract_claimed_intent(
            "A small utility for trimming and normalizing strings.",
            {"name": "string-tools", "description": "String helpers"},
        )
        actual = BehavioralFingerprint.model_validate(
            {
                "install_time": {
                    "files_touched": ["/usr/lib/python3.14/site.py"],
                    "env_vars_read": [
                        "PATH",
                        "HOME",
                        "LANG",
                        {"name": "PYTHONPATH", "value": "/workspace"},
                    ],
                },
                "import_time": {"env_vars_read": ["PYTHONPATH", "NODE_ENV"]},
            }
        )
        verdict = evaluate_mismatch(claimed, actual)
        self.assertEqual(verdict.risk_score, 0)
        self.assertEqual(verdict.severity, "low")

    def test_benign_http_library(self):
        claimed = ClaimedIntent(
            package_name="http-client",
            expects_network=True,
        )
        actual = BehavioralFingerprint(
            install_time={},
            import_time={"files_touched": ["/usr/lib/python3.14/ssl.py"]},
        )
        verdict = evaluate_mismatch(claimed, actual)
        self.assertEqual(verdict.risk_score, 0)

    def test_malicious_install_time_exfiltrator(self):
        claimed = ClaimedIntent(package_name="tiny-helper")
        actual = BehavioralFingerprint(
            install_time={
                "network_calls": [{"url": "https://collector.example.test/upload"}],
                "subprocesses_spawned": ["curl collector.example.test"],
            }
        )
        verdict = evaluate_mismatch(claimed, actual)
        self.assertGreaterEqual(verdict.risk_score, 80)
        self.assertIn("installation", " ".join(verdict.findings))

    def test_malicious_import_time_env_stealer(self):
        claimed = ClaimedIntent(package_name="format-utils")
        actual = BehavioralFingerprint(
            import_time={
                "env_vars_read": ["AWS_SECRET_ACCESS_KEY", "GITHUB_TOKEN"],
                "files_touched": ["/home/runner/.ssh/id_rsa"],
            }
        )
        verdict = evaluate_mismatch(claimed, actual)
        self.assertEqual(verdict.risk_score, 100)
        self.assertEqual(verdict.severity, "critical")

    def test_combined_install_and_import_activity_is_cumulative(self):
        claimed = ClaimedIntent(package_name="suspicious")
        actual = BehavioralFingerprint(
            install_time={
                "network_calls": ["https://collector.example.test/upload"],
                "subprocesses_spawned": ["curl collector.example.test"],
            },
            import_time={
                "network_calls": ["https://collector.example.test/ping"],
                "subprocesses_spawned": ["sh -c whoami"],
            },
        )
        verdict = evaluate_mismatch(claimed, actual)
        self.assertGreaterEqual(verdict.risk_score, 80)
        self.assertEqual(verdict.severity, "critical")

    def test_lowercase_secret_env_vars_are_detected(self):
        claimed = extract_claimed_intent(
            "This tool reads aws_secret_access_key and communicates with a server.",
            {"name": "config-reader", "description": "Reads local settings"},
        )
        self.assertIn("AWS_SECRET_ACCESS_KEY", claimed.expects_env_reads)


if __name__ == "__main__":
    unittest.main()
