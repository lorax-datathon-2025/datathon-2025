import os
from copy import deepcopy
from functools import lru_cache
from typing import Any, Dict, List

import yaml

CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "config", "prompt_library.yaml")
)

_DEFAULT_PROMPT_FLOW: List[Dict[str, Any]] = [
    {
        "id": "image_analysis",
        "prompt": "image_analysis",
        "runner": "multimodal",
        "conditions": {"has_images": True},
        "stop_on_error": False,
    },
    {"id": "precheck", "prompt": "precheck", "collect_summary": True},
    {
        "id": "pii_scan",
        "prompt": "pii_scan",
        "depends_on": ["precheck"],
        "use_summary_pages": True,
        "conditions": {"signals_true": ["has_pii"]},
    },
    {
        "id": "unsafe_scan",
        "prompt": "unsafe_scan",
        "depends_on": ["precheck"],
        "use_summary_pages": True,
    },
    {
        "id": "confidentiality_scan",
        "prompt": "confidentiality_scan",
        "depends_on": ["precheck", "unsafe_scan"],
        "use_summary_pages": True,
    },
    {
        "id": "final_decision",
        "prompt": "final_decision",
        "depends_on": ["confidentiality_scan"],
        "use_summary_pages": True,
        "final_node": True,
    },
]


@lru_cache()
def load_prompt_library():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def get_prompt(name: str) -> dict:
    cfg = load_prompt_library()
    return cfg["prompts"][name]


def get_prompt_flow() -> List[Dict[str, Any]]:
    cfg = load_prompt_library()
    flow = cfg.get("prompt_flow")
    if not flow:
        return deepcopy(_DEFAULT_PROMPT_FLOW)
    return deepcopy(flow)
