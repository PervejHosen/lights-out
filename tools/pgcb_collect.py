
"""
PGCB Hourly Generation Data Collector
=======================================

Collects hourly generation data from the PGCB public portal
and saves it into monthly CSV files.

Source:
https://erp.powergrid.gov.bd/web/generations/view_generations

One request per day:
?search=DD-MM-YYYY

Usage:
    python tools/pgcb_collect.py

    # Full history
    python tools/pgcb_collect.py --start 2015-04-01

    # Specific date range
    python tools/pgcb_collect.py --start 2026-08-01 --end 2026-08-31

    # Custom output directory
    python tools/pgcb_collect.py --out ./my_data

Dependencies:
    pip install truststore

SSL:
    Uses Windows native certificate store through truststore.

Features:
    - One request per day
    - Monthly CSV output
    - Skips previously collected dates
    - Four retry attempts
    - SSL certificate verification enabled
    - Configurable request delay
"""

import argparse
import csv
import datetime as dt
import html
import os
import re
import sys
import time
import ssl
import urllib.request

import truststore


# --------------------------------------------------
# SSL CONFIGURATION
# --------------------------------------------------

# Inject Windows native certificate verification
# into Python's default SSL configuration.

truststore.inject_into_ssl()


def create_ssl_context():
    """
    Create SSL context using Windows native
    certificate store.
    """

    return ssl.create_default_context()


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

URL = (
    "https://erp.powergrid.gov.bd/web/generations/"
    "view_generations?search={d}"
)

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_OUT = os.path.join(
    HERE,
    "..",
    "01_data",
    "raw",
    "pgcb_portal_2026"
)

UA = "LightsOut independent research (public data, 1 request per day)"


# --------------------------------------------------
# COLUMN DEFINITIONS
# --------------------------------------------------

COLS17 = [
    "date",
    "time",
    "generation_mw",
    "demand_mw_raw",
    "demand_calc_raw",
    "loadshed_mw_raw",
    "gas",
    "liquid_fuel",
    "coal",
    "hydro",
    "solar",
    "wind",
    "india_bheramara_hvdc",
    "india_tripura",
    "india_adani",
    "nepal",
    "remarks"
]

HEADER = COLS17 + [
    "source_date",
    "fetched_at",
    "cell_count"
]


# --------------------------------------------------
# HTML PARSING
# --------------------------------------------------

def parse_day(page):
    """
    Parse one day's PGCB HTML response.

    Returns:
        List of rows containing cell values.
    """

    a = page.find("<tbody")
    b = page.find("</tbody>", a)

    if a < 0 or b < 0:
        return []

    body = page[a:b]

    # Restore hidden/commented HTML cells.

    body = body.replace("<!--td>", "<td>")
    body = body.replace("</td-->", "</td>")

    body = body.replace("<!--", "")
    body = body.replace("-->", "")

    rows = []

    for tr in re.findall(
        r"<tr[^>]*>(.*?)</tr>",
        body,
        flags=re.S
    ):

        cells = re.findall(
            r"<td[^>]*>(.*?)</td>",
            tr,
            flags=re.S
        )

        cells = [
            html.unescape(
                re.sub(r"<[^>]+>", "", c)
            ).strip()
            for c in cells
        ]

        # Only accept rows containing a valid date.

        if (
            cells
            and re.match(
                r"\d{2}-\d{2}-\d{4}$",
                cells[0]
            )
        ):
            rows.append(cells)

    return rows


# --------------------------------------------------
# FETCH DATA FROM PGCB
# --------------------------------------------------

def fetch(day, tries=4):
    """
    Fetch one day's generation data.

    Uses Windows native SSL certificates.
    Retries failed requests with increasing delays.
    """

    url = URL.format(
        d=day.strftime("%d-%m-%Y")
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA
        }
    )

    context = create_ssl_context()

    for i in range(tries):

        try:

            with urllib.request.urlopen(
                req,
                timeout=40,
                context=context
            ) as response:

                status = response.status

                if status != 200:
                    raise RuntimeError(
                        f"Unexpected HTTP status: {status}"
                    )

                page = response.read().decode(
                    "utf-8",
                    errors="replace"
                )

                return page

        except Exception as e:

            wait = 5 * (i + 1)

            print(
                f"  {day} attempt {i + 1} failed "
                f"({e}); retrying in {wait}s",
                file=sys.stderr
            )

            if i < tries - 1:
                time.sleep(wait)

    raise RuntimeError(
        f"Could not fetch {day} after {tries} attempts"
    )


# --------------------------------------------------
# CHECK SAVED DAYS
# --------------------------------------------------

def saved_days(path):
    """
    Return dates already saved in the monthly CSV.
    """

    if not os.path.exists(path):
        return set()

    with open(
        path,
        newline="",
        encoding="utf-8"
    ) as f:

        return {
            r["source_date"]
            for r in csv.DictReader(f)
            if r.get("source_date")
        }


# --------------------------------------------------
# VALIDATE RESPONSE
# --------------------------------------------------


