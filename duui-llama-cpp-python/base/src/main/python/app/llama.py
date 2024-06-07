import json
import os
import sys
import traceback

from fastapi import FastAPI
from llama_cpp.server.app import create_app
from llama_cpp.server.settings import ConfigFileSettings, ModelSettings, ServerSettings


def load_config(config_file) -> tuple[ServerSettings, list[ModelSettings]]:
    with open(config_file, "rb") as f:
        if config_file.endswith(".yaml") or config_file.endswith(".yml"):
            import yaml

            config_json_string = json.dumps(yaml.safe_load(f))
        else:
            config_json_string = f.read()

    config_file_settings = ConfigFileSettings.model_validate_json(config_json_string)
    server_settings = ServerSettings.model_validate(config_file_settings)
    model_settings = config_file_settings.models

    return server_settings, model_settings


def llama_cpp_app() -> FastAPI:
    try:
        config_file = os.environ.get("CONFIG_FILE", "config.json")

        if not os.path.exists(config_file):
            raise ValueError(f"Config file {config_file} not found!")

        server_settings, model_settings = load_config(config_file)

        if not model_settings:
            raise ValueError("No models defined in config file!")

        return create_app(
            server_settings=server_settings,
            model_settings=model_settings,
        )
    except Exception:
        traceback.print_exc()
        sys.exit(1)

