import json
from dataclasses import asdict
from pathlib import Path
from .model import Config


def save(path,config):
    config.validate()
    Path(path).write_text(json.dumps(asdict(config),indent=2),encoding='utf-8')


def load(path):
    config=Config(**json.loads(Path(path).read_text(encoding='utf-8')))
    config.validate()
    return config
