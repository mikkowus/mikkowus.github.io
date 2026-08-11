# Running `extract_coordinates_final.py`

This script extracts latitude/longitude coordinates from a Google Maps KML export and saves the results to a CSV file.

## 1. Requirements

You need:

- Python 3.10 or newer
- The `extract_coordinates_final.py` script
- Your Google Maps `.kml` file
- Playwright
- Playwright's Chromium browser

You do **not** need a Google API key or Gemini API key.

---

## 2. Install Playwright

Open PowerShell and navigate to the folder containing the script.

For example:

```powershell
cd C:\canoe-training-location-picker

Install Playwright:

python -m pip install playwright

Then install only Chromium:

python -m playwright install chromium

You do not need to install Firefox or WebKit.

3. Put Your KML File in the Same Folder

Your folder should look something like:

C:\canoe-training-location-picker\
│
├── extract_coordinates_final.py
└── paddlespots.kml

The KML file should be the Google Maps list you exported.

4. Set the KML Filename

Open:

extract_coordinates_final.py

Find the KML filename setting near the top of the script.

For example:

KML_FILE = "paddlespots.kml"

Change the filename to match your actual KML file.

For example, if your file is:

my_google_maps_list.kml

use:

KML_FILE = "my_google_maps_list.kml"

Save the file.

5. Run the Script

In PowerShell, make sure you are in the project folder:

cd C:\canoe-training-location-picker

Then run:

python extract_coordinates_final.py
6. What Happens

The script will read every location in the KML and try several methods to find its coordinates.

You will see output similar to:

Reading KML...
Found 207 placemarks.

[2] Rainbow Bend State Forest Campground
✓ PLACE COORDINATES: 44.6697377, -84.4177964

[3] 44°40'35.8"N 84°32'52.4"W
✓ Direct coordinates: 44.6766125, -84.5478871

[4] Grayling City Park
✓ PLACE COORDINATES: 44.6599493, -84.7132973

Some locations may say:

✗ Could not find place coordinates

This means the script could not automatically extract coordinates for that particular location.

7. Find the Output

When the script finishes, it will create:

paddlespots_coordinates.csv

The CSV will contain:

Name,Latitude,Longitude,Method,Google Maps URL

You can open the CSV in Excel, Google Sheets, or another spreadsheet program.

8. If python Doesn't Work

If PowerShell says that python is not recognized, try:

py extract_coordinates_final.py

If you have multiple Python installations, you can also run it using the full path to Python:

& "C:\Path\To\Python\python.exe" extract_coordinates_final.py
Quick Start

If Python is already installed and your KML file is in the same folder as the script, the complete setup is:

python -m pip install playwright
python -m playwright install chromium
python extract_coordinates_final.py

That's it.

The results will be written to:

paddlespots_coordinates.csv