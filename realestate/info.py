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


# BC municipalities, plus neighbourhoods people write in place of their city.
BC_CITIES = [
    "Abbotsford", "Anmore", "Armstrong", "Belcarra", "Bowen Island", "Burnaby", "Campbell River", "Castlegar",
    "Central Saanich", "Chilliwack", "Coldstream", "Colwood", "Comox", "Coquitlam", "Courtenay", "Cranbrook",
    "Dawson Creek", "Delta", "Duncan", "Esquimalt", "Fernie", "Fort St. John", "Gibsons", "Golden", "Harrison Hot Springs",
    "Hope", "Kamloops", "Kelowna", "Kent", "Kimberley", "Kitimat", "Ladysmith", "Lake Country", "Langford",
    "Langley", "Lions Bay", "Maple Ridge", "Merritt", "Metchosin", "Mission", "Nanaimo", "Nelson", "New Westminster",
    "North Cowichan", "North Saanich", "North Vancouver", "Oak Bay", "Oliver", "Osoyoos", "Parksville", "Peachland",
    "Penticton", "Pitt Meadows", "Port Alberni", "Port Coquitlam", "Port Moody", "Powell River", "Prince George",
    "Prince Rupert", "Qualicum Beach", "Quesnel", "Revelstoke", "Richmond", "Saanich", "Salmon Arm", "Sechelt",
    "Sidney", "Sooke", "Squamish", "Summerland", "Surrey", "Terrace", "Tofino", "Trail", "Ucluelet", "Vancouver",
    "Vernon", "Victoria", "View Royal", "West Kelowna", "West Vancouver", "Whistler", "White Rock", "Williams Lake",
]
NEIGHBOURHOODS = {
    "South Surrey": "Surrey", "Cloverdale": "Surrey", "Fleetwood": "Surrey", "Guildford": "Surrey", "Whalley": "Surrey",
    "Newton": "Surrey", "North Delta": "Delta", "Ladner": "Delta", "Tsawwassen": "Delta", "Walnut Grove": "Langley",
    "Willoughby": "Langley", "Aldergrove": "Langley", "Murrayville": "Langley", "Burke Mountain": "Coquitlam",
    "Steveston": "Richmond", "Yaletown": "Vancouver", "Kitsilano": "Vancouver",
}
STREET_WORDS = (r"street|st|avenue|ave|road|rd|drive|dr|way|boulevard|blvd|crescent|cres|place|pl|court|ct|lane|ln|"
                r"highway|hwy|parkway|pkwy|terrace|close|gate|row|mews|walk|trail|square|sq")
_PLACE_NAMES = sorted([*BC_CITIES, *NEIGHBOURHOODS], key=len, reverse=True)


def city_from_address(address: str) -> str | None:
    """The city in an address, e.g. "#406-12160 80 Avenue Surrey BC" -> "Surrey".

    The last place name wins, so a street named after another city ("Victoria
    Drive, Vancouver") still gives the right one, and a name followed by a
    street word ("Surrey Road") is not taken as the city.
    """
    found: list[tuple[int, int, str]] = []
    for name in _PLACE_NAMES:  # longest first, so "North Vancouver" beats "Vancouver"
        pattern = rf"(?<![\w.]){re.escape(name)}(?!\w)(?!\s*,?\s*(?:{STREET_WORDS})\b\.?)"
        for m in re.finditer(pattern, address, re.I):
            if not any(start <= m.start() < end for start, end, _ in found):
                found.append((m.start(), m.end(), name))
    if not found:
        return None
    name = max(found)[2]
    return NEIGHBOURHOODS.get(name, name)


ADDRESS_RE = re.compile(rf"^#?\s*\d+[a-z]?\s*[-–]?\s*\d*\s+.*\b({STREET_WORDS})\b", re.I)


def looks_like_address(line: str) -> bool:
    return bool(ADDRESS_RE.search(line)) or (bool(re.match(r"#?\s*\d", line)) and city_from_address(line) is not None)


MONTHS = r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
VALUE_START = re.compile(rf"^(\d|#|\$|({MONTHS})[a-z]*\.?$|today|tonight|tomorrow|noon)", re.I)


def split_unseparated(line: str) -> tuple[str, str] | None:
    """Read "Completion November 15 2026" as label "Completion" and its value.

    The label is the leading words before the value starts (a number, month or
    "tonight"), shortened from the end until it names a known field.
    """
    words = line.split()
    end = next((i for i, w in enumerate(words) if VALUE_START.match(w)), len(words))
    for n in range(min(end, 5), 0, -1):
        if n < len(words) and (key := match_key(" ".join(words[:n]))):
            return key, " ".join(words[n:])
    return None


NAMES_RE = re.compile(r"^[A-Z][\w'’-]*(\s+[A-Z][\w'’-]*)*(\s*(,|&|\band\b)\s*[A-Z][\w'’-]*(\s+[A-Z][\w'’-]*)*)+$")


def looks_like_names(line: str) -> bool:
    """ "Mykyta and Raj" or "Jane Doe & John Lee": capitalized names joined by and/&/commas."""
    return bool(NAMES_RE.match(line)) and city_from_address(line) is None


def is_heading(line: str) -> bool:
    """A label-only line such as "Offer information" or "Details:"."""
    return line.endswith(":") or bool(
        re.fullmatch(r"((new |the )?(offer|deal|buyer|property|client|purchase)s?)?\s*(info(rmation)?|details|summary|notes?)?", line, re.I))


def parse(text: str) -> DealInfo:
    info = DealInfo()
    for raw in text.splitlines():
        line = raw.strip().lstrip("*•").strip()
        if not line or re.match(r"#(?!\s*\d)", line):  # a comment, not "#406-..."
            continue
        parts = SEPARATOR.split(line, maxsplit=1)
        key = match_key(parts[0]) if len(parts) == 2 else None
        if key:
            info.values[key] = parts[1].strip()
        elif status := detect_residency(line):
            info.values["residency"] = status
        elif "property_address" not in info.values and looks_like_address(line):
            info.values["property_address"] = line
        elif found := split_unseparated(line):
            info.values.setdefault(found[0], found[1])
        elif is_heading(line):
            continue
        elif "buyer_names" not in info.values and looks_like_names(line):
            info.values["buyer_names"] = line
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
