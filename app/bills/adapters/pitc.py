"""Shared code for the electricity companies whose bills PITC hosts at bill.pitc.com.pk.

LESCO, GEPCO, FESCO, IESCO, MEPCO, PESCO, HESCO, QESCO, SEPCO and TESCO all use the
same page and bill layout, so each of them is a few lines (see gepco.py).

How a bill is fetched:
  1. A POST to `/<slug>/general/<reference number>`, which currently answers with the
     bill page directly.
  2. If the portal stops doing that and asks for its CAPTCHA instead, `fetch()` returns
     the CAPTCHA as a Challenge for the user to read; nothing here reads or skips it.
"""

from __future__ import annotations

import re
from datetime import date
from typing import ClassVar, Optional, Union

from bs4 import BeautifulSoup

from app.bills.base import Adapter, Bill, BillError, Challenge, Charge, HistoryRow
from app.bills.http import PolicyClient

HOST = "bill.pitc.com.pk"

MONTHS = {m: i for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split(), start=1)}

# (label on the bill) -> (stable key, kind). Anything not listed is kept under its own label.
CHARGE_KEYS = {
    "total electricity charges": ("electricity", "charge"),
    "subsidies": ("subsidies", "credit"),
    "net electricity charges": ("net_electricity", "total"),
    "taxes": ("taxes", "tax"),
    "current bill": ("current_bill", "total"),
    "arrears": ("arrears", "arrears"),
    "installment": ("installment", "arrears"),
    "adjustments": ("adjustments", "adjustment"),
    "w.e credit": ("we_credit", "credit"),
    "lock open credit": ("lock_open_credit", "credit"),
    "total fpa": ("fpa", "charge"),
    "grand total": ("grand_total", "total"),
}


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node is not None else ""


def _number(value: str) -> Optional[float]:
    match = re.search(r"-?\d[\d,]*\.?\d*", value or "")
    return float(match.group().replace(",", "")) if match else None


def _day(value: str) -> Optional[date]:
    """'12 NOV 26' or '26-NOV-26' -> date"""
    match = re.search(r"(\d{1,2})[\s-]+([A-Za-z]{3})[A-Za-z]*[\s-]+(\d{2,4})", value or "")
    if not match or match.group(2).upper() not in MONTHS:
        return None
    year = int(match.group(3))
    return date(year + 2000 if year < 100 else year, MONTHS[match.group(2).upper()], int(match.group(1)))


def _month(value: str) -> Optional[date]:
    """'NOV 26' or 'Nov25' -> first day of that month"""
    match = re.search(r"([A-Za-z]{3})[A-Za-z]*\s*(\d{2,4})", value or "")
    if not match or match.group(1).upper() not in MONTHS:
        return None
    year = int(match.group(2))
    return date(year + 2000 if year < 100 else year, MONTHS[match.group(1).upper()], 1)


def _details(soup: BeautifulSoup) -> dict:
    """The page carries a hidden plain-text breakdown (energy, taxes, FPA); turn it into a dict."""
    box = soup.find("textarea", id=re.compile("charges_qr_text"))
    if box is None:
        return {}
    sections: dict[str, dict] = {}
    current = None
    for raw in box.get_text().splitlines():
        line = raw.strip()
        heading = re.match(r"-+\s*(.+?)\s*(?:=\s*([\d.,]+))?\s*-+$", line)
        if heading:
            current = sections.setdefault(heading.group(1).strip().lower(), {})
            if heading.group(2):
                current["total"] = _number(heading.group(2))
        elif current is not None and ":" in line:
            key, _, value = line.partition(":")
            value = value.strip()
            # Amounts become numbers; identifiers (long or zero-padded digit strings) stay text.
            is_amount = re.fullmatch(r"-?[\d,]*\.?\d+", value) and not (len(value) > 9 or (len(value) > 1 and value.startswith("0") and "." not in value))
            current[key.strip().lower()] = _number(value) if is_amount else value
        elif current is not None and line:
            current.setdefault("lines", []).append(line)
    return sections


