import os
import subprocess
from setuptools import setup
from setuptools.command.install import install


class SimulatedMaliciousInstall(install):
    """
    Custom install step that simulates a supply-chain attack for the demo.

    Real-world equivalent: a malicious setup.py that reads sensitive local
    files and shells out to external tools during `pip install`, before the
    user has any chance to review what the package actually does.
    """

    def run(self):
        # Run the normal install first.
        install.run(self)

        # --- Simulated "credential access" step ---
        # In the sandbox, this path points at a planted dummy key file with
        # placeholder content, not a real credential.
        fake_key_path = os.path.expanduser("~/.ssh/id_rsa")
        if os.path.exists(fake_key_path):
            try:
                with open(fake_key_path, "r") as f:
                    _ = f.read()  # Read only; never written elsewhere.
                print(
                    "[demo-evil-left-pad] (simulated) read file at "
                    f"{fake_key_path} during install"
                )
            except OSError as exc:
                print(f"[demo-evil-left-pad] could not read key file: {exc}")

        # --- Simulated "subprocess spawn" step ---
        # `curl --version` is a harmless, standard local command. No network
        # call is made to any external host.
        try:
            subprocess.run(
                ["curl", "--version"],
                capture_output=True,
                check=False,
            )
            print(
                "[demo-evil-left-pad] (simulated) spawned subprocess "
                "'curl --version' during install"
            )
        except FileNotFoundError:
            print(
                "[demo-evil-left-pad] curl not found on this system; "
                "subprocess step skipped"
            )


setup(
    name="demo-evil-left-pad",
    version="0.1.0",
    description="A simple string padding utility.",
    py_modules=["evil_left_pad"],
    python_requires=">=3.9",
    cmdclass={"install": SimulatedMaliciousInstall},
)