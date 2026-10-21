"""Web interface: paste the offer, check the fields, download the filled PDF.

    python -m realestate.web            # then open http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import io
import re
import threading
import webbrowser
from dataclasses import asdict
from datetime import date

import pypdfium2
from flask import Flask, jsonify, request, send_file

from . import info as info_mod
from .forms import disclosure_of_remuneration as form
from .pdf import fill, overflowing

app = Flask(__name__)
app.json.sort_keys = False  # keep fields in the order the form and the user wrote them


def request_today() -> date:
    """The browser's local date, so "tonight" means the user's tonight."""
    try:
        return date.fromisoformat(request.json.get("today", ""))
    except (TypeError, ValueError):
        return date.today()


def request_info() -> info_mod.DealInfo:
    values = request.json.get("values") or {}
    return info_mod.DealInfo({k: str(v) for k, v in values.items() if isinstance(v, (str, int, float)) and str(v).strip()})


def check(deal: info_mod.DealInfo, today: date) -> dict:
    result = form.build(deal, today)
    return {
        "missing": [asdict(m) for m in result.missing],
        "warnings": result.warnings + overflowing(result.fields, result.values),
        "not_on_form": result.not_on_form,
    }


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/form")
def form_spec():
    return jsonify(name=form.NAME, inputs=[asdict(i) for i in form.INPUTS])


@app.post("/api/parse")
def parse():
    """Turn the pasted text into field values, plus what is still missing."""
    today = request_today()
    deal = info_mod.parse(request.json.get("text", ""))
    # The page shows this in a date picker, which takes YYYY-MM-DD.
    if raw := deal.get("disclosure_date"):
        if (day := info_mod.parse_date(raw, today)) is not None:
            deal.values["disclosure_date"] = day.isoformat()
    return jsonify(values=deal.values, unrecognized=deal.unrecognized, **check(deal, today))


@app.post("/api/check")
def recheck():
    return jsonify(check(request_info(), request_today()))


def filled_pdf() -> bytes:
    result = form.build(request_info(), request_today())
    return fill(result.template, result.fields, result.values)[0]


@app.post("/api/preview")
def preview():
    """The filled first page as an image: every browser shows it, unlike an embedded PDF."""
    page = pypdfium2.PdfDocument(filled_pdf())[0]
    image = page.render(scale=2).to_pil()
    out = io.BytesIO()
    image.save(out, "PNG", optimize=True)
    out.seek(0)
    return send_file(out, mimetype="image/png")


@app.post("/api/pdf")
def pdf():
    data = filled_pdf()
    address = re.sub(r"[^\w#,. -]+", "", request_info().get("property_address") or "").strip()
    name = f"Disclosure of Remuneration{' - ' + address if address else ''}.pdf"
    return send_file(io.BytesIO(data), mimetype="application/pdf", download_name=name,
                     as_attachment=request.args.get("download") == "1")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="realestate-web", description="Run the RealEstate web interface.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--open", action="store_true", help="open the page in your browser once the server is up")
    args = parser.parse_args(argv)
    url = f"http://{args.host}:{args.port}"
    print(f"RealEstate is running: open {url} in your browser (Ctrl+C to stop)")
    if args.open:
        threading.Timer(1.0, webbrowser.open, [url]).start()
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
