# Writing a bill adapter

An adapter teaches Notifaybers how to get **one company's bill** (electricity, gas,
water, phone) for a consumer number. You write one Python file. Everything else is
already done for you: the "add a bill" dialog, saving, the daily check, push
notifications, the 12-month chart, the explanation in English / Roman Urdu / Urdu, and
the share image.

Read [CONTRIBUTING.md](../CONTRIBUTING.md) first for the rules. The most important one:
**an adapter never solves, bypasses or works around a CAPTCHA.** If the portal asks for
one, you hand the image to the user and they type it.

## How it fits together

```
user picks a company ──▶ app draws the dialog from your class attributes
user types the number ─▶ app calls  your_adapter.fetch(http, number)
                              │
              returns a Bill ─┴─ or a Challenge (CAPTCHA image)
                   │                      │
            saved, explained,      shown to the user; their answer
            charted, pushed        comes back as  fetch(..., answer, state)
```

- `app/bills/base.py` defines the `Adapter` class, the `Bill` you return and `BillError`.
- `app/bills/http.py` is the only HTTP client you get (see "The HTTP client").
- `app/bills/adapters/` is where your file goes. Every `.py` file in it that does not
  start with `_` is loaded automatically; there is nothing to register.
- `app/bills/adapters/pitc.py` + `gepco.py` are a complete working example.

## Quick start

1. Copy `app/bills/adapters/_template.py` to `app/bills/adapters/<company>.py`.
2. Rename the class and fill in the attributes (next section).
3. Implement `fetch()`.
4. Save one real bill page as `tests/fixtures/<company>_bill.html` (redacted, see
   "Fixtures") and write tests in `tests/test_bills_<company>.py`.
5. Run the tests, then open a pull request.

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Use Python 3.12 (what the Docker image runs). The pinned `sqlmodel` does not load on 3.14.

## The class attributes

```python
class Example(Adapter):
    id = "example"
    name = "Example Gas Company"
    category = "gas"

    input_label = "Consumer number"
    input_hint = "11 digits, printed on your bill"
    input_example = "12345678901"
    input_pattern = r"\d{11}"
    help_text = "You can find it at the top right of the bill."

    allowed_hosts = ("bills.example.com.pk",)

    publish_day = 5
    check_days_before = 2
    reports_paid_status = False
```

| Attribute | What it does |
| --- | --- |
| `id` | Lowercase, unique, never changed later (saved accounts point to it). |
| `name` | What people see, e.g. `"SNGPL (Lahore)"`. |
| `category` | `electricity`, `gas`, `water` or `telecom`. The picker groups by this. |
| `input_label`, `input_hint`, `input_example`, `help_text` | Text for the dialog. Plain text only; the app builds the HTML, so you cannot inject markup. |
| `input_pattern` | The whole number must match it (`re.fullmatch`). The browser checks it too with JavaScript's `RegExp`, so write something valid in **both** Python and JavaScript. Allow spaces if the bill prints them. |
| `allowed_hosts` | Every host you may contact. Requests to anything else fail. |
| `publish_day` | Day of the month the company usually issues bills (`None` if unknown). |
| `check_days_before` | Start checking this many days before `publish_day`. |
| `reports_paid_status` | `True` only if a fetched bill really says whether it has been paid. |

Note: the number you receive in `fetch()` has its spaces already removed.

### Choosing the schedule

The app does **not** fetch every day. From `publish_day - check_days_before` it checks
once each morning (about 8 am) until a bill newer than that window appears, then stops
until next month. It fetches once more the day before the due date. With
`publish_day = None` it checks daily from the 1st until a bill for the month shows up,
so give a real value whenever you know it.

If you only know the publish day from one bill, say so in a comment. A wrong guess
means a late notification, not a wrong bill.

## `fetch()`

```python
def fetch(self, http, consumer_number, answer="", state=None) -> Bill | Challenge:
```

The app creates a fresh instance for every call, so **keep no state on `self`**. Anything
you need between the two calls goes in the `Challenge`'s `state` dict (cookies, hidden
form fields) and comes back to you.

### A portal with no CAPTCHA

```python
def fetch(self, http, consumer_number, answer="", state=None):
    response = http.get(f"https://bills.example.com.pk/bill?no={consumer_number}")
    if response.status_code == 404:
        raise BillError("No bill found for this number")
    return parse(response.text, consumer_number)
```

### A portal that asks for a code

Call 1 returns a `Challenge`; the app shows the image. Call 2 gets the user's `answer`
and your `state` back.

```python
def fetch(self, http, consumer_number, answer="", state=None):
    if state is None:                                   # first call
        page = http.get(FORM_URL)
        image = http.get(CAPTCHA_URL)
        return Challenge(
            image=image.content,
            media_type="image/png",
            state={"cookies": http.export_cookies(), "token": find_token(page.text)},
        )
    response = http.post(FORM_URL, data={"consumer": consumer_number,
                                         "code": answer, "token": state["token"]})
    if "invalid code" in response.text.lower():
        raise BillError("That code was wrong")
    return parse(response.text, consumer_number)
```

The cookies in `state` are put back on the HTTP client for the second call automatically.

If a portal sometimes asks for a code and sometimes does not, try the plain request
first and only return a `Challenge` when it does (the PITC adapter works this way).

### Errors

Raise `BillError("message")` for anything the user should be told: wrong number, portal
down, wrong code, page layout changed. Write the message for a normal person, in one
sentence. Do not let other exceptions escape if you can name the cause.

## The `Bill` you return

Return `app.bills.base.Bill`. Only some fields are required.

