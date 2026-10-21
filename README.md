# RealEstate

Fills BC real estate forms from plain-text deal information. It checks what is
missing or doubtful, asks for it, and writes a PDF that is the original form,
untouched, with the blanks filled in a clean Helvetica.

Supported forms:

- **BCFSA Disclosure of Remuneration – Trading Services** (Rev 06/2021)

## Setup

```sh
pip install -e ".[test]"
```

## Use

Write the offer the way you would in a message:

```text
Buyer name - Mykyta and Raj
He is PR
Property address - #406-12160 80 Avenue Surrey BC
Subject removal date - October 30 2026
Completion - November 15 2026
Possession - November 16 2026
Offer open till - 11 pm tonight
```

Keep your own licensee details in a profile file so you write them once
(see `examples/agent.txt`), then run:

```sh
python -m realestate examples/offer.txt --profile examples/agent.txt -o filled.pdf
```

In a terminal it asks for anything the form still needs. With `--no-prompt`
(or when not run interactively) it leaves those blanks empty and lists them.
It exits with status 1 while anything required is missing.

The report also flags things worth a second look (first names only, no postal
code, agency not stated, a value too long for its blank) and lists the offer
terms this form has no place for, so nothing you gave it is silently dropped.

Labels are matched loosely: "Buyer name", "Buyers" and "Purchaser" all work,
and "Label: value" works as well as "Label - value".

## What the Disclosure of Remuneration needs

| Blank | Info label |
| --- | --- |
| Notice to (name of client) | `Buyer name` |
| Street address of subject real estate | `Property address` |
| Name of licensee | `Licensee name` |
| Name of brokerage | `Brokerage` |
| Commission (amount or method) | `Commission` |
| Commission paid by | `Commission paid by` |
| One party or dual agent | `Agency` (`one party` or `dual`; defaults to one party) |
| Place | `Place` |
| Date | `Disclosure date` (defaults to today) |
| Part C referral fees (optional) | `Referral fee`, `Referral fee paid by`, `Referred client to`, `Referred to client` |

Signature lines are always left blank.

## Adding a form

A form lives in `realestate/forms/`: a list of `Field`s (where each blank sits,
measured in PDF points from the top-left of the page) and a `build()` that
turns `DealInfo` into values, missing items and warnings. The template PDF
goes in `realestate/templates/`.

## Tests

```sh
python -m pytest
```