def parse_pitc_bill(html: str, company: str, consumer_number: str) -> Bill:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    # Labelled boxes ("REFERENCE NO" followed by its value), including the meter block.
    fields: dict[str, str] = {}
    for row in soup.select(".label-row"):
        label = _text(row.select_one(".en-lbl")).lower()
        value = row.find_next_sibling(class_="val-space")
        if label and label not in fields:
            fields[label] = _text(value)

    # Right-hand panel: bill month, reading/issue/due dates.
    panel: dict[str, str] = {}
    for row in soup.select(".right-panel-label-row"):
        value = row.find_next_sibling(class_="right-main-val")
        panel[_text(row.select_one(".right-panel-en")).lower().lstrip("⚠ ").strip()] = _text(value)
    for cell in soup.select(".right-grid-cell"):
        label = _text(cell.select_one(".right-panel-en")).lower()
        panel[label] = _text(cell.select_one(".right-panel-date-val"))

    bill_month = _month(panel.get("bill month", ""))
    if bill_month is None:
        raise BillError("This does not look like a bill page (no bill month found)")

    charges = []
    for row in soup.select(".charges-bd-row"):
        label = _text(row.select_one(".charges-bd-en"))
        amount = _number(_text(row.select_one(".charges-bd-val")))
        if not label or amount is None:
            continue
        key, kind = CHARGE_KEYS.get(label.lower(), (re.sub(r"\W+", "_", label.lower()).strip("_"), "charge"))
        charges.append(Charge(key=key, label=label, amount=amount, kind=kind))

    reading_date = _day(panel.get("reading date (pro-rata)", "") or panel.get("reading date", ""))
    amount_due = _number(_text(soup.select_one(".payable-card-amount")))
    if amount_due is None:
        raise BillError("Could not find the amount payable on the bill page")

    # Late-payment columns: surcharge, "Till <date>" payable, and the same after that date.
    late = []
    for col in soup.select(".lp-surcharge-data-col"):
        late.append(
            {
                "surcharge": _number(_text(col.select_one(".lp-surcharge-top-val"))),
                "period": _text(col.select_one(".lp-surcharge-period")),
                "payable": _number(_text(col.select_one(".lp-surcharge-bottom-val"))),
            }
        )

    history = []
    for row in soup.select(".history-row"):
        cells = [_text(c) for c in row.select(".history-cell")]
        month = _month(cells[0]) if cells else None
        if month is None or len(cells) < 5:
            continue
        history.append(HistoryRow(month=month, units=_number(cells[2]), billed=_number(cells[3]), paid=_number(cells[4])))
    history.sort(key=lambda r: r.month)

    # Paid when the portal's history already shows a payment for this bill's month.
    paid = None
    for row in history:
        if row.month == bill_month and row.paid is not None and row.billed is not None and row.paid >= row.billed > 0:
            paid = True

    return Bill(
        company=company,
        consumer_number=consumer_number,
        bill_month=bill_month,
        due_date=_day(panel.get("due date", "")),
        amount_due=amount_due,
        amount_after_due=late[-1]["payable"] if late else None,
        units=_number(fields.get("units", "")),
        previous_reading=_number(fields.get("previous reading", "")),
        present_reading=_number(fields.get("present reading", "")),
        issue_date=_day(panel.get("issue date", "")),
        tariff=fields.get("tariff", "") or fields.get("tariff category", ""),
        name_and_address=fields.get("name & address", ""),
        meter_no=fields.get("meter no", ""),
        charges=charges,
        history=history,
        paid=paid,
        extra={
            "reference_no": fields.get("reference no", ""),
            "consumer_id": fields.get("consumer id", ""),
            "category": fields.get("category", ""),
            "status": fields.get("status", ""),
            "tariff_category": fields.get("tariff category", ""),
            "sanctioned_load": fields.get("san load", ""),
            "reading_date": str(reading_date) if reading_date else "",
            "late_payment": late,
            "details": _details(soup),
        },
    )


class PitcAdapter(Adapter):
    """Subclass and set `id`, `name`, `slug` (the path on bill.pitc.com.pk) and the schedule."""

    slug: ClassVar[str] = ""  # "gepcobill"
    category = "electricity"
    input_label = "Reference number"
    input_hint = "14 digits, printed at the top of your bill"
    input_example = "04 12345 1234567"
    help_text = "Use the Reference No., not the Consumer ID. Your bill is fetched from the official PITC portal."
    input_pattern = r"\d{2}\s?\d{5}\s?\d{7}[A-Za-z]?|\d{14}[A-Za-z]?"
    allowed_hosts = (HOST,)
    reports_paid_status = True  # the bill's history shows the payment made for each month

    @property
    def _page(self) -> str:
        return f"https://{HOST}/{self.slug}"

    @staticmethod
    def _is_bill(html: str) -> bool:
        return "BILL CHARGES BREAKDOWN" in html or "charges-bd-row" in html

    def fetch(
        self, http: PolicyClient, consumer_number: str, answer: str = "", state: Optional[dict] = None
    ) -> Union[Bill, Challenge]:
        digits = "".join(consumer_number.split())
        if state:
            return self._submit_captcha(http, consumer_number, digits, answer, state)

        # 1. The portal's own bill address answers a plain POST with the bill.
        direct = http.post(f"{self._page}/general/{digits[:14]}")
        if direct.status_code == 200 and self._is_bill(direct.text):
            return parse_pitc_bill(direct.text, self.id, consumer_number)
        # 2. Otherwise it wants the CAPTCHA form: hand the CAPTCHA to the user.
        return self._challenge(http)

    def _challenge(self, http: PolicyClient) -> Challenge:
        page = http.get(self._page)
        if page.status_code != 200:
            raise BillError(f"The {self.name} portal answered {page.status_code}")
        soup = BeautifulSoup(page.text, "html.parser")
        form = soup.find("form", id="SubmitForm")
        image = soup.find("img", id="captchaImage")
        if form is None or image is None:
            raise BillError(f"The {self.name} portal page looks different than expected")
        hidden = {t["name"]: t.get("value", "") for t in form.find_all("input", type="hidden") if t.get("name")}
        picture = http.get(str(page.url.join(image["src"])))
        if picture.status_code != 200 or not picture.content:
            raise BillError("Could not load the CAPTCHA image")
        return Challenge(
            image=picture.content,
            media_type=picture.headers.get("content-type", "image/jpeg").split(";")[0],
            state={"hidden": hidden, "cookies": http.export_cookies()},
        )

    def _submit_captcha(self, http, consumer_number: str, digits: str, answer: str, state: dict) -> Bill:
        number, suffix = digits[:14], digits[14:].upper()  # a trailing R marks a rural number
        form = dict(state["hidden"])
        form.update(
            {
                "rbSearchByList": "refno",
                "searchTextBox": number,
                "ruCodeTextBox": suffix if suffix in ("R", "U") else "",
                "captchaInput": answer.strip(),
                "btnSearch": "Search",
            }
        )
        response = http.post(self._page, data=form)
        if response.status_code != 200:
            raise BillError(f"The {self.name} portal answered {response.status_code}")
        if not self._is_bill(response.text):
            raise BillError("No bill came back: the code may be wrong or the number not found")
        return parse_pitc_bill(response.text, self.id, consumer_number)
