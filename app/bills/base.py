"""The contract every bill adapter follows, and the one bill format they all return.

An adapter knows how to get ONE company's bill for a consumer number. Everything
else (storage, reminders, the Roman Urdu text, charts) works on the normalized
`Bill` below, so adding a company never touches the rest of the app.

Rules for adapters (see CONTRIBUTING.md):
  * Never solve, bypass or work around a CAPTCHA. If the portal asks for one,
    return it from `fetch()` and let the user answer it.
  * Only talk to the hosts listed in `allowed_hosts`.
  * No access to settings, the database or secrets: you get a consumer number
    and an HTTP client, nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import ClassVar, Optional


class BillError(Exception):
    """Raised for anything the user should be told: wrong number, portal down, bad CAPTCHA."""


@dataclass
class Charge:
    """One line of the breakdown, in rupees. `kind` lets the UI group and explain lines."""

    key: str  # stable id, e.g. "electricity", "subsidies", "taxes", "fpa"
    label: str  # as printed on the bill
    amount: float
    kind: str = "charge"  # charge | tax | credit | arrears | adjustment | total


@dataclass
class HistoryRow:
    month: date  # first day of the billing month
    units: Optional[float]
    billed: Optional[float]
    paid: Optional[float]  # None when the portal does not say


@dataclass
class Bill:
    company: str  # adapter id, e.g. "gepco"
    consumer_number: str  # as the user typed it
    bill_month: date  # first day of the billing month
    due_date: Optional[date]
    amount_due: float  # payable by the due date
    amount_after_due: Optional[float] = None  # late-payment amount, if the bill states one
    units: Optional[float] = None
    previous_reading: Optional[float] = None
    present_reading: Optional[float] = None
    issue_date: Optional[date] = None
    tariff: str = ""
    name_and_address: str = ""  # as printed; the portals do not separate them reliably
    meter_no: str = ""
    charges: list[Charge] = field(default_factory=list)
    history: list[HistoryRow] = field(default_factory=list)
    # True/False when the portal tells us, None when it cannot.
    paid: Optional[bool] = None
    extra: dict = field(default_factory=dict)  # anything company-specific worth keeping


@dataclass
class Challenge:
    """Something the user has to answer before the bill can be fetched (a CAPTCHA).

    `image` is the raw image bytes to show. `state` is whatever the adapter needs
    to carry to the second `fetch()` call (cookies, hidden form fields); it is kept
    on the server and never shown to the user.
    """

    image: bytes
    media_type: str = "image/png"
    prompt: str = "Type the code from the image"
    state: dict = field(default_factory=dict)


class Adapter:
    """Subclass this, fill in the class attributes, implement `fetch`."""

    # --- identity -------------------------------------------------------------
    id: ClassVar[str] = ""  # lowercase, unique: "gepco"
    name: ClassVar[str] = ""  # for people: "GEPCO (Gujranwala)"
    category: ClassVar[str] = "electricity"  # electricity | gas | water | telecom

    # --- what the user must give us ------------------------------------------
    input_label: ClassVar[str] = "Reference number"
    input_hint: ClassVar[str] = ""  # e.g. "14 digits, printed on your bill"
    input_pattern: ClassVar[str] = r".+"  # full-match regex; checked before any request
    input_example: ClassVar[str] = ""  # shown as the placeholder
    help_text: ClassVar[str] = ""  # one or two plain sentences shown in the add dialog

    # --- network policy --------------------------------------------------------
    allowed_hosts: ClassVar[tuple[str, ...]] = ()

    # --- when to look ----------------------------------------------------------
    # Day of the month the company usually publishes, and how many days before that
    # to start checking. The scheduler only fetches when today falls in the window.
    publish_day: ClassVar[Optional[int]] = None
    check_days_before: ClassVar[int] = 2
    # Whether a fetched bill can say if it has been paid.
    reports_paid_status: ClassVar[bool] = False

    def fetch(self, http, consumer_number: str, answer: str = "", state: Optional[dict] = None):
        """Get the bill. Returns a `Bill`, or a `Challenge` when the user must answer something first.

        Call it once. If it returns a Challenge, show it to the user and call it again with
        their `answer` and the Challenge's `state`. An adapter whose portal asks for nothing
        simply always returns a Bill.
        """
        raise NotImplementedError

    @classmethod
    def form_spec(cls) -> dict:
        """What the app needs to draw this company's "add account" dialog.

        Plain data only: the app builds the HTML itself, so an adapter can never inject markup.
        """
        return {
            "id": cls.id,
            "name": cls.name,
            "category": cls.category,
            "label": cls.input_label,
            "hint": cls.input_hint,
            "example": cls.input_example,
            "pattern": cls.input_pattern,
            "help": cls.help_text,
            "reports_paid_status": cls.reports_paid_status,
        }

    @classmethod
    def valid_number(cls, value: str) -> bool:
        import re

        return re.fullmatch(cls.input_pattern, value.strip()) is not None
