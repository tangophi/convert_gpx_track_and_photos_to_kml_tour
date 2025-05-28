# 🏞️ GPX + Photo to KMZ Tour Generator

This Python script creates a `.kmz` file from a **GPX track** and **timestamped photos** taken during a trek or hike. The `.kmz` file can be opened in **Google Earth Pro** to view:

- A **progressively drawn path** of your hike.
- Photos displayed at the **locations and times** they were taken.
- Custom **waypoint icons** (e.g., restaurants, hotels, summits).
- A customizable **title screen** at the start of the tour.

You can even record a **video** of the tour using Google Earth Pro.

---

## 📂 Folder Structure

All required files should be placed in a **single folder**:


---

## 📥 Inputs

### 1. GPX Track File (`.gpx`)
- Should contain:
  - Latitude, Longitude
  - Elevation
  - Timestamps
- Can be exported from:
  - **Strava**, **Gaia GPS**, or any GPS tracking app.
- For multi-day treks:
  - Combine multiple tracks via [GPX Studio](https://gpx.studio/)
  - Add **waypoints** (like lunch stops, hotels) using GPX Studio.

### 2. Photos (`.jpg`, `.jpeg`, `.heic`)
- Must include **EXIF timestamps**.
- **Geotags in images are not used**.
- The script matches photos to GPX points based on timestamp only.

> ⚠️ **Timezone alignment is critical.**  
> Most GPX timestamps are in **UTC**, while camera photos are in **local time**.  
> Update the script’s `LOCAL_TIME_OFFSET_FROM_UTC` to reflect your photo timezone.  
> _(e.g., for Nepal: `timedelta(hours=5, minutes=45)`)_

### 3. Waypoint Icons
- Transparent `.png` icons should be named based on the `<sym>` tag in the GPX file.
  - For example:
    ```xml
    <sym>Restaurant</sym>  →  Restaurant.png
    ```
- Common icons to include:
  - `Hiker.png`, `Bridge.png`, `Hotel.png`, `Restaurant.png`, `Summit.png`
- Download free icons from [Flaticon](https://www.flaticon.com/free-icons)

### 4. Title Image
- A transparent `Title.png` image shown at the beginning of the tour.

---

## 📤 Output

- A file named `combined.kmz` is generated in the same folder.
- Open this file in **Google Earth Pro**.
- Find the **"Animated tour"** element in the sidebar and press **play**.

---

## 🧩 Troubleshooting KMZ File Size

- If the KMZ is too large, Google Earth Pro might fail to open it.
- In that case:
  1. Rename `combined.kmz` to `combined.zip`
  2. Unzip it
  3. Open the `.kml` file inside using Google Earth Pro

---

## 🎥 Recording the Tour as a Video

Google Earth Pro allows you to **record a video** of the animated tour:
1. Play the animated tour
2. Use Google Earth's **movie maker** to export the video

---

## 📦 Installation & Dependencies

This script uses the following Python libraries:
- `gpxpy`
- `Pillow`
- `pyheif` (for `.heic` image support)

Run the script once. It will indicate any missing modules. Then install them with 'pip install'



## ⚙️ Customization
You can tailor the script for your trip or region:

Timezone Offset:
Modify LOCAL_TIME_OFFSET_FROM_UTC to match the timezone where your photos were taken.

Photo Display Duration:
Change how long each image stays on screen during the animation by adjusting values in the script.

Waypoint Icons:
Add or replace PNG icons matching the <sym> names used in your GPX file.

Title and Overlays:
Replace Title.png with your own custom title image. You can also modify or add additional overlay images or text.

## 🙌 Acknowledgments
ChatGPT and Google Gemini were instrumental in brainstorming, debugging, and refining the logic for this script.

Icons used in the KMZ tour are from Flaticon.

GPX track editing and waypoint support were made easier using GPX Studio.

