# TODO: Remove this file

import json
import os
from pathlib import Path

from llama_cpp.server.model import LlamaProxy
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


def pre_load():
    config_file = os.environ.get("CONFIG_FILE", "config.json")
    _, model_settings = load_config(config_file)
    for model in model_settings:
        if (
            model.hf_pretrained_model_name_or_path is None
            and model.hf_model_repo_id is None
        ):
            assert Path(model.model).exists(), f"Model file {model.model} not found!"

    model_settings = [
        model
        for model in model_settings
        if (
            model.hf_pretrained_model_name_or_path is not None
            or model.hf_model_repo_id is not None
        )
    ]
    proxy = LlamaProxy(model_settings)
    for model in model_settings:
        _ = proxy(model.model_alias or model.model)
