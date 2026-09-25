"""
Password strength analysis and cryptographically secure generation.

The scoring model mirrors the entropy-based approach from PassForge's
original web prototype: strength is estimated from the real size of the
guessing space (entropy), then penalized for known-bad patterns, rather
than from a naive "does it contain a symbol" checkbox count.
"""

import math
import re
import secrets
from dataclasses import dataclass, field
from typing import Optional

COMMON_PASSWORDS = {
    "123456", "123456789", "password", "12345678", "qwerty", "12345",
    "1234", "111111", "1234567", "dragon", "123123", "qwerty123",
    "iloveyou", "000000", "admin", "letmein", "welcome", "monkey",
    "password1", "abc123", "football", "baseball", "sunshine", "princess",
    "login", "master", "hello", "freedom", "whatever", "qazwsx",
    "trustno1", "superman", "shadow", "michael", "mustang", "hunter",
    "starwars", "computer", "passw0rd", "changeme", "secret", "summer",
    "access", "flower", "batman", "test", "pass", "121212", "abcd1234",
    "qwertyuiop", "1qaz2wsx", "password123",
}

KEYBOARD_RUNS = [
    "qwertyuiop", "asdfghjkl", "zxcvbnm", "1234567890", "0987654321",
    "qazwsx", "wsxedc",
]


def _has_sequential_run(pw: str, min_run: int = 4) -> bool:
    lower = pw.lower()
    for run in KEYBOARD_RUNS:
        for i in range(len(run) - min_run + 1):
            if run[i:i + min_run] in lower:
                return True
    for i in range(len(lower) - min_run + 1):
        window = lower[i:i + min_run]
        codes = [ord(c) for c in window]
        ascending = all(b - a == 1 for a, b in zip(codes, codes[1:]))
        descending = all(a - b == 1 for a, b in zip(codes, codes[1:]))
        if ascending or descending:
            return True
    return False


def _has_repeated_run(pw: str, min_run: int = 3) -> bool:
    return re.search(r"(.)\1{" + str(min_run - 1) + ",}", pw) is not None


@dataclass
class StrengthResult:
    score: int                 # 0-100
    label: str                 # Very weak / Weak / Fair / Good / Strong
    entropy_bits: float
    checks: dict = field(default_factory=dict)
    suggestions: list = field(default_factory=list)


def analyze_strength(pw: str) -> StrengthResult:
    if not pw:
        return StrengthResult(0, "Empty", 0.0, {}, ["Enter a password."])

    checks = {
        "length": len(pw) >= 12,
        "case": bool(re.search(r"[a-z]", pw)) and bool(re.search(r"[A-Z]", pw)),
        "digit": bool(re.search(r"[0-9]", pw)),
        "symbol": bool(re.search(r"[^A-Za-z0-9]", pw)),
    }

    is_common = pw.lower() in COMMON_PASSWORDS
    sequential = _has_sequential_run(pw)
    repeated = _has_repeated_run(pw)
    checks["pattern"] = not (is_common or sequential or repeated)

    charset_size = 0
    if re.search(r"[a-z]", pw):
        charset_size += 26
    if re.search(r"[A-Z]", pw):
        charset_size += 26
    if re.search(r"[0-9]", pw):
        charset_size += 10
    if re.search(r"[^A-Za-z0-9]", pw):
        charset_size += 32
    charset_size = charset_size or 1

    entropy_bits = len(pw) * math.log2(charset_size)
    if is_common:
        entropy_bits = min(entropy_bits, 8)
    elif sequential or repeated:
        entropy_bits *= 0.5

    score = max(0, min(100, round((entropy_bits / 80) * 100)))

    if score < 20:
        label = "Very weak"
    elif score < 40:
        label = "Weak"
    elif score < 60:
        label = "Fair"
    elif score < 80:
        label = "Good"
    else:
        label = "Strong"

    suggestions = []
    if not checks["length"]:
        suggestions.append("Use at least 12 characters.")
    if not checks["case"]:
        suggestions.append("Mix uppercase and lowercase letters.")
    if not checks["digit"]:
        suggestions.append("Add at least one number.")
    if not checks["symbol"]:
        suggestions.append("Add a symbol, e.g. ! @ # $ %.")
    if is_common:
        suggestions.append("This is a widely used, breached password — avoid it entirely.")
    elif sequential:
        suggestions.append("Avoid keyboard runs or sequences like \"qwerty\" or \"1234\".")
    elif repeated:
        suggestions.append("Avoid repeating the same character several times in a row.")

    return StrengthResult(score, label, entropy_bits, checks, suggestions)


# ---------------------------------------------------------------------------
# Secure generation — uses `secrets`, Python's CSPRNG module, never `random`.
# ---------------------------------------------------------------------------

_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"       # no I/O
_LOWER = "abcdefghijkmnopqrstuvwxyz"      # no l
_DIGITS = "23456789"                      # no 0/1
_SYMBOLS = "!@#$%^&*()-_=+[]{}"
_AMBIGUOUS = {"upper": "IO", "lower": "l", "digits": "01"}


def generate_password(
    length: int = 20,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    exclude_ambiguous: bool = False,
) -> Optional[str]:
    pools = []
    if use_upper:
        pools.append(_UPPER if exclude_ambiguous else _UPPER + _AMBIGUOUS["upper"])
    if use_lower:
        pools.append(_LOWER if exclude_ambiguous else _LOWER + _AMBIGUOUS["lower"])
    if use_digits:
        pools.append(_DIGITS if exclude_ambiguous else _DIGITS + _AMBIGUOUS["digits"])
    if use_symbols:
        pools.append(_SYMBOLS)

    if not pools:
        return None

    all_chars = "".join(pools)
    chars = [secrets.choice(pool) for pool in pools]  # guarantee each class appears
    while len(chars) < length:
        chars.append(secrets.choice(all_chars))

    # Cryptographically secure shuffle (Fisher-Yates using `secrets`).
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]

    return "".join(chars[:length])


WORDLIST = [
    "anchor", "banjo", "cactus", "dolphin", "ember", "falcon", "garnet",
    "harbor", "island", "jungle", "kernel", "lagoon", "meadow", "nectar",
    "oyster", "pebble", "quartz", "raven", "summit", "temple", "umbrella",
    "velvet", "willow", "zephyr", "amber", "bronze", "canyon", "desert",
    "echo", "forest", "glacier", "horizon", "ivory", "jasper", "kettle",
    "lantern", "marble", "nutmeg", "olive", "prairie", "quiver", "ribbon",
    "sable", "thicket", "urchin", "violet", "walnut", "yonder", "acorn",
    "basil", "cedar", "dune", "ferry", "granite", "hazel", "indigo",
    "juniper", "kayak", "lily", "maple", "nomad", "orchid", "pine",
    "quail", "ridge", "sparrow", "timber", "vale", "wren", "yarrow",
]


def generate_passphrase(word_count: int = 5, capitalize: bool = True,
                         append_number: bool = True, separator: str = "-") -> str:
    words = [secrets.choice(WORDLIST) for _ in range(word_count)]
    if capitalize:
        words = [w.capitalize() for w in words]
    if append_number:
        words.append(str(secrets.randbelow(100)).zfill(2))
    return separator.join(words)
