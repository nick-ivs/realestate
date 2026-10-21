from realestate.web import app

OFFER = """Offer information
Buyer name - Mykyta and Raj
He is PR
Property address - #406-12160 80 Avenue Surrey BC
Offer open till - 11 pm tonight
Disclosure date - October 22 2026
"""

AGENT = {
    "licensee_name": "Sample Licensee",
    "brokerage": "Sample Realty Ltd.",
    "commission": "3.22% on the first $100,000 and 1.15% on the balance",
    "commission_paid_by": "the listing brokerage",
    "place": "Surrey, BC",
}


def client():
    return app.test_client()


def test_page_and_form_spec_are_served():
    c = client()
    assert b"RealEstate Forms" in c.get("/").data
    keys = [i["key"] for i in c.get("/api/form").json["inputs"]]
    assert keys[:2] == ["buyer_names", "property_address"]


def test_parse_returns_fields_and_what_is_missing():
    res = client().post("/api/parse", json={"text": OFFER, "today": "2026-10-21"}).json
    assert res["values"]["buyer_names"] == "Mykyta and Raj"
    assert res["values"]["disclosure_date"] == "2026-10-22"  # ready for a date picker
    assert [m["key"] for m in res["missing"]] == ["licensee_name", "brokerage", "commission", "commission_paid_by"]
    assert res["derived"] == {"place": "Surrey"}
    assert res["not_on_form"]["offer expiry"] == "October 21, 2026, 11:00 PM"
    assert res["unrecognized"] == []


def test_check_with_edited_values_has_nothing_missing():
    values = {"buyer_names": "Mykyta Hryb and Raj Sharma", "property_address": "1 Main St, Surrey, BC V3W 3L9",
              "agency": "one party", **AGENT}
    res = client().post("/api/check", json={"values": values, "today": "2026-10-21"}).json
    assert res["missing"] == []
    assert res["warnings"] == []


def test_check_reports_values_too_long_for_the_form():
    values = {**AGENT, "brokerage": "An Extraordinarily Long Brokerage Name That Will Never Fit Realty Ltd."}
    res = client().post("/api/check", json={"values": values}).json
    assert any("too long" in w for w in res["warnings"])


COMPLETE = {"buyer_names": "Mykyta Hryb and Raj Sharma", "property_address": "#406-12160 80 Avenue Surrey BC", **AGENT}


def test_no_pdf_or_preview_while_information_is_missing():
    for path in ("/api/pdf", "/api/preview"):
        res = client().post(path, json={"values": AGENT})
        assert res.status_code == 422
        assert [m["key"] for m in res.json["missing"]] == ["buyer_names", "property_address"]


def test_pdf_is_returned_with_a_useful_name():
    res = client().post("/api/pdf?download=1", json={"values": COMPLETE})
    assert res.mimetype == "application/pdf"
    assert res.data.startswith(b"%PDF")
    assert "Disclosure of Remuneration - #406-12160 80 Avenue Surrey BC.pdf" in res.headers["Content-Disposition"]


def test_preview_is_an_image_of_the_filled_page():
    res = client().post("/api/preview", json={"values": COMPLETE})
    assert res.mimetype == "image/png"
    assert res.data.startswith(b"\x89PNG")


def test_also_found_is_not_alphabetized():
    res = client().post("/api/parse", json={"text": "Completion - Nov 15 2026\nHe is PR\nOffer open till - 11 pm tonight"}).json
    assert list(res["not_on_form"]) == ["residency status", "completion date", "offer expiry"]
