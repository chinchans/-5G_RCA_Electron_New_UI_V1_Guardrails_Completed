"""Layer 1: rule-based prompt-injection and jailbreak pattern detection."""

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Tuple

# Fast substring checks (Layer 1 — escalate suspicious chunks to Llama Guard)
SUSPICIOUS_LITERALS: Tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "reveal system prompt",
    "show system prompt",
    "forget your role",
    "you are now",
    "disregard your instructions",
    "override your instructions",
    "new instructions:",
    "developer mode",
    "jailbreak",
    "do anything now",
    "bypass safety",
    "bypass content filter",
    "disable guardrails",
    "pretend you are",
    "simulate being",
    "ignore the above",
    "end of prompt",
    "begin system",
    "hidden instructions",
    "secret instructions",
    "print your instructions",
    "output your prompt",
    "dan mode",
    "sudo mode",
    "god mode",
)

# Additional high-risk phrases (Layer 1)
MALICIOUS_LITERALS: Tuple[str, ...] = (
    "execute the following command",
    "run this shell command",
    "exfiltrate data",
    "dump credentials",
    "ignore openapi",
    "ignore 3gpp",
    "roleplay as admin",
    "unfiltered mode",
    "no restrictions",
    "without limitations",
    "hypothetically ignore",
    "for educational purposes ignore",
)

INJECTION_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("ignore_previous_instructions", re.compile(
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
        re.IGNORECASE,
    )),
    ("reveal_system_prompt", re.compile(
        r"(reveal|show|print|output|disclose)\s+(your\s+)?(system\s+prompt|hidden\s+prompt|instructions?)",
        re.IGNORECASE,
    )),
    ("forget_your_role", re.compile(
        r"forget\s+(your\s+)?(role|instructions?|rules?|guidelines?)",
        re.IGNORECASE,
    )),
    ("role_override", re.compile(
        r"you\s+are\s+now\s+(?:a|an|the)\s+\w+",
        re.IGNORECASE,
    )),
    ("act_as_override", re.compile(
        r"\bact\s+as\s+(?:a|an|the)\s+(?!specified\b|defined\b|configured\b|described\b|follows\b)\w+",
        re.IGNORECASE,
    )),
    ("system_prompt_reference", re.compile(
        r"\bsystem\s+prompt\b",
        re.IGNORECASE,
    )),
    ("disregard_system", re.compile(
        r"disregard\s+(the\s+)?(above|system|previous|all)",
        re.IGNORECASE,
    )),
    ("new_instructions", re.compile(
        r"(new|updated|override|hidden)\s+instructions?\s*:?",
        re.IGNORECASE,
    )),
    ("jailbreak_dan", re.compile(
        r"\bDAN\b.*\b(do anything now|jailbreak)\b",
        re.IGNORECASE,
    )),
    ("developer_mode", re.compile(
        r"(developer|dev|god|sudo)\s+mode\s+(enabled|on|activated)?",
        re.IGNORECASE,
    )),
    ("xml_system_tag", re.compile(
        r"<\s*/?\s*system\s*>",
        re.IGNORECASE,
    )),
    ("prompt_injection_delimiter", re.compile(
        r"={3,}\s*(system|assistant|end of prompt)\s*={3,}",
        re.IGNORECASE,
    )),
    ("base64_instruction", re.compile(
        r"(decode|execute|run)\s+(this\s+)?base64",
        re.IGNORECASE,
    )),
    ("bypass_safety", re.compile(
        r"bypass\s+(safety|content\s+filter|guardrails?|restrictions?)",
        re.IGNORECASE,
    )),
    ("pretend_roleplay", re.compile(
        r"(pretend|simulate|roleplay)\s+(you\s+are|to\s+be|being)",
        re.IGNORECASE,
    )),
    ("instruction_boundary", re.compile(
        r"(end|start)\s+of\s+(system|user)\s+(prompt|message)",
        re.IGNORECASE,
    )),
]


# Regex names that block uploads even when the Layer 2 model is unavailable
HIGH_CONFIDENCE_BLOCKING_PATTERNS = frozenset({
    "ignore_previous_instructions",
    "reveal_system_prompt",
    "forget_your_role",
    "role_override",
    "act_as_override",
    "disregard_system",
    "new_instructions",
    "jailbreak_dan",
    "developer_mode",
    "xml_system_tag",
    "prompt_injection_delimiter",
    "base64_instruction",
    "bypass_safety",
    "pretend_roleplay",
    "instruction_boundary",
    "system_prompt_reference",
})


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text)


