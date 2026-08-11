import csv
import os
import re
import time
import xml.etree.ElementTree as ET
from urllib.parse import unquote

from playwright.sync_api import sync_playwright


# ============================================================
# CONFIGURATION
# ============================================================

KML_FILE = "Paddlespots.kml"
OUTPUT_FILE = "paddlespots_coordinates.csv"

# How long to let Google Maps load
GOOGLE_WAIT_SECONDS = 8

# Number of attempts for a Google Place URL
MAX_RETRIES = 3

# Pause after every N Google requests
BREAK_EVERY = 20
BREAK_SECONDS = 20


# ============================================================
# KML HELPERS
# ============================================================

NS = {
    "kml": "http://www.opengis.net/kml/2.2"
}


def get_element_text(parent, tag):

    element = parent.find(tag, NS)

    if element is not None and element.text:
        return element.text.strip()

    return ""


def get_data(placemark, field_name):

    for data in placemark.findall(".//kml:Data", NS):

        if data.get("name") == field_name:

            value = data.find("kml:value", NS)

            if value is not None and value.text:
                return value.text.strip()

    return ""


def clean_google_url(raw_url):

    """
    The KML export sometimes contains URLs represented like:

        [https://www.google.com/maps/place/foo](https://www.google.com/maps/place/foo)

    Extract the actual URL without accidentally truncating names
    containing apostrophes.
    """

    if not raw_url:
        return ""

    url = raw_url.strip()

    # Markdown-style URL:
    #
    # [URL](URL)
    #
    if url.startswith("["):

        closing_bracket = url.find("](")

        if closing_bracket != -1:

            url = url[
                1:closing_bracket
            ]

    # Decode HTML entities that may appear in the export
    url = (
        url
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
    )

    return url.strip()


# ============================================================
# COORDINATE EXTRACTION
# ============================================================

def valid_coordinates(lat, lon):

    return (
        -90 <= lat <= 90
        and
        -180 <= lon <= 180
    )


def coordinates_from_direct_search_url(url):

    """
    Handles:

        https://www.google.com/maps/search/44.6766125,-84.5478871
    """

    if not url:
        return None

    decoded = unquote(url)

    match = re.search(
        r"/maps/search/"
        r"(-?\d+(?:\.\d+)?),"
        r"(-?\d+(?:\.\d+)?)",
        decoded
    )

    if not match:
        return None

    lat = float(match.group(1))
    lon = float(match.group(2))

    if valid_coordinates(lat, lon):

        return lat, lon

    return None


def coordinates_from_canonical_url(url):

    """
    Handles Google's canonical place URL:

        /maps/place/Saco+River+access/@43.8797798,-70.8028945,17z/...

    """

    if not url:
        return None

    decoded = unquote(url)

    match = re.search(
        r"/@"
        r"(-?\d+(?:\.\d+)?),"
        r"(-?\d+(?:\.\d+)?)"
        r"(?:,|/)",
        decoded
    )

    if not match:
        return None

    lat = float(match.group(1))
    lon = float(match.group(2))

    if valid_coordinates(lat, lon):

        return lat, lon

    return None


def coordinates_from_place_data(text):

    """
    Handles:

        !3d43.8797798!4d-70.8028945

    Also handles URL-encoded versions:

        %213d43.8797798%214d-70.8028945
    """

    if not text:
        return None

    decoded = text

    # Google can encode things more than once.
    for _ in range(3):

        new_decoded = unquote(decoded)

        if new_decoded == decoded:
            break

        decoded = new_decoded

    matches = re.findall(
        r"!3d"
        r"(-?\d+(?:\.\d+)?)"
        r"!4d"
        r"(-?\d+(?:\.\d+)?)",
        decoded
    )

    for lat_string, lon_string in matches:

        lat = float(lat_string)
        lon = float(lon_string)

        if valid_coordinates(lat, lon):

            return lat, lon

    return None


# ============================================================
# GOOGLE PLACE PROCESSING
# ============================================================

