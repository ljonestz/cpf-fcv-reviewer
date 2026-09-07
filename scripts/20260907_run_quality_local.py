"""Serve the candidate build locally with existing provider configuration for one quality run."""

from __future__ import annotations

import argparse
import os
import runpy
import ssl
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=58424)
    args = parser.parse_args()
    helper = runpy.run_path(str(ROOT / "scripts" / "20260907_probe_live_research.py"))
    env, tls = helper["service_environment"]()
    os.environ.update(env)
    # Export only public root certificates so all local HTTP clients trust WBG TLS.
    with tempfile.TemporaryDirectory(prefix="cpf-quality-tls-") as directory:
        roots = Path(directory) / "roots.pem"
        roots.write_text("".join(
            ssl.DER_cert_to_PEM_cert(cert) for cert in tls.get_ca_certs(binary_form=True)
        ), encoding="ascii")
        os.environ["SSL_CERT_FILE"] = str(roots)
        from cpf_fcv_reviewer.app import create_app

        registry_name = Path(env["REGISTRY_BUNDLE_PATH"]).name
        registry = ROOT / "registry_bundles" / registry_name
        if not registry.is_file():
            raise RuntimeError("Configured approved registry is unavailable locally.")
        release = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        ).strip()
        app = create_app({
            "REGISTRY_BUNDLE_PATH": str(registry),
            "PERSISTENCE_PATH": "",
            "ALLOW_VOLATILE_PROTOTYPE": True,
            "APP_RELEASE": release,
        })
        app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
