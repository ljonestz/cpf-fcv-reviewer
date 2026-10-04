"""Run the CPF reviewer on loopback with existing mAI Desktop DEV access."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cpf_fcv_reviewer.app import create_app  # noqa: E402
from cpf_fcv_reviewer.config import build_config  # noqa: E402
from cpf_fcv_reviewer.mai_desktop import MaiDesktopGateway  # noqa: E402
from cpf_fcv_reviewer.runtime import build_runtime_services  # noqa: E402


def main():
    registry = PROJECT_ROOT / "registry_bundles" / "cpf_fcv_reviewer_public_guardrails_v1.1.0.json"
    output = PROJECT_ROOT / "output" / "mai-desktop"
    output.mkdir(parents=True, exist_ok=True)
    research_provider = os.environ.get("RESEARCH_PROVIDER", "institutional")
    config = build_config({
        "APP_ENV": "development", "MODEL_PROVIDER": "mai_desktop",
        "MAI_TEAM_NAME": os.environ.get("MAI_TEAM_NAME", ""),
        "ANTHROPIC_API_KEY": (os.environ.get("ANTHROPIC_API_KEY", "")
                              if research_provider == "anthropic" else ""),
        "RESEARCH_PROVIDER": research_provider,
        "RESEARCH_MODEL_ID": os.environ.get("RESEARCH_MODEL_ID", "claude-sonnet-4-5"),
        "APP_RELEASE": os.environ.get("APP_RELEASE", "mai-desktop-development"),
        "REGISTRY_BUNDLE_PATH": str(registry),
        "REGISTRY_BUNDLE_SHA256": registry.with_suffix(".sha256").read_text().split()[0],
        "PERSISTENCE_PATH": str(output / "sessions.sqlite3"),
        "RELIEFWEB_APP_NAME": os.environ.get("RELIEFWEB_APP_NAME", ""),
    }, use_environment=False)
    gateway = MaiDesktopGateway(config["MAI_TEAM_NAME"])
    gateway.authenticate()
    services = build_runtime_services(config, model_gateway=gateway, follow_on_gateway=gateway)
    print(f"Local mAI DEV reviewer: {research_provider} research; assistant replies arrive complete.")
    create_app(config, services=services, use_environment=False).run(
        host="127.0.0.1", port=58423, debug=False, use_reloader=False,
    )


if __name__ == "__main__":
    main()
