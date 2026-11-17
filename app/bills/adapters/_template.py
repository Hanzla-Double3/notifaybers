"""Copy this file to `<company>.py`, rename the class and fill in the blanks.

Files starting with an underscore are ignored, so this template is never loaded.
Read docs/ADAPTERS.md and CONTRIBUTING.md first, especially the rule about CAPTCHAs.
"""

from typing import Optional, Union

from app.bills.base import Adapter, Bill, BillError, Challenge, Charge, HistoryRow  # noqa: F401
from app.bills.http import PolicyClient


class Example(Adapter):
    id = "example"  # lowercase, unique
    name = "Example Gas Company"
    category = "gas"  # electricity | gas | water | telecom

    input_label = "Consumer number"
    input_hint = "11 digits, printed on your bill"
    input_pattern = r"\d{11}"  # the whole number must match this
    input_example = "12345678901"  # shown as the placeholder
    help_text = "Where to find the number on the bill."  # one or two plain sentences

    allowed_hosts = ("bills.example.com.pk",)  # the only hosts you may contact

    publish_day = 5  # the day of the month bills usually appear (None if unknown)
    check_days_before = 2  # start looking this many days earlier
    reports_paid_status = False  # True only if a fetched bill really says whether it is paid

    def fetch(
        self, http: PolicyClient, consumer_number: str, answer: str = "", state: Optional[dict] = None
    ) -> Union[Bill, Challenge]:
        # 1. If the portal needs the user to type something (a CAPTCHA), return a Challenge
        #    with the image. The app shows it and calls fetch() again with `answer` and `state`.
        #    Never read or skip the CAPTCHA yourself.
        # 2. Otherwise request the page, parse it and return a Bill.
        # Raise BillError("a message the user can read") for anything that goes wrong.
        raise BillError("Not implemented")