def extract_google_place_coordinates(page, url, name):

    """
    Open a Google Place URL and attempt several extraction methods.

    Returns:

        (latitude, longitude, method)

    or:

        (None, None, "")
    """

    for attempt in range(1, MAX_RETRIES + 1):

        print(
            f"  Google attempt {attempt}/{MAX_RETRIES}"
        )

        try:

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            # IMPORTANT:
            #
            # Google Maps often changes the URL after the initial
            # page load. We need to give it time to navigate to
            # the canonical /@LAT,LON URL.

            print(
                f"  Waiting {GOOGLE_WAIT_SECONDS}s..."
            )

            page.wait_for_timeout(
                GOOGLE_WAIT_SECONDS * 1000
            )

            canonical_url = page.url

            print(
                "  Canonical URL:"
            )

            print(
                " ",
                canonical_url[:500]
            )

            # ------------------------------------------------
            # METHOD 1:
            # Canonical /@LAT,LON URL
            # ------------------------------------------------

            canonical_coords = (
                coordinates_from_canonical_url(
                    canonical_url
                )
            )

            # ------------------------------------------------
            # Get HTML for verification/fallback
            # ------------------------------------------------

            html = page.content()

            place_coords = (
                coordinates_from_place_data(
                    html
                )
            )

            # ------------------------------------------------
            # If both methods agree, excellent.
            # ------------------------------------------------

            if canonical_coords and place_coords:

                clat, clon = canonical_coords
                plat, plon = place_coords

                print(
                    f"  Canonical coordinates:"
                    f" {clat}, {clon}"
                )

                print(
                    f"  Place-data coordinates:"
                    f" {plat}, {plon}"
                )

                # Treat coordinates as agreeing if they're
                # extremely close. Google sometimes rounds
                # slightly differently.

                if (
                    abs(clat - plat) < 0.00001
                    and
                    abs(clon - plon) < 0.00001
                ):

                    print(
                        "  ✓ Coordinates verified"
                    )

                    return (
                        clat,
                        clon,
                        "Google canonical URL + verified"
                    )

                # If they disagree, prefer the place-specific
                # !3d/!4d coordinates.

                print(
                    "  ⚠ Coordinates differ"
                )

                print(
                    "  Using Google place-data coordinates"
                )

                return (
                    plat,
                    plon,
                    "Google !3d/!4d"
                )

            # ------------------------------------------------
            # METHOD 2:
            # Canonical URL only
            # ------------------------------------------------

            if canonical_coords:

                lat, lon = canonical_coords

                print(
                    f"  ✓ Coordinates from canonical URL:"
                    f" {lat}, {lon}"
                )

                return (
                    lat,
                    lon,
                    "Google canonical URL"
                )

            # ------------------------------------------------
            # METHOD 3:
            # !3d/!4d HTML only
            # ------------------------------------------------

            if place_coords:

                lat, lon = place_coords

                print(
                    f"  ✓ Coordinates from page HTML:"
                    f" {lat}, {lon}"
                )

                return (
                    lat,
                    lon,
                    "Google !3d/!4d"
                )

            print(
                "  ✗ No coordinates found on this attempt"
            )

        except Exception as e:

            print(
                "  ✗ Google error:",
                repr(e)
            )

        # Retry if necessary

        if attempt < MAX_RETRIES:

            wait = 10 * attempt

            print(
                f"  Waiting {wait}s before retry..."
            )

            time.sleep(wait)

    return None, None, ""


# ============================================================
# EXISTING CSV / RESUME SUPPORT
# ============================================================

def load_existing_results():

    results = {}

    if not os.path.exists(OUTPUT_FILE):

        return results

    print()
    print(
        f"Existing output found:"
        f" {OUTPUT_FILE}"
    )

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:

                name = row.get(
                    "Name",
                    ""
                )

                lat = row.get(
                    "Latitude",
                    ""
                )

                lon = row.get(
                    "Longitude",
                    ""
                )

                if (
                    name
                    and
                    lat
                    and
                    lon
                ):

                    # Use name + URL as the key when possible.
                    url = row.get(
                        "Google Maps URL",
                        ""
                    )

                    key = (
                        name,
                        url
                    )

                    results[key] = row

    except Exception as e:

        print(
            "Warning: could not read existing CSV:",
            repr(e)
        )

    print(
        f"Existing successful results:"
        f" {len(results)}"
    )

    return results


