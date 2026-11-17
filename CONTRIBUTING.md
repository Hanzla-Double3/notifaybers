# Contributing

The easiest way to help is to add a **bill adapter**: a small file that fetches one
company's bill (electricity, gas, water, telecom) and returns it in a common format.
Notifaybers does the rest: reminders, history, the Roman Urdu explanation, sharing.

Companies that share a portal, such as the ten electricity companies on
`bill.pitc.com.pk`, already share one parser (`app/bills/adapters/pitc.py`); each of
them is a few lines (see `gepco.py`). Good first pull requests: LESCO, FESCO, IESCO,
MEPCO, PESCO, HESCO, QESCO, SEPCO, TESCO.

## Add an adapter

The full guide is [docs/ADAPTERS.md](docs/ADAPTERS.md). In short:

1. Copy `app/bills/adapters/_template.py` to `app/bills/adapters/<company>.py`.
2. Fill in the class attributes and `fetch()`. `app/bills/base.py` explains each field. The
   attributes (`input_label`, `input_hint`, `input_example`, `help_text`, ...) are what the app
   draws its "add this bill" dialog from, so you never write HTML.
3. Save one real bill page as `tests/fixtures/<company>_bill.html` and write tests like
   `tests/test_bills_pitc.py`. Tests run on that file, never on the live site.
4. Run `pip install -r requirements-dev.txt && pytest`.
5. Open a pull request.

## Rules

- **No CAPTCHA solving or bypassing, ever.** If the portal asks for a CAPTCHA, return it
  as a `Challenge` and let the user type it. No OCR, no solver services, no tricks to
  skip it. Pull requests that do this are closed.
- **Use only the hosts you declare** in `allowed_hosts`. The provided HTTP client
  enforces it. Do not import `requests`, `httpx` or `socket` yourself.
- **No secrets, no database.** An adapter gets a consumer number and an HTTP client, nothing else.
- **Be gentle with the portal:** one request per bill, no loops, no parallel calls.
- **Redact fixtures.** Before committing a sample bill page, replace the name, address,
  reference or consumer numbers, meter number and any QR or barcode payload with fake
  values. Strip `<script>` tags. Search the file for your own details before you push.
- **Say so when you are unsure.** If you only know a company's publish day from one bill,
  say that in a comment so a later change can correct it.

## Questions

Open an issue. If a portal changes and an adapter breaks, a fix with a new fixture is
the best kind of pull request.