def validate_page(page, day):
    """
    Validate the PGCB response.

    Do not reject a valid data page just because
    its HTML contains the word 'cloudflare'.
    """

    if not page or not page.strip():
        raise RuntimeError(
            f"Empty HTTP response for {day}"
        )

    lower_page = page.lower()

    # A valid PGCB data response should contain
    # the HTML table body.

    if "<tbody" not in lower_page:

        # Detect actual challenge/error pages.

        error_indicators = [
            "just a moment...",
            "cf-chl-",
            "challenge-platform",
            "verify you are human",
            "attention required",
            "access denied",
            "bad gateway",
            "service unavailable",
            "internal server error",
            "captcha"
        ]

        for indicator in error_indicators:

            if indicator in lower_page:
                raise RuntimeError(
                    f"Blocked or error page detected: {indicator}"
                )

        raise RuntimeError(
            f"No table body found in PGCB response for {day}"
        )


# --------------------------------------------------
# MAIN COLLECTION PROCESS
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Collect hourly PGCB generation data."
    )

    parser.add_argument(
        "--start",
        default="2026-03-01",
        help="First date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--end",
        default=None,
        help="Last date (default: yesterday)"
    )

    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help="Output directory"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Delay between requests (minimum 1.5 seconds)"
    )

    args = parser.parse_args()

    # Date validation.

    start = dt.date.fromisoformat(args.start)

    end = (
        dt.date.fromisoformat(args.end)
        if args.end
        else dt.date.today() - dt.timedelta(days=1)
    )

    if end < start:
        parser.error(
            "End date cannot be earlier than start date."
        )

    if args.delay < 1.5:
        parser.error(
            "Delay must be at least 1.5 seconds."
        )

    # Create output directory.

    os.makedirs(
        args.out,
        exist_ok=True
    )

    # Counters.

    day = start
    done = 0
    skipped = 0
    empty = []
    failed = []

    # --------------------------------------------------
    # COLLECTION START
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("PGCB HOURLY GENERATION DATA COLLECTOR")
    print("=" * 60)

    print(f"Start date : {start}")
    print(f"End date   : {end}")
    print(f"Output     : {os.path.abspath(args.out)}")
    print(f"Delay      : {args.delay} seconds")
    print("SSL        : Windows native certificate store")

    print("=" * 60)

    # --------------------------------------------------
    # DAILY COLLECTION LOOP
    # --------------------------------------------------

    while day <= end:

        path = os.path.join(
            args.out,
            f"pgcb_hourly_{day:%Y-%m}.csv"
        )

        # Skip previously collected dates.

        if day.isoformat() in saved_days(path):

            print(
                f"{day}  SKIPPED (already saved)"
            )

            skipped += 1

            day += dt.timedelta(days=1)

            continue

        try:

            # Fetch HTML.

            page = fetch(day)

            # Validate response.

            validate_page(page, day)

            # Parse rows.

            rows = parse_day(page)

            # Open monthly CSV.

            new = not os.path.exists(path)

            with open(
                path,
                "a",
                newline="",
                encoding="utf-8"
            ) as f:

                writer = csv.writer(f)

                if new:
                    writer.writerow(HEADER)

                now = dt.datetime.now().isoformat(
                    timespec="seconds"
                )

                # Write data rows.

                for r in rows:

                    cells = (
                        r + [""] * (17 - len(r))
                        if len(r) <= 17
                        else r[:17]
                    )

                    writer.writerow(
                        cells + [
                            day.isoformat(),
                            now,
                            len(r)
                        ]
                    )

                # Record valid empty days.

                if not rows:

                    writer.writerow(
                        [""] * 17 + [
                            day.isoformat(),
                            now,
                            0
                        ]
                    )

                    empty.append(
                        day.isoformat()
                    )

            done += 1

            print(
                f"{day}  {len(rows):>2} rows"
            )

        except Exception as e:

            # Do not mark failed dates as collected.
            # They can be retried on the next run.

            failed.append(
                (day.isoformat(), str(e))
            )

            print(
                f"{day}  FAILED: {e}",
                file=sys.stderr
            )

        day += dt.timedelta(days=1)

        # Respect minimum request delay.

        if day <= end:
            time.sleep(args.delay)

    # --------------------------------------------------
    # COLLECTION SUMMARY
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("COLLECTION SUMMARY")
    print("=" * 60)

    print(f"Successfully fetched : {done}")
    print(f"Previously saved     : {skipped}")
    print(f"Empty data days      : {len(empty)}")
    print(f"Failed days          : {len(failed)}")

    print(
        f"\nOutput directory:\n{os.path.abspath(args.out)}"
    )

    if empty:

        print(
            f"\nEmpty days ({len(empty)}):"
        )

        print(
            ", ".join(empty[:20])
            + (" ..." if len(empty) > 20 else "")
        )

    if failed:

        print(
            f"\nFailed days ({len(failed)}):"
        )

        for failed_day, reason in failed[:20]:

            print(
                f"  {failed_day}: {reason}"
            )

        if len(failed) > 20:
            print("  ...")

        print(
            "\nRun the script again to retry failed dates."
        )

    print("\n" + "=" * 60)
    print("COLLECTION FINISHED")
    print("=" * 60)


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    main()
