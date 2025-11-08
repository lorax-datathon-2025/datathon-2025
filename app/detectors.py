import re
from typing import Dict
from .models import DetectorSignals, Citation

SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CC_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

# use lowercase for consistency
INTERNAL_MARKERS = [
    "internal use only",
    "do not distribute",
    "confidential",
    "non-disclosure",
    "nda",
]
UNSAFE_KEYWORDS = [
    "child sexual",
    "exploit", "molest",
    "kill them all",
    "how to make a bomb",
    "join isis",
]

def run_detectors(pages: Dict[int, str]) -> DetectorSignals:
    signals = DetectorSignals()

    # Precompile marker regexes once with word boundaries
    internal_regexes = [
        re.compile(rf"\b{re.escape(word)}\b", flags=re.IGNORECASE)
        for word in INTERNAL_MARKERS
    ]
    unsafe_regexes = [
        re.compile(rf"\b{re.escape(word)}\b", flags=re.IGNORECASE)
        for word in UNSAFE_KEYWORDS
    ]

    for page, text in pages.items():
        lower = text.lower()

        # PII
        if SSN_PATTERN.search(text) or CC_PATTERN.search(text):
            signals.has_pii = True
            snippet = text[:200].replace("\n", " ")
            signals.pii_hits.append(Citation(page=page, snippet=snippet))

        # internal (whole word)
        if any(rx.search(lower) for rx in internal_regexes):
            signals.has_internal_markers = True
            signals.notes.append(f"Internal marker on page {page}")

        # unsafe (whole word)
        if any(rx.search(lower) for rx in unsafe_regexes):
            signals.has_unsafe_pattern = True
            snippet = text[:200].replace("\n", " ")
            signals.unsafe_hits.append(Citation(page=page, snippet=snippet))

    return signals