| Field | Notes |
| --- | --- |
| `company` | Your adapter `id`. |
| `consumer_number` | The number you were given. |
| `bill_month` | `date` of the **first day** of the billing month. |
| `due_date` | `date` or `None`. |
| `amount_due` | Rupees payable by the due date. |
| `amount_after_due` | Rupees payable after the due date, or `None`. |
| `units` | Units, cubic metres, etc., or `None`. |
| `previous_reading`, `present_reading` | Meter readings, or `None`. |
| `issue_date` | When the bill was issued. **Please set it**: the scheduler uses it to know a new bill has arrived. |
| `tariff`, `meter_no`, `name_and_address` | Strings as printed. |
| `charges` | The breakdown, a list of `Charge` (below). |
| `history` | A list of `HistoryRow(month, units, billed, paid)`, oldest first. |
| `paid` | `True`/`False` only when the bill itself tells you; otherwise `None`. |
| `extra` | Anything company-specific worth keeping (a dict, must be JSON-friendly). |

Use plain numbers (`float`), never strings like `"Rs. 3,831"`. Parse commas and currency
text yourself. Dates are `datetime.date`.

### Charges

Each line of the breakdown is `Charge(key, label, amount, kind)`:

- `label` is the text as printed on the bill.
- `key` is a stable id such as `electricity`, `subsidies`, `taxes`, `fpa`, `current_bill`,
  `grand_total`. The explanation text looks for these keys, so reuse them where they fit.
- `kind` is one of `charge`, `tax`, `credit`, `arrears`, `adjustment`, `total`.
  A `credit` is shown as a minus.
- Keep amounts positive as printed. The app does the signs.

### Paid status

Only set `paid` when you are sure. A common pattern is a history table with a payment
column: if the row for this bill's month shows a payment at least equal to the bill, it
is paid; otherwise leave it `None`, not `False`. "Unknown" is honest; a wrong "unpaid"
sends a wrong reminder.

## Parsing

`beautifulsoup4` is installed. Prefer reading by meaning (a label and its value, a CSS
class) over positions, and fail clearly when the page changes:

```python
soup = BeautifulSoup(html, "html.parser")
month = soup.select_one(".bill-month")
if month is None:
    raise BillError("The portal page looks different than expected")
```

See `parse_pitc_bill()` in `pitc.py` for a full example. If the page has a hidden
machine-readable block (the PITC page has one), prefer that.

## The HTTP client

The `http` argument is a `PolicyClient`:

- `http.get(url, **kw)` and `http.post(url, **kw)` return an `httpx.Response`.
- **https only**, and only for hosts in `allowed_hosts`. Anything else raises `BillError`.
- Redirects are followed by hand and **every hop** is checked against `allowed_hosts`.
- 20 second timeout and a 2 MB response limit.
- `http.export_cookies()` gives you the session cookies to store in a `Challenge`.

Do not import `requests`, `httpx` or `socket` in an adapter, and do not read files,
environment variables or the database. You receive a number and a client, nothing else.
Be gentle with the portal: one request per step, no loops, no parallel calls.

## Fixtures and tests

Tests run on a saved page, never on the live site.

1. Open your own bill on the portal (solve the CAPTCHA yourself if there is one) and
   save the page as HTML.
2. **Redact it.** Replace your name, address, consumer and reference numbers, meter
   number, feeder, phone, and any QR or barcode payload with fake values. Remove
   `<script>` tags and images. Then search the file for every real digit string and name
   you can think of before you commit it.
3. Save it as `tests/fixtures/<company>_bill.html`.

Then test what matters. This is the pattern used by `tests/test_bills_pitc.py`:

```python
FIXTURE = (Path(__file__).parent / "fixtures" / "example_bill.html").read_text(encoding="utf-8")

def test_parses_the_headline_numbers():
    bill = parse(FIXTURE, "example", "12345678901")
    assert bill.amount_due == 1234
    assert bill.due_date == date(2026, 11, 23)

def test_breakdown_adds_up():
    ...   # the charges should sum to the total on the bill

def test_fetch_without_the_network():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=FIXTURE)
    client = PolicyClient(Example, transport=httpx.MockTransport(handler))
    bill = Example().fetch(client, "12345678901")
    assert isinstance(bill, Bill)
```

Also test the failure paths: a wrong number, a page that is not a bill, and (if your
portal has one) a wrong CAPTCHA answer.

## Adding a PITC company

LESCO, GEPCO, FESCO, IESCO, MEPCO, PESCO, HESCO, QESCO, SEPCO and TESCO share one portal
and one bill layout, so a new one is a few lines:

```python
from app.bills.adapters.pitc import PitcAdapter

class Lesco(PitcAdapter):
    id = "lesco"
    name = "LESCO (Lahore)"
    slug = "lescobill"       # the path on bill.pitc.com.pk
    publish_day = 6          # your own observation, say so in a comment
    check_days_before = 3
```

Only GEPCO has been checked against a real bill. For another company you need **a real
redacted bill page from that company** as a fixture, because the portal may differ in
small ways. A pull request without one cannot be reviewed.

## Pull request checklist

- [ ] One new file in `app/bills/adapters/`, plus its fixture and tests.
- [ ] `id` is unique and lowercase.
- [ ] `allowed_hosts` lists exactly the hosts you contact.
- [ ] No CAPTCHA solving, OCR or workarounds.
- [ ] `issue_date` is set, and `paid` is `None` unless the bill really says.
- [ ] The fixture has no personal data (names, numbers, addresses, QR payloads).
- [ ] `pytest` passes on Python 3.12.
- [ ] `publish_day` comes with a comment saying how you know it.
