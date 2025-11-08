import os
import yaml
from functools import lru_cache

CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "config", "prompt_library.yaml")
)

@lru_cache()
def load_prompt_library():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def get_prompt(name: str) -> dict:
    cfg = load_prompt_library()
    return cfg["prompts"][name]
