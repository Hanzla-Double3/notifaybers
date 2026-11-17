"""Plain-language text for a bill, in English, Roman Urdu and Urdu script.

Everything here works on the bill as a dict (what `service.bill_to_dict` produces and the
database stores), so it can run on any saved bill without an adapter.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

LANGS = ("en", "ur_roman", "ur")
DEFAULT_LANG = "ur_roman"

MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "ur_roman": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "ur": ["جنوری", "فروری", "مارچ", "اپریل", "مئی", "جون", "جولائی", "اگست", "ستمبر", "اکتوبر", "نومبر", "دسمبر"],
}


def rs(value: Optional[float], lang: str = "en") -> str:
    if value is None:
        return "-"
    number = f"{value:,.0f}"
    return f"{number} روپے" if lang == "ur" else f"Rs {number}"


def _iso(value) -> Optional[date]:
    if not value:
        return None
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def day(value, lang: str) -> str:
    d = _iso(value)
    if d is None:
        return "-"
    return f"{d.day} {MONTHS[lang][d.month - 1]}"


def month_year(value, lang: str) -> str:
    d = _iso(value if len(str(value)) > 7 else f"{value}-01")
    return f"{MONTHS[lang][d.month - 1]} {d.year}"


def _charge(bill: dict, key: str) -> Optional[float]:
    for c in bill.get("charges", []):
        if c["key"] == key:
            return c["amount"]
    return None


def _previous(bill: dict) -> Optional[dict]:
    """The history row just before this bill's month (that month's units and amount)."""
    this = str(bill["bill_month"])[:7]
    earlier = [h for h in bill.get("history", []) if str(h["month"])[:7] < this]
    return max(earlier, key=lambda h: str(h["month"])) if earlier else None


def explain(bill: dict, lang: str = DEFAULT_LANG) -> list[str]:
    """Short paragraphs that say what the bill is made of and how it compares with last month."""
    lang = lang if lang in LANGS else DEFAULT_LANG
    month = month_year(str(bill["bill_month"])[:7], lang)
    due, after = bill.get("due_date"), bill.get("amount_after_due")
    units = bill.get("units")
    total = bill["amount_due"]
    out: list[str] = []

    # 1. headline
    if lang == "en":
        line = f"Your {month} bill is {rs(total)}."
        if due:
            line += f" Pay by {day(due, lang)}"
            line += f"; after that it becomes {rs(after)}." if after else "."
    elif lang == "ur_roman":
        line = f"Aap ka {month} ka bill {rs(total)} hai."
        if due:
            line += f" Akhri tareekh {day(due, lang)} hai"
            line += f", us ke baad {rs(after)} ho jayega." if after else "."
    else:
        line = f"آپ کا {month} کا بل {rs(total, lang)} ہے۔"
        if due:
            line += f" آخری تاریخ {day(due, lang)} ہے"
            line += f"، اس کے بعد {rs(after, lang)} ہو جائے گا۔" if after else "۔"
    out.append(line)

    # 2. units
    if units is not None:
        a, b = bill.get("previous_reading"), bill.get("present_reading")
        readings = f" ({a:g} → {b:g})" if a is not None and b is not None else ""
        out.append(
            {
                "en": f"You used {units:g} units{readings}.",
                "ur_roman": f"Aap ne {units:g} units istemal kiye{readings}.",
                "ur": f"آپ نے {units:g} یونٹ استعمال کیے{readings}۔",
            }[lang]
        )

    # 3. what it is made of
    elec, subs = _charge(bill, "electricity"), _charge(bill, "subsidies")
    taxes, fpa = _charge(bill, "taxes"), _charge(bill, "fpa")
    parts = []
    if elec is not None:
        parts.append(
            {
                "en": f"electricity {rs(elec)}" + (f" minus a government subsidy of {rs(subs)}" if subs else ""),
                "ur_roman": f"bijli ke charges {rs(elec)}" + (f" (hukumat ki subsidy {rs(subs)} minus ho kar)" if subs else ""),
                "ur": f"بجلی کے چارجز {rs(elec, lang)}" + (f" (حکومت کی سبسڈی {rs(subs, lang)} منفی ہو کر)" if subs else ""),
            }[lang]
        )
    if taxes:
        parts.append({"en": f"taxes {rs(taxes)}", "ur_roman": f"taxes {rs(taxes)}", "ur": f"ٹیکس {rs(taxes, lang)}"}[lang])
    if fpa:
        parts.append(
            {
                "en": f"fuel price adjustment {rs(fpa)}",
                "ur_roman": f"fuel price adjustment (FPA) {rs(fpa)}",
                "ur": f"فیول پرائس ایڈجسٹمنٹ {rs(fpa, lang)}",
            }[lang]
        )
    if parts:
        joiner = {"en": "The bill is made of: ", "ur_roman": "Bill is tarah bana hai: ", "ur": "بل یوں بنا ہے: "}[lang]
        out.append(joiner + ("; " if lang == "en" else "، " if lang == "ur" else "; ").join(parts) + ("۔" if lang == "ur" else "."))
    if fpa:
        out.append(
            {
                "en": "FPA is an extra charge for fuel costs that were higher than planned in an earlier month. It is added on top of your usage charges.",
                "ur_roman": "FPA pichle mahino mein fuel ki qeemat andaze se zyada hone ki wajah se lagne wala izafi charge hai. Ye aap ke istemal ke charges ke ilawa hota hai.",
                "ur": "ایف پی اے پچھلے مہینوں میں ایندھن کی قیمت اندازے سے زیادہ ہونے کی وجہ سے لگنے والا اضافی چارج ہے۔ یہ آپ کے استعمال کے چارجز کے علاوہ ہوتا ہے۔",
            }[lang]
        )

    # 4. cost per unit
    if units:
        per = total / units
        out.append(
            {
                "en": f"That works out to about {rs(per)} for every unit.",
                "ur_roman": f"Yani taqreeban {rs(per)} har unit par.",
                "ur": f"یعنی تقریباً {rs(per, lang)} فی یونٹ۔",
            }[lang]
        )

    # 5. arrears
    arrears = _charge(bill, "arrears")
    if arrears:
        out.append(
            {
                "en": f"This bill includes {rs(arrears)} still unpaid from before.",
                "ur_roman": f"Is bill mein pichla {rs(arrears)} bhi shamil hai jo ada nahi hua.",
                "ur": f"اس بل میں پچھلا {rs(arrears, lang)} بھی شامل ہے جو ادا نہیں ہوا۔",
            }[lang]
        )

    # 6. compared with last month
    prev = _previous(bill)
    if prev and prev.get("units") and units is not None:
        diff = units - prev["units"]
        pct = abs(diff) / prev["units"] * 100
        if abs(pct) >= 10:
            more = diff > 0
            out.append(
                {
                    "en": f"That is {pct:.0f}% {'more' if more else 'less'} than last month ({prev['units']:g} units).",
                    "ur_roman": f"Ye pichle mahine ({prev['units']:g} units) se {pct:.0f}% {'zyada' if more else 'kam'} hai.",
                    "ur": f"یہ پچھلے مہینے ({prev['units']:g} یونٹ) سے {pct:.0f}% {'زیادہ' if more else 'کم'} ہے۔",
                }[lang]
            )
    return out


# ---- push notification texts ----------------------------------------------------------


def notice_new(bill: dict, name: str, lang: str = DEFAULT_LANG) -> tuple[str, str]:
    lang = lang if lang in LANGS else DEFAULT_LANG
    total, due, units = rs(bill["amount_due"], lang), day(bill.get("due_date"), lang), bill.get("units")
    u = f"{units:g}" if units is not None else "-"
    if lang == "en":
        return f"New {name} bill: {total}", f"{u} units. Pay by {due}."
    if lang == "ur_roman":
        return f"Naya {name} bill aa gaya: {total}", f"{u} units. Akhri tareekh {due}."
    return f"نیا {name} بل آ گیا: {total}", f"{u} یونٹ۔ آخری تاریخ {due}۔"


def notice_due(bill: dict, name: str, paid: Optional[bool], lang: str = DEFAULT_LANG) -> tuple[str, str]:
    lang = lang if lang in LANGS else DEFAULT_LANG
    total = rs(bill["amount_due"], lang)
    late = rs(bill.get("amount_after_due"), lang) if bill.get("amount_after_due") else None
    if lang == "en":
        body = "Not paid yet." if paid is False else "Ignore this if you have already paid."
        if late:
            body += f" After the due date it is {late}."
        return f"{name} bill is due tomorrow: {total}", body
    if lang == "ur_roman":
        body = "Abhi tak ada nahi hua." if paid is False else "Agar ada kar chuke hain to is ko nazar andaz karein."
        if late:
            body += f" Akhri tareekh ke baad {late} ho jayega."
        return f"{name} bill kal due hai: {total}", body
    body = "ابھی تک ادا نہیں ہوا۔" if paid is False else "اگر ادا کر چکے ہیں تو اسے نظر انداز کریں۔"
    if late:
        body += f" آخری تاریخ کے بعد {late} ہو جائے گا۔"
    return f"{name} کا بل کل واجب الادا ہے: {total}", body


def notice_captcha(name: str, lang: str = DEFAULT_LANG) -> tuple[str, str]:
    return {
        "en": (f"{name} bill needs you", "The portal needs a code typed in. Open Bills and tap Refresh."),
        "ur_roman": (f"{name} bill ke liye aap chahiye", "Portal code mang raha hai. Bills kholein aur Refresh dabayein."),
        "ur": (f"{name} بل کے لیے آپ کی ضرورت ہے", "پورٹل کوڈ مانگ رہا ہے۔ بلز کھولیں اور ریفریش دبائیں۔"),
    }[lang if lang in LANGS else DEFAULT_LANG]


def notice_failure(name: str, lang: str = DEFAULT_LANG) -> tuple[str, str]:
    return {
        "en": (f"Can't check {name} bill", "The last 3 daily checks failed. Open Bills to see why."),
        "ur_roman": (f"{name} bill check nahi ho raha", "Pichle 3 din ke checks nakam rahe. Wajah ke liye Bills kholein."),
        "ur": (f"{name} بل چیک نہیں ہو رہا", "پچھلے 3 دن کے چیک ناکام رہے۔ وجہ کے لیے بلز کھولیں۔"),
    }[lang if lang in LANGS else DEFAULT_LANG]
