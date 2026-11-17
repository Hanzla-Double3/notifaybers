from app.bills.adapters.pitc import PitcAdapter


class Gepco(PitcAdapter):
    id = "gepco"
    name = "GEPCO (Gujranwala)"
    slug = "gepcobill"
    # Bills are issued around the 12th and fall due around the 23rd (seen on a Nov 2026 bill);
    # confirm the usual publish day over a few months before relying on it.
    publish_day = 12
    check_days_before = 3
