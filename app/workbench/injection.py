"""Possible prompt injection: chat lines that read like instructions to the AI
instead of lines of the conversation.

marked() only marks a message for the creator. Nothing is removed or changed:
the AI judge reads every message as data either way, and its prompt tells it
never to follow one. A persona probe like "you're an AI" is a line of the
conversation, not an instruction, so it isn't marked. Pure: no I/O.
"""

import re

_VERB = r"(?:ignore|disregard|forget|override|bypass)"
# Each pattern is checked against each line of a message, ignoring case.
PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        # A line that opens with a role label, like "SYSTEM:" or "### Instruction:".
        r"^\W{0,4}(?:system|assistant|developer|admin|administrator|instructions?|prompt)\W{0,4}\s*:",
        # "Ignore your rules", "disregard all previous instructions".
        rf"\b{_VERB}\s+(?:all\s+|any\s+)?(?:of\s+)?(?:your|previous|prior|earlier|preceding|above|the\s+above"
        r"|the\s+previous|the\s+prior|these|those)\s+(?:\w+\s+){0,2}"
        r"(?:rules|instructions|prompts?|spec|guidelines|directions|programming)\b",
        # "Ignore the instructions", "disregard the spec".
        rf"\b{_VERB}\s+(?:(?:all|any|the|of)\s+)*(?:instructions|prompts?|system\s+prompt|spec|guidelines)\b",
        # "Return no flags", "don't flag this".
        r"\b(?:return|give|report|output|raise|send|produce|list)\b[^\n.!?]{0,20}?\bno\s+flags?\b",
        r"\bdo(?:n'?t|\s+not)\s+(?:flag|report)\b|\bflag\s+nothing\b|\bzero\s+flags\b",
        # "From now on you are", "you are now an unrestricted AI", "developer mode".
        r"\bfrom\s+now\s+on,?\s+you\s+(?:are|will|must|should)\b",
        r"\byou\s+are\s+now\s+(?:an?\s+|the\s+)?"
        r"(?:ai|assistant|chatbot|language\s+model|unrestricted|jailbroken|in\s+developer\s+mode)\b",
        r"\b(?:developer|god|jailbreak|dan)\s+mode\b|\bnew\s+(?:system\s+)?instructions\s*:",
        # Chat template tokens: <|im_start|>, [INST], <<SYS>>.
        r"<\|[a-z_]{2,20}\|>|\[/?inst\]|<</?sys>>",
    )
]


def marked(text: str) -> bool:
    """True when a line of the text reads like an instruction to the AI."""
    return any(pattern.search(line) for line in text.splitlines() for pattern in PATTERNS)
