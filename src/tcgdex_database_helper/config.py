from pathlib import Path
import yaml

ROOT_DIR = Path(__file__).resolve().parents[2]

CONFIG_DIR = ROOT_DIR / "config"
DEFAULT_CONFIG = CONFIG_DIR / "config.yaml"
LOCAL_CONFIG = CONFIG_DIR / "config.local.yaml"
LANGUAGE = "en"
NO_SSL_VERIFY = False
IS_LOCAL_ENDPOINT = False

def set_language(lang: str):
    global LANGUAGE
    LANGUAGE = lang

def get_language() -> str:
    return LANGUAGE

def set_no_ssl_verify(verify: bool):
    global NO_SSL_VERIFY
    NO_SSL_VERIFY = verify

def get_no_ssl_verify() -> bool:
    return NO_SSL_VERIFY

def set_is_local_endpoint(is_local: bool):
    global IS_LOCAL_ENDPOINT
    IS_LOCAL_ENDPOINT = is_local

def get_is_local_endpoint() -> bool:
    return IS_LOCAL_ENDPOINT

def load_config() -> dict:
    print("Loading configs...")
    print("Default path:", DEFAULT_CONFIG, "Exists:", DEFAULT_CONFIG.exists())
    print("Local path:", LOCAL_CONFIG, "Exists:", LOCAL_CONFIG.exists())

    config = {}

    if DEFAULT_CONFIG.exists():
        with DEFAULT_CONFIG.open() as f:
            config = yaml.safe_load(f) or {}

    if LOCAL_CONFIG.exists():
        with LOCAL_CONFIG.open() as f:
            local = yaml.safe_load(f) or {}
        deep_merge(config, local)

    return resolve_paths(config)


def deep_merge(base: dict, override: dict):
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v


def resolve_paths(config: dict) -> dict:
    paths = config.get("paths", {})
    resolved = {}

    for name, value in paths.items():
        p = Path(value)
        if not p.is_absolute():
            p = (ROOT_DIR / p).resolve()
        resolved[name] = p

    config["paths"] = resolved
    return config
