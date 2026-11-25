from pathlib import Path

import yaml

from learnmate.config import Settings

REPO = Path(__file__).resolve().parents[2]
COMPOSE = REPO / "deploy" / "compose.yaml"
ENV_EXAMPLE = REPO / "deploy" / ".env.example"
DOCKERFILE = REPO / "server" / "Dockerfile"
SECRETS = {
    "CLOUDFLARE_TUNNEL_TOKEN",
    "DEVICE_TOKEN",
    "ANTHROPIC_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "PIN_KEY",
}
REQUIRED = SECRETS | {"LLM_MONTHLY_BUDGET_USD", "EMBED_MODEL", "RERANK_ENABLED"}


def _services() -> dict:
    return yaml.safe_load(COMPOSE.read_text())["services"]


def _env_example() -> dict[str, str]:
    values = {}
    for line in ENV_EXAMPLE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            values[key] = value
    return values


def test_server_publishes_no_ports():
    assert "ports" not in _services()["server"]


def test_server_restarts_and_keeps_data():
    server = _services()["server"]
    assert server["restart"] == "always"
    assert "./data:/data" in server["volumes"]
    assert server["environment"]["DATA_DIR"] == "/data"


def test_server_runs_migrations_on_start():
    text = DOCKERFILE.read_text()
    migrate = text.index("alembic -c alembic.ini upgrade head &&")
    assert migrate < text.index("uvicorn")


def test_cloudflared_uses_tunnel_token_from_env():
    tunnel = _services()["cloudflared"]
    assert tunnel["environment"]["TUNNEL_TOKEN"] == "${CLOUDFLARE_TUNNEL_TOKEN}"
    assert "run" in tunnel["command"].split()
    assert "ports" not in tunnel


def test_env_example_lists_required_variables():
    assert REQUIRED <= _env_example().keys()


def test_env_example_has_no_secret_values():
    env = _env_example()
    assert all(env[name] == "" for name in SECRETS)


def test_env_example_settings_exist():
    names = _env_example().keys() - {"CLOUDFLARE_TUNNEL_TOKEN"}
    assert all(name.lower() in Settings.model_fields for name in names)


def test_env_example_defaults_load():
    env = _env_example()
    Settings(
        **{k.lower(): v for k, v in env.items() if v and k != "CLOUDFLARE_TUNNEL_TOKEN"}
    )
