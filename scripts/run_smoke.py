"""Run the deterministic provider-free browser smoke service."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cpf_fcv_reviewer.app import create_smoke_app  # noqa: E402


def main() -> None:
    create_smoke_app().run(host="127.0.0.1", port=58422, debug=False)


if __name__ == "__main__":
    main()
