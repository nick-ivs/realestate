"""BCFSA Disclosure of Remuneration – Trading Services (Rev 06/2021)."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from ..info import DealInfo, format_date, parse_date, parse_datetime
from ..pdf import Field
from . import FormResult, Input, Missing

NAME = "BCFSA Disclosure of Remuneration"
TEMPLATE = str(Path(__file__).resolve().parent.parent / "templates" / "bcfsa_disclosure_of_remuneration.pdf")

# Measured from the template's underscore runs: baseline sits 3pt above the
# bottom of each run so text rests on the line without touching it.
FIELDS = [
    # Part A
    Field("client_name", "Notice to (name of client)", 200, 578, 171.8),
    Field("property_address", "Street address of subject real estate", 200, 578, 194.8),
    # Part B – acting for one party
    Field("b1_licensee", "Part B (one party): name of licensee", 48, 226, 250.2),
    Field("b1_brokerage", "Part B (one party): name of brokerage", 43.5, 212.5, 275.6),
    Field("b1_commission", "Part B (one party): commission", 354, 567.5, 275.9),
    Field("b1_paid_by", "Part B (one party): commission paid by", 62, 204, 299.7),
    # Part B – acting as dual agent
    Field("b2_licensee", "Part B (dual agent): name of licensee", 48, 226, 348.8),
    Field("b2_brokerage", "Part B (dual agent): name of brokerage", 43.5, 212.5, 374.1),
    Field("b2_commission", "Part B (dual agent): commission", 356, 569.5, 374.4),
    Field("b2_paid_by", "Part B (dual agent): commission paid by", 62, 239.5, 399.4),
    # Part C – referral fees
    Field("c_licensee", "Part C: name of licensee", 48, 226, 461.0),
    Field("c_brokerage", "Part C: name of brokerage", 43.5, 266, 486.3),
    Field("c_remuneration", "Part C: form or amount of remuneration", 43.5, 190.5, 510.4),
    Field("c_paid_by", "Part C: remuneration paid by", 217, 386.5, 510.6),
    Field("c_referred_client_to", "Part C (a): client referred to", 258.5, 486, 538.2),
    Field("c_referred_to_client", "Part C (b): referred to client", 237, 486.5, 561.2),
    # Part D
    Field("d_place", "Part D: place of disclosure", 46, 206, 647.2),
    Field("d_date", "Part D: date of disclosure", 228, 357, 647.3),
    Field("d_licensee", "Part D: name of licensee", 110, 301.5, 672.5),
    Field("d_ack_place", "Part D: place of acknowledgement", 338.5, 455, 699.0),
    Field("d_ack_date", "Part D: date of acknowledgement", 472.5, 574.5, 699.0),
]

# What the form asks for, in the order a person would fill it in.
INPUTS = [
    Input("buyer_names", "Buyer name(s)", "Client & property",
          "full legal names of every buyer, e.g. \"Mykyta Hryb and Raj Sharma\""),
    Input("property_address", "Property address", "Client & property",
          "unit, street, city, e.g. \"#406 - 12160 80 Avenue, Surrey, BC\""),
    Input("licensee_name", "Licensee name", "Your details", "your name as it appears on your BCFSA licence"),
    Input("brokerage", "Brokerage", "Your details", "your related brokerage, e.g. \"Sample Realty Ltd.\""),
    Input("place", "Place of disclosure", "Your details", "city where the form is presented, e.g. \"Surrey, BC\""),
    Input("agency", "Agency", "Commission", "acting for one party, or as dual agent", required=False,
          choices=("one party", "dual")),
    Input("commission", "Commission", "Commission",
          "amount or method, e.g. \"3.22% on the first $100,000 and 1.15% on the balance\""),
    Input("commission_paid_by", "Commission paid by", "Commission", "who pays it, e.g. the listing brokerage's name"),
    Input("disclosure_date", "Disclosure date", "Commission", "defaults to today", required=False, kind="date"),
    Input("referral_remuneration", "Referral fee", "Referral fees (Part C)", "form or amount, only if you receive one",
          required=False),
    Input("referral_paid_by", "Referral fee paid by", "Referral fees (Part C)", "who pays the referral fee", required=False),
    Input("referred_client_to", "Client referred to", "Referral fees (Part C)",
          "who you referred the client to", required=False),
    Input("referred_to_client", "Referred to client", "Referral fees (Part C)",
          "who you referred to the client", required=False),
]
INPUT_BY_KEY = {i.key: i for i in INPUTS}

# Information that is useful for the deal but has no place on this form.
NOT_ON_THIS_FORM = {
    "residency": "residency status",
    "price": "purchase price",
    "deposit": "deposit",
    "subject_removal_date": "subject removal date",
    "completion_date": "completion date",
    "possession_date": "possession date",
    "offer_expiry": "offer expiry",
}


def readable(key: str, value: str, today: date) -> str:
    """Show dates the way they were understood, so a misread is easy to spot."""
    if key == "offer_expiry":
        if (when := parse_datetime(value, today)) is not None:
            return f"{format_date(when.date())}, {when.hour % 12 or 12}:{when:%M %p}"
    elif key.endswith("_date"):
        if (day := parse_date(value, today)) is not None:
            return format_date(day)
    return value


def agency_kind(value: str | None) -> str | None:
    if value is None:
        return None
    lowered = value.lower()
    if "dual" in lowered or "both" in lowered:
        return "dual"
    if re.search(r"one|single|buyer|seller|purchaser|vendor", lowered):
        return "one"
    return None


def build(info: DealInfo, today: date) -> FormResult:
    result = FormResult(NAME, TEMPLATE, FIELDS)
    v = result.values

    def need(key: str) -> str | None:
        value = info.get(key)
        if value is None:
            spec = INPUT_BY_KEY[key]
            result.missing.append(Missing(key, spec.label, spec.hint))
        return value

    def missing(key: str) -> None:
        spec = INPUT_BY_KEY[key]
        result.missing.append(Missing(key, spec.label, spec.hint))

    # Part A
    if buyers := need("buyer_names"):
        v["client_name"] = buyers
        names = [n.strip() for n in re.split(r",|\band\b|&", buyers) if n.strip()]
        if any(len(n.split()) < 2 for n in names):
            result.warnings.append(
                f"Buyer name \"{buyers}\" looks like first names only. Use full legal names as they will appear on the contract."
            )
    if address := need("property_address"):
        v["property_address"] = address
        if not re.search(r"[A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d", address):
            result.warnings.append("Property address has no postal code. It is not required on this form, but worth adding.")

    # Part B
    licensee = need("licensee_name")
    brokerage = need("brokerage")
    commission = need("commission")
    paid_by = need("commission_paid_by")

    kind = agency_kind(info.get("agency"))
    if kind is None:
        kind = "one"
        result.warnings.append(
            "Agency was not stated; filled Part B as \"acting for one party\". Add \"Agency - dual\" if you act for both sides."
        )
    prefix = "b1" if kind == "one" else "b2"
    for suffix, value in (("licensee", licensee), ("brokerage", brokerage), ("commission", commission), ("paid_by", paid_by)):
        if value:
            v[f"{prefix}_{suffix}"] = value

    # Part C – only when a referral fee is declared
    referral = info.get("referral_remuneration")
    if referral:
        v["c_remuneration"] = referral
        for key in ("referral_paid_by", "referred_client_to", "referred_to_client"):
            if value := info.get(key):
                v["c_" + key.removeprefix("referral_")] = value
        if licensee:
            v["c_licensee"] = licensee
        if brokerage:
            v["c_brokerage"] = brokerage
        if not info.get("referral_paid_by"):
            missing("referral_paid_by")
        if not (info.get("referred_client_to") or info.get("referred_to_client")):
            missing("referred_client_to")

    # Part D
    place = need("place")
    when = today
    if raw := info.get("disclosure_date"):
        parsed = parse_date(raw, today)
        if parsed is None:
            result.warnings.append(f"Could not read the disclosure date \"{raw}\"; used today instead.")
        else:
            when = parsed
    if place:
        v["d_place"] = v["d_ack_place"] = place
    v["d_date"] = v["d_ack_date"] = format_date(when)
    if licensee:
        v["d_licensee"] = licensee

    result.not_on_form = {label: readable(key, info.get(key), today) for key, label in NOT_ON_THIS_FORM.items() if info.get(key)}
    return result
