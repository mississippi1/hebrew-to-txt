# MCC "חבר" business directory scraper

`mcc_reshet_scraper.py` builds a list of the businesses you can order from on
the מועדון חבר directory (https://www.mcc.co.il/st_reshet_public.aspx),
**grouped by category**, and writes it to a `.txt` (and `.csv`) file.

## Why you have to run it yourself

The site was **blocked at the network layer** in the environment where this
script was written (the egress proxy rejected `www.mcc.co.il` with a 403), so
the live list could not be generated there. Run the script from a machine /
network that can reach the site normally.

## Usage

```bash
pip install requests beautifulsoup4 lxml

python mcc_reshet_scraper.py                 # -> restaurants_by_category.txt + .csv
python mcc_reshet_scraper.py --debug         # print the form fields it discovered
python mcc_reshet_scraper.py --out list.txt --csv list.csv
```

## How it works

The page is ASP.NET WebForms (state carried in `__VIEWSTATE` /
`__EVENTVALIDATION`, re-posts the whole form on filter). The scraper:

1. GETs the page once.
2. Discovers the **category dropdown** and its options *at runtime* by reading
   the actual `<select>` elements — no fragile hardcoded control IDs.
3. For each category, re-POSTs the form (carrying the hidden state) and parses
   the returned business list, anchoring on the `st_reshet_out` detail links
   and grabbing the nearby discount figure (e.g. `8% הנחה`).
4. Follows in-category pagination, de-duplicates, and writes the output.

Because field names are discovered dynamically, it keeps working if the site
tweaks its control IDs.

## If something doesn't parse

Run with `--debug` to see which `<select>` fields and filter button were
found. If the category dropdown isn't detected, adjust `CATEGORY_HINTS`; if the
business list isn't parsed, tune `parse_businesses()` (the site may render
results in a table/grid instead of anchor links).