@dataclass(frozen=True)
class PatternHit:
    pattern_id: str
    matched_text: str
    char_offset: int


def _find_literal_hits(normalized_lower: str, literals: Tuple[str, ...], prefix: str) -> List[str]:
    hits: List[str] = []
    for literal in literals:
        if literal.lower() in normalized_lower:
            hits.append(f"{prefix}:{literal}")
    return hits


def _find_literal_details(
    normalized: str,
    normalized_lower: str,
    literals: Tuple[str, ...],
    prefix: str,
    base_offset: int,
) -> List[PatternHit]:
    hits: List[PatternHit] = []
    for literal in literals:
        needle = literal.lower()
        start = 0
        while True:
            pos = normalized_lower.find(needle, start)
            if pos == -1:
                break
            hits.append(
                PatternHit(
                    pattern_id=f"{prefix}:{literal}",
                    matched_text=normalized[pos : pos + len(literal)],
                    char_offset=base_offset + pos,
                )
            )
            start = pos + len(needle)
    return hits


def find_layer1_pattern_details(text: str, base_offset: int = 0) -> List[PatternHit]:
    """Layer 1 hits with global character offsets for location reporting."""
    normalized = normalize_text(text)
    normalized_lower = normalized.lower()
    hits: List[PatternHit] = []

    hits.extend(
        _find_literal_details(normalized, normalized_lower, SUSPICIOUS_LITERALS, "suspicious", base_offset)
    )
    hits.extend(
        _find_literal_details(normalized, normalized_lower, MALICIOUS_LITERALS, "malicious", base_offset)
    )

    for name, pattern in INJECTION_PATTERNS:
        for match in pattern.finditer(normalized):
            hits.append(
                PatternHit(
                    pattern_id=name,
                    matched_text=match.group(0),
                    char_offset=base_offset + match.start(),
                )
            )

    seen: set[tuple[int, str]] = set()
    unique: List[PatternHit] = []
    for hit in hits:
        key = (hit.char_offset, hit.pattern_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(hit)
    return unique


def find_layer1_suspicious_patterns(text: str) -> List[str]:
    """
    Layer 1 regex / substring filter.
    Returns pattern identifiers for any suspicious hit in the chunk.
    """
    normalized = normalize_text(text)
    normalized_lower = normalized.lower()
    hits: List[str] = []

    hits.extend(_find_literal_hits(normalized_lower, SUSPICIOUS_LITERALS, "suspicious"))
    hits.extend(_find_literal_hits(normalized_lower, MALICIOUS_LITERALS, "malicious"))

    for name, pattern in INJECTION_PATTERNS:
        if pattern.search(normalized):
            hits.append(name)

    return list(dict.fromkeys(hits))


def is_chunk_suspicious(text: str) -> bool:
    """True if Layer 1 flags the chunk for Layer 2 (Llama Guard) review."""
    return bool(find_layer1_suspicious_patterns(text))


def is_chunk_blocking_without_layer2(text: str) -> bool:
    """
    High-confidence Layer 1 hits that block even when the ML model is unavailable.
    Broad 'suspicious' literals (e.g. in 3GPP spec prose) escalate to L2 only.
    """
    normalized = normalize_text(text)
    normalized_lower = normalized.lower()

    for literal in MALICIOUS_LITERALS:
        if literal.lower() in normalized_lower:
            return True

    for name, pattern in INJECTION_PATTERNS:
        if name in HIGH_CONFIDENCE_BLOCKING_PATTERNS and pattern.search(normalized):
            return True

    return False


def find_injection_patterns(text: str) -> List[str]:
    """Backward-compatible alias for Layer 1 pattern names."""
    return find_layer1_suspicious_patterns(text)


def neutralize_injection_patterns(text: str) -> str:
    """Replace known injection phrases with a neutral marker (for LLM-bound text)."""
    normalized = normalize_text(text)
    for _name, pattern in INJECTION_PATTERNS:
        normalized = pattern.sub("[filtered-instruction]", normalized)
    for literal in (*SUSPICIOUS_LITERALS, *MALICIOUS_LITERALS):
        idx = literal.lower()
        # case-insensitive replace for literals
        start = 0
        lower = normalized.lower()
        while True:
            pos = lower.find(idx, start)
            if pos == -1:
                break
            normalized = normalized[:pos] + "[filtered-instruction]" + normalized[pos + len(literal):]
            lower = normalized.lower()
            start = pos + len("[filtered-instruction]")
    return normalized
