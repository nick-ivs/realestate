from datetime import date, datetime

from realestate.info import city_from_address, parse, parse_date, parse_datetime

TODAY = date(2026, 10, 21)

OFFER = """Offer information

Buyer name - Mykyta and Raj
He is PR
property Address - #406-12160 80 Avenue Surrey BC

Subject removal date - October 30 2026
Completion - November 15 2026
Possession - November 16 2026
Offer open till - 11 pm tonight
"""


def test_parses_the_offer_format():
    info = parse(OFFER)
    assert info.values == {
        "buyer_names": "Mykyta and Raj",
        "residency": "Permanent Resident",
        "property_address": "#406-12160 80 Avenue Surrey BC",
        "subject_removal_date": "October 30 2026",
        "completion_date": "November 15 2026",
        "possession_date": "November 16 2026",
        "offer_expiry": "11 pm tonight",
    }
    assert info.unrecognized == []


def test_specific_labels_win_over_broad_ones():
    info = parse("Commission paid by - Listing Realty\nReferral fee paid by - Mortgage Co\nCommission - 3%")
    assert info.values == {
        "commission_paid_by": "Listing Realty",
        "referral_paid_by": "Mortgage Co",
        "commission": "3%",
    }


def test_colon_separator_and_unknown_lines():
    info = parse("Buyers: Jane Doe\nthe cat is orange today 2026")
    assert info.values == {"buyer_names": "Jane Doe"}
    assert info.unrecognized == ["the cat is orange today 2026"]


def test_dates():
    assert parse_date("October 30 2026", TODAY) == date(2026, 10, 30)
    assert parse_date("Nov 15th, 2026", TODAY) == date(2026, 11, 15)
    assert parse_date("2026-11-16", TODAY) == date(2026, 11, 16)
    assert parse_date("someday", TODAY) is None
    assert parse_datetime("11 pm tonight", TODAY) == datetime(2026, 10, 21, 23, 0)
    assert parse_datetime("October 22 2026 at 9:30 am", TODAY) == datetime(2026, 10, 22, 9, 30)


def test_messy_offer_without_labels_or_dashes():
    info = parse("""New offer
Mykyta and Raj
#406-12160 80 Avenue Surrey BC
he is pr
Subject removal October 30 2026
Completion November 15 2026
possession: Nov 16 2026
Offer open till 11 pm tonight""")
    assert info.values == {
        "buyer_names": "Mykyta and Raj",
        "property_address": "#406-12160 80 Avenue Surrey BC",
        "residency": "Permanent Resident",
        "subject_removal_date": "October 30 2026",
        "completion_date": "November 15 2026",
        "possession_date": "Nov 16 2026",
        "offer_expiry": "11 pm tonight",
    }
    assert info.unrecognized == []


def test_unknown_lines_are_reported_not_dropped():
    assert parse("the cat sat on the mat").unrecognized == ["the cat sat on the mat"]


def test_city_from_address():
    cases = {
        "#406-12160 80 Avenue Surrey BC": "Surrey",
        "123 Victoria Drive, Vancouver, BC V5L 4C8": "Vancouver",  # street named after a city
        "5 Surrey Road, Langley": "Langley",
        "1500 Marine Dr North Vancouver": "North Vancouver",  # longest name wins
        "15 Johnston Rd, White Rock": "White Rock",
        "8 Ladner Trunk Rd, Ladner BC": "Delta",  # neighbourhood -> municipality
        "12 Main St": None,
    }
    for address, city in cases.items():
        assert city_from_address(address) == city, address