def save_results(results):

    fieldnames = [
        "Name",
        "Latitude",
        "Longitude",
        "Method",
        "Google Maps URL"
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(results)


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("GOOGLE MAPS KML COORDINATE EXTRACTOR")
    print("=" * 70)
    print()

    print(
        f"Reading KML: {KML_FILE}"
    )

    tree = ET.parse(KML_FILE)
    root = tree.getroot()

    placemarks = root.findall(
        ".//kml:Placemark",
        NS
    )

    print(
        f"Found {len(placemarks)} placemarks."
    )

    # --------------------------------------------------------
    # Load existing successful results
    # --------------------------------------------------------

    existing = load_existing_results()

    # We'll keep results in the order they appear in the KML.
    results = []

    processed = 0
    successful = 0
    failed = 0
    skipped = 0

    # --------------------------------------------------------
    # Start browser
    # --------------------------------------------------------

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False
        )

        page = browser.new_page()

        # ----------------------------------------------------
        # Process placemarks
        # ----------------------------------------------------

        for i, placemark in enumerate(
            placemarks,
            start=1
        ):

            print()
            print("=" * 70)
            print(
                f"[{i}/{len(placemarks)}]"
            )

            name = get_element_text(
                placemark,
                "kml:name"
            )

            raw_url = get_data(
                placemark,
                "URL"
            )

            url = clean_google_url(
                raw_url
            )

            print(
                f"Name: {name}"
            )

            # ------------------------------------------------
            # Empty placemark
            # ------------------------------------------------

            if not name and not url:

                print(
                    "  Empty placemark - skipping"
                )

                results.append({
                    "Name": "",
                    "Latitude": "",
                    "Longitude": "",
                    "Method": "",
                    "Google Maps URL": ""
                })

                skipped += 1
                continue

            # ------------------------------------------------
            # Check existing successful result
            # ------------------------------------------------

            key = (
                name,
                url
            )

            if key in existing:

                row = existing[key]

                print(
                    "  ✓ Already extracted"
                )

                print(
                    f"  {row['Latitude']},"
                    f" {row['Longitude']}"
                )

                results.append(row)

                successful += 1
                continue

            # ------------------------------------------------
            # Direct coordinate URL
            # ------------------------------------------------

            direct_coords = (
                coordinates_from_direct_search_url(
                    url
                )
            )

            if direct_coords:

                lat, lon = direct_coords

                print(
                    f"  ✓ Direct coordinates:"
                    f" {lat}, {lon}"
                )

                row = {
                    "Name": name,
                    "Latitude": lat,
                    "Longitude": lon,
                    "Method": "Direct KML URL",
                    "Google Maps URL": url
                }

                results.append(row)

                existing[key] = row

                successful += 1

                # Save immediately
                save_results(results)

                continue

            # ------------------------------------------------
            # Google Place URL
            # ------------------------------------------------

            if not url:

                print(
                    "  ✗ No Google Maps URL"
                )

                row = {
                    "Name": name,
                    "Latitude": "",
                    "Longitude": "",
                    "Method": "",
                    "Google Maps URL": ""
                }

                results.append(row)

                failed += 1

                continue

            print(
                "Google Place URL:"
            )

            print(
                " ",
                url
            )

            lat, lon, method = (
                extract_google_place_coordinates(
                    page,
                    url,
                    name
                )
            )

            # ------------------------------------------------
            # Success
            # ------------------------------------------------

            if lat is not None:

                row = {
                    "Name": name,
                    "Latitude": lat,
                    "Longitude": lon,
                    "Method": method,
                    "Google Maps URL": url
                }

                results.append(row)

                existing[key] = row

                successful += 1

                print(
                    "  ✓ SUCCESS"
                )

            # ------------------------------------------------
            # Failure
            # ------------------------------------------------

            else:

                row = {
                    "Name": name,
                    "Latitude": "",
                    "Longitude": "",
                    "Method": "FAILED",
                    "Google Maps URL": url
                }

                results.append(row)

                failed += 1

                print(
                    "  ✗ FAILED"
                )

            processed += 1

            # ------------------------------------------------
            # Save after every location
            # ------------------------------------------------

            save_results(results)

            # ------------------------------------------------
            # Periodic break
            # ------------------------------------------------

            if (
                processed > 0
                and
                processed % BREAK_EVERY == 0
            ):

                print()
                print(
                    "=" * 70
                )

                print(
                    f"Processed {processed} Google Place URLs."
                )

                print(
                    f"Taking a {BREAK_SECONDS}-second break..."
                )

                print(
                    "=" * 70
                )

                time.sleep(
                    BREAK_SECONDS
                )

        browser.close()

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    save_results(results)

    print()
    print("=" * 70)
    print("FINISHED")
    print("=" * 70)

    print(
        f"Total placemarks:       {len(placemarks)}"
    )

    print(
        f"Successful:              {successful}"
    )

    print(
        f"Failed:                  {failed}"
    )

    print(
        f"Skipped empty:           {skipped}"
    )

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()