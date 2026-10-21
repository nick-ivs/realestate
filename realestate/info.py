"""Read deal information written as plain text, one fact per line.

Lines look like ``Buyer name - Mykyta and Raj`` or ``Completion: November 15 2026``.
A line without a separator ("He is PR") is matched by its words instead.
Labels are matched loosely, so "Buyer name", "Buyers" and "Purchaser" all land
on the same key.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

# key -> label patterns (regexes matched against the lower-cased label).
# Checked in order, so the specific referral/commission-payer labels come before
# the broader ones that would also match them.
KEY_PATTERNS: dict[str, list[str]] = {
    "referral_paid_by": [r"referral (fee |remuneration )?(paid )?(by|from)"],
    "referral_remuneration": [r"^referral (fee|remuneration)( amount)?$"],
    "referred_to_client": [r"referred to (the )?client"],
    "referred_client_to": [r"referred (the )?client to"],
    "commission_paid_by": [r"commission (paid )?(by|from)", r"^paid by$"],
    "buyer_names": [r"^buyers?( names?)?$", r"^purchasers?( names?)?$", r"^clients?( names?)?$",
                    r"^notice to$"],
    "residency": [r"residen", r"^status$", r"^immigration"],
    "property_address": [r"address", r"^property$", r"^subject (real estate|property)$"],
    "price": [r"price", r"^offer amount$"],
    "deposit": [r"deposit"],
    "subject_removal_date": [r"subject"],
    "completion_date": [r"completion"],
    "possession_date": [r"possession"],
    "offer_expiry": [r"offer (open|valid|good)", r"open (till|until)", r"irrevocab", r"acceptance"],
    "licensee_name": [r"licensee", r"^(realtor|agent)( name)?$"],
    "brokerage": [r"brokerage", r"^office$"],
    "agency": [r"agency", r"acting (for|as)", r"^representation$"],
    "commission": [r"^commission( amount| rate)?$"],
    "place": [r"^place", r"^city$", r"^signed (at|in)$"],
    "disclosure_date": [r"disclosure date", r"^date$"],
}

RESIDENCY_WORDS = {
    "pr": "Permanent Resident",
    "permanent resident": "Permanent Resident",
    "citizen": "Canadian Citizen",
    "foreign national": "Foreign National",
    "work permit": "Work Permit Holder",
}

SEPARATOR = re.compile(r"\s+[-–—]\s+|\s*:\s+|\s*=\s*")


@dataclass
class DealInfo:
    values: dict[str, str] = field(default_factory=dict)
    unrecognized: list[str] = field(default_factory=list)

    def get(self, key: str) -> str | None:
        value = self.values.get(key, "").strip()
        return value or None

    def merged_over(self, base: "DealInfo") -> "DealInfo":
        """Return a copy of ``base`` with this info's values taking precedence."""
        return DealInfo({**base.values, **self.values}, base.unrecognized + self.unrecognized)


def match_key(label: str) -> str | None:
    label = re.sub(r"\s+", " ", label.strip().lower())
    for key, patterns in KEY_PATTERNS.items():
        if any(re.search(p, label) for p in patterns):
            return key
    return None


def detect_residency(text: str) -> str | None:
    lowered = text.lower()
    for word, status in RESIDENCY_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return status
    return None


def is_heading(line: str) -> bool:
    """A short label-only line such as "Offer information"."""
    return line.endswith(":") or (len(line.split()) <= 3 and not re.search(r"\d", line))


def parse(text: str) -> DealInfo:
    info = DealInfo()
    for raw in text.splitlines():
        line = raw.strip().lstrip("*•").strip()
        if not line or line.startswith("#"):
            continue
        parts = SEPARATOR.split(line, maxsplit=1)
        key = match_key(parts[0]) if len(parts) == 2 else None
        if key:
            info.values[key] = parts[1].strip()
        elif status := detect_residency(line):
            info.values["residency"] = status
        elif is_heading(line):
            continue
        else:
            info.unrecognized.append(line)
    return info


def parse_file(path: str) -> DealInfo:
    with open(path, encoding="utf-8") as f:
        return parse(f.read())


DATE_FORMATS = ["%B %d %Y", "%B %d, %Y", "%b %d %Y", "%b %d, %Y", "%Y-%m-%d", "%d %B %Y"]
TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)", re.I)


def parse_date(text: str, today: date) -> date | None:
    text = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", text.strip())
    lowered = text.lower()
    if "tonight" in lowered or "today" in lowered:
        return today
    if "tomorrow" in lowered:
        return today + timedelta(days=1)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def parse_datetime(text: str, today: date) -> datetime | None:
    """Parse "11 pm tonight" or "October 30 2026 5:00 pm" style expiries."""
    found = TIME_RE.search(text)
    rest = re.sub(r"\bat\b", "", TIME_RE.sub("", text)).strip(" ,")
    day = parse_date(rest, today)
    if day is None or found is None:
        return None
    hour, minute = int(found.group(1)) % 12, int(found.group(2) or 0)
    if found.group(3).lower().startswith("p"):
        hour += 12
    return datetime.combine(day, time(hour, minute))


def format_date(d: date) -> str:
    return f"{d:%B} {d.day}, {d.year}"
