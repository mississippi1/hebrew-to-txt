#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mcc_reshet_scraper.py
=====================

Scrapes the "מועדון חבר" (Hever club) business directory at
https://www.mcc.co.il/st_reshet_public.aspx and produces a list of the
places you can order from, grouped by category.

The page is a classic ASP.NET WebForms page: it keeps state in the hidden
__VIEWSTATE / __EVENTVALIDATION fields and re-posts the whole form when you
pick a category. This script does NOT hardcode the fragile auto-generated
field names. Instead it:

  1. GETs the page once.
  2. Reads the *actual* <select> elements to discover the category dropdown
     and its options at runtime.
  3. For every category, re-POSTs the form (carrying the hidden state) and
     parses the returned business list.
  4. Writes the result grouped by category to a .txt file (and a .csv).

Because the field names are discovered dynamically, the script keeps working
even if the site tweaks its control IDs.

Usage
-----
    pip install requests beautifulsoup4 lxml
    python mcc_reshet_scraper.py                 # scrape everything -> restaurants_by_category.txt
    python mcc_reshet_scraper.py --debug         # print the form fields it discovered
    python mcc_reshet_scraper.py --out mylist.txt

Note: run this from a machine that can reach www.mcc.co.il. In some sandboxed
/ corporate-proxied environments the host is blocked at the network layer.
"""

import argparse
import csv
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit(
        "Missing dependencies. Run:\n"
        "    pip install requests beautifulsoup4 lxml"
    )

BASE_URL = "https://www.mcc.co.il/st_reshet_public.aspx"

# Hebrew hints used to recognise the relevant dropdowns / buttons.
CATEGORY_HINTS = ("קטגור", "תחום", "ענף", "סוג", "category", "cat")
AREA_HINTS = ("אזור", "עיר", "מחוז", "area", "city")
FILTER_HINTS = ("סנן", "חפש", "הצג", "filter", "search")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
}


@dataclass
class Business:
    name: str
    category: str
    discount: str = ""
    detail_url: str = ""


@dataclass
class SelectField:
    """A discovered <select> element."""
    name: str
    options: List[Tuple[str, str]] = field(default_factory=list)  # (value, label)


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def get_hidden_fields(soup: BeautifulSoup) -> Dict[str, str]:
    """Collect all hidden <input> fields (VIEWSTATE, EVENTVALIDATION, ...)."""
    fields: Dict[str, str] = {}
    for inp in soup.select("input[type=hidden]"):
        name = inp.get("name")
        if name:
            fields[name] = inp.get("value", "")
    # Also carry submit/text inputs with a value so the form round-trips.
    for inp in soup.find_all("input"):
        name = inp.get("name")
        itype = (inp.get("type") or "text").lower()
        if name and itype in ("text", "radio", "checkbox") and name not in fields:
            if itype in ("radio", "checkbox") and not inp.has_attr("checked"):
                continue
            fields[name] = inp.get("value", "")
    return fields


def discover_selects(soup: BeautifulSoup) -> List[SelectField]:
    result = []
    for sel in soup.find_all("select"):
        name = sel.get("name")
        if not name:
            continue
        opts = []
        for opt in sel.find_all("option"):
            val = opt.get("value", opt.get_text(strip=True))
            label = opt.get_text(strip=True)
            opts.append((val, label))
        result.append(SelectField(name=name, options=opts))
    return result


def _score(field_name: str, options: List[Tuple[str, str]], hints) -> int:
    blob = (field_name + " " + " ".join(l for _, l in options)).lower()
    return sum(blob.count(h.lower()) for h in hints)


def pick_select(selects: List[SelectField], hints) -> Optional[SelectField]:
    """Choose the <select> that best matches the given hints, with >1 real option."""
    best, best_score = None, 0
    for s in selects:
        real_opts = [o for o in s.options if o[0] and o[0] not in ("0", "-1", "")]
        if len(real_opts) < 2:
            continue
        sc = _score(s.name, s.options, hints)
        if sc > best_score:
            best, best_score = s, sc
    if best is None:  # fall back to the select with the most options
        candidates = [s for s in selects if len(s.options) > 2]
        if candidates:
            best = max(candidates, key=lambda s: len(s.options))
    return best


def find_filter_button(soup: BeautifulSoup) -> Optional[Tuple[str, str]]:
    """Return (name, value) of a submit/button that triggers the filter."""
    for inp in soup.find_all(["input", "button"]):
        name = inp.get("name")
        if not name:
            continue
        label = (inp.get("value") or inp.get_text(strip=True) or "").lower()
        if any(h in label for h in FILTER_HINTS):
            return name, inp.get("value", "")
    return None


def parse_businesses(soup: BeautifulSoup, category: str) -> List[Business]:
    """
    Extract businesses from a results page. The directory links each business
    to a detail page (st_reshet_out&p1=<id>), so we anchor on those links and
    grab nearby discount text.
    """
    results: List[Business] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "st_reshet_out" not in href and "reshet_out" not in href:
            continue
        name = a.get_text(strip=True)
        if not name:
            continue
        key = (name, href)
        if key in seen:
            continue
        seen.add(key)

        # Look for a discount figure ("8% הנחה", "5% החזר") near the link.
        discount = ""
        container = a.find_parent(["li", "tr", "div"]) or a.parent
        if container:
            m = re.search(r"(\d{1,2}%[^,\n<]{0,25})", container.get_text(" ", strip=True))
            if m:
                discount = m.group(1).strip()

        url = href
        if url.startswith("/"):
            url = "https://www.mcc.co.il" + url
        elif not url.startswith("http"):
            url = "https://www.mcc.co.il/" + url.lstrip("./")

        results.append(Business(name=name, category=category,
                                discount=discount, detail_url=url))
    return results


def find_next_page(soup: BeautifulSoup) -> Optional[Tuple[str, str]]:
    """Find a pagination postback target ('הבא' / '>' / numeric next)."""
    for a in soup.find_all("a", href=True):
        txt = a.get_text(strip=True)
        if txt in ("הבא", "»", ">", "הבא >", "Next"):
            m = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", a["href"])
            if m:
                return m.group(1), m.group(2)
    return None


def scrape(debug: bool = False, delay: float = 1.0) -> List[Business]:
    session = make_session()
    resp = session.get(BASE_URL, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")

    selects = discover_selects(soup)
    category_sel = pick_select(selects, CATEGORY_HINTS)
    filter_btn = find_filter_button(soup)

    if debug:
        print("== Discovered <select> fields ==")
        for s in selects:
            print(f"  {s.name}: {len(s.options)} options; "
                  f"sample={[l for _, l in s.options[:4]]}")
        print(f"== Chosen category select: "
              f"{category_sel.name if category_sel else None} ==")
        print(f"== Filter button: {filter_btn} ==")

    if not category_sel:
        raise RuntimeError(
            "Could not locate the category dropdown. Re-run with --debug and "
            "adjust CATEGORY_HINTS / pick_select() to match the page."
        )

    categories = [(v, l) for v, l in category_sel.options
                  if v and v not in ("0", "-1", "") and l]

    all_businesses: List[Business] = []
    for value, label in categories:
        print(f"[+] Category: {label} ({value})", file=sys.stderr)
        hidden = get_hidden_fields(soup)
        data = dict(hidden)
        data[category_sel.name] = value
        if filter_btn:
            data[filter_btn[0]] = filter_btn[1] or "1"
        else:
            # No explicit button -> assume the dropdown auto-posts back.
            data["__EVENTTARGET"] = category_sel.name
            data["__EVENTARGUMENT"] = ""

        try:
            r = session.post(BASE_URL, data=data, timeout=30)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
        except requests.RequestException as e:
            print(f"    ! request failed: {e}", file=sys.stderr)
            continue

        page = BeautifulSoup(r.text, "lxml")
        found = parse_businesses(page, label)

        # Follow pagination within the category.
        guard = 0
        while guard < 50:
            nxt = find_next_page(page)
            if not nxt:
                break
            guard += 1
            hidden = get_hidden_fields(page)
            data = dict(hidden)
            data[category_sel.name] = value
            data["__EVENTTARGET"] = nxt[0]
            data["__EVENTARGUMENT"] = nxt[1]
            try:
                r = session.post(BASE_URL, data=data, timeout=30)
                r.raise_for_status()
                r.encoding = r.apparent_encoding or "utf-8"
            except requests.RequestException:
                break
            page = BeautifulSoup(r.text, "lxml")
            more = parse_businesses(page, label)
            if not more:
                break
            found.extend(more)
            time.sleep(delay)

        print(f"    -> {len(found)} businesses", file=sys.stderr)
        all_businesses.extend(found)
        time.sleep(delay)

    return all_businesses


def dedupe(businesses: List[Business]) -> List[Business]:
    seen, out = set(), []
    for b in businesses:
        key = (b.category, b.name)
        if key in seen:
            continue
        seen.add(key)
        out.append(b)
    return out


def write_txt(businesses: List[Business], path: str) -> None:
    by_cat: Dict[str, List[Business]] = {}
    for b in businesses:
        by_cat.setdefault(b.category, []).append(b)

    with open(path, "w", encoding="utf-8") as f:
        f.write("רשימת בתי עסק - מועדון חבר (לפי קטגוריה)\n")
        f.write("=" * 50 + "\n\n")
        for cat in sorted(by_cat):
            items = sorted(by_cat[cat], key=lambda b: b.name)
            f.write(f"## {cat}  ({len(items)})\n")
            for b in items:
                line = f"  - {b.name}"
                if b.discount:
                    line += f"  [{b.discount}]"
                f.write(line + "\n")
            f.write("\n")
    print(f"[✓] Wrote {len(businesses)} businesses to {path}")


def write_csv(businesses: List[Business], path: str) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["category", "name", "discount", "detail_url"])
        for b in businesses:
            w.writerow([b.category, b.name, b.discount, b.detail_url])
    print(f"[✓] Wrote CSV to {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="restaurants_by_category.txt",
                    help="output .txt path (default: restaurants_by_category.txt)")
    ap.add_argument("--csv", default="restaurants_by_category.csv",
                    help="output .csv path")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="polite delay (seconds) between requests")
    ap.add_argument("--debug", action="store_true",
                    help="print the form fields the scraper discovered")
    args = ap.parse_args()

    businesses = dedupe(scrape(debug=args.debug, delay=args.delay))
    if not businesses:
        print("No businesses parsed. Re-run with --debug to inspect the form; "
              "the results-list selector in parse_businesses() may need tuning.",
              file=sys.stderr)
        sys.exit(2)

    write_txt(businesses, args.out)
    write_csv(businesses, args.csv)


if __name__ == "__main__":
    main()
