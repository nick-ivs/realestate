import io
from datetime import date

import pdfplumber

from realestate.forms import disclosure_of_remuneration as form
from realestate.info import parse
from realestate.pdf import INK, fill

TODAY = date(2026, 10, 21)

OFFER = """Buyer name - Mykyta Hryb and Raj Sharma
He is PR
Property address - #406-12160 80 Avenue Surrey BC V3W 3L9
Completion - November 15 2026
Offer open till - 11 pm tonight
"""

PROFILE = """Licensee name - Sample Licensee
Brokerage - Sample Realty Ltd.
Agency - one party
Commission - 3.22% on the first $100,000 and 1.15% on the balance
Commission paid by - the listing brokerage
Place - Surrey, BC
"""


def build(text):
    return form.build(parse(text), TODAY)


def test_offer_alone_reports_the_licensee_details_as_missing():
    result = build(OFFER)
    assert [m.key for m in result.missing] == ["licensee_name", "brokerage", "commission", "commission_paid_by"]
    assert result.derived == {"place": "Surrey"}
    assert result.values["client_name"] == "Mykyta Hryb and Raj Sharma"
    assert result.values["d_date"] == "October 21, 2026"


def test_complete_info_has_nothing_missing():
    result = build(OFFER + PROFILE)
    assert result.missing == []
    assert result.warnings == []
    assert result.values["b1_licensee"] == "Sample Licensee"
    assert "b2_licensee" not in result.values


def test_first_names_only_and_no_agency_are_flagged():
    result = build("Buyer name - Mykyta and Raj\nProperty address - 1 Main St")
    assert any("first names only" in w for w in result.warnings)
    assert any("Agency was not stated" in w for w in result.warnings)
    assert any("postal code" in w for w in result.warnings)


def test_dual_agency_fills_the_dual_section():
    result = build(OFFER + PROFILE.replace("one party", "dual"))
    assert result.values["b2_brokerage"] == "Sample Realty Ltd."
    assert "b1_brokerage" not in result.values


def test_offer_terms_are_reported_as_not_on_this_form():
    result = build(OFFER)
    assert result.not_on_form == {
        "residency status": "Permanent Resident",
        "completion date": "November 15, 2026",
        "offer expiry": "October 21, 2026, 11:00 PM",
    }


def test_values_land_on_their_blanks():
    result = build(OFFER + PROFILE)
    pdf, problems = fill(result.template, result.fields, result.values)
    assert problems == []
    page = pdfplumber.open(io.BytesIO(pdf)).pages[0]
    # Only our layer: the form's own underscores would otherwise split the words.
    filled = page.filter(lambda obj: obj.get("object_type") != "char" or tuple(obj.get("non_stroking_color") or ()) == INK)
    words = filled.extract_words()
    for field in result.fields:
        value = result.values.get(field.name)
        if not value:
            continue
        first = value.split()[0]
        hits = [w for w in words if w["text"] == first and abs(w["x0"] - field.x0) < 1 and abs(w["bottom"] - field.baseline) < 3.5]
        assert hits, f"{field.name}: {value!r} not drawn at its blank"


def test_too_long_values_are_reported():
    result = build(OFFER + PROFILE.replace("Sample Realty Ltd.", "A Very Long Brokerage Name That Cannot Possibly Fit Here Ltd."))
    _, problems = fill(result.template, result.fields, result.values)
    assert any("too long" in p for p in problems)


def test_place_comes_from_the_property_city_unless_given():
    assert build(OFFER).values["d_place"] == "Surrey"
    assert build(OFFER + "Place - Vancouver, BC").values["d_place"] == "Vancouver, BC"
    no_city = build("Buyer name - Jane Doe\nProperty address - 12 Main St")
    assert "place" in [m.key for m in no_city.missing]
