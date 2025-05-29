# 🏞️ GPX + Photo to KMZ Tour Generator

This Python script creates a `.kmz` file from a **GPX track** and **timestamped photos** taken during a trek or hike. The `.kmz` file can be opened in **Google Earth Pro** to view:

- A **progressively drawn path** of your hike.
- Photos displayed at the **locations and times** they were taken.
- Custom **waypoint icons** (e.g., restaurants, hotels, summits).
- A customizable **title screen** at the start of the tour.

You can even record a **video** of the tour using Google Earth Pro.

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

## 📂 Folder Structure

All required files (gpx file, image files, icon files and the title image file should be placed in the **same folder** and that folder path should be given as the input to run the script.

---

## 📤 Output

- A file named `combined.kmz` is generated in the same folder.
- Open this file in **Google Earth Pro**.
- Find the **"Animated tour"** element in the sidebar and play it.

---

## How to Run the Script

1. Download the git repo to your computer, preferably Linux based.  
2. Copy the GPX track, title image file, and any additional icons to the same folder containing the script.  
3. Change directory (`cd`) to the folder and run the script with `.` as the input.  
   - A sample GPX track and some images are included in the repo.

### Example usage and output

```bash
(myenv) user@ubuntu22:~/convert_gpx_track_and_photos_to_kml_tour$ ls
Bridge.png  convert_gpx_track_and_photos_to_kml_tour.py  Hiker.png  Hotel.png  LICENSE  README.md  Restaurant.png  sample_files  Summit.png

(myenv) user@ubuntu22:~/convert_gpx_track_and_photos_to_kml_tour$ ls sample_files/
IMG_2025-04-05_13-51-55.jpg  IMG_2025-04-06_09-30-50.jpg  IMG_2025-04-06_09-53-05.jpg  IMG_2025-04-06_13-27-05.jpg  IMG_2025-04-06_15-09-58.jpg  IMG_2025-04-07_14-22-51.jpg  Title.png
IMG_2025-04-05_17-03-33.jpg  IMG_2025-04-06_09-30-57.jpg  IMG_2025-04-06_11-27-08.jpg  IMG_2025-04-06_14-46-24.jpg  IMG_2025-04-06_17-19-07.jpg  merged-EBC_Trek-Lukla_to_Namche_Bazaar.gpx

(myenv) user@ubuntu22:~/convert_gpx_track_and_photos_to_kml_tour$ cp sample_files/* .

(myenv) user@ubuntu22:~/convert_gpx_track_and_photos_to_kml_tour$ ls
Bridge.png                                   Hotel.png                    IMG_2025-04-06_09-30-50.jpg  IMG_2025-04-06_11-27-08.jpg  IMG_2025-04-06_15-09-58.jpg  LICENSE                                     Restaurant.png  Title.png
convert_gpx_track_and_photos_to_kml_tour.py  IMG_2025-04-05_13-51-55.jpg  IMG_2025-04-06_09-30-57.jpg  IMG_2025-04-06_13-27-05.jpg  IMG_2025-04-06_17-19-07.jpg  merged-EBC_Trek-Lukla_to_Namche_Bazaar.gpx  sample_files
Hiker.png                                    IMG_2025-04-05_17-03-33.jpg  IMG_2025-04-06_09-53-05.jpg  IMG_2025-04-06_14-46-24.jpg  IMG_2025-04-07_14-22-51.jpg  README.md                                   Summit.png

(myenv) user@ubuntu22:~/convert_gpx_track_and_photos_to_kml_tour$ python3 convert_gpx_track_and_photos_to_kml_tour.py .
Found gpx file: ./merged-EBC_Trek-Lukla_to_Namche_Bazaar.gpx.  Converting it to kml and embedding photos and track details inside it...
Combining the KML file along with the images and creating KMZ file - ./combined.kmz...

(myenv) user@ubuntu22:~/convert_gpx_track_and_photos_to_kml_tour$ ls -l combined.kmz
-rw-rw-r-- 1 user user 95516018 May 29 08:40 combined.kmz
```

---

## 🎥 Recording the Tour as a Video

Google Earth Pro allows you to **record a video** of the animated tour:
- Use **Tools -> Movie maker** to record a video of the tour.

[![Demo Video](https://img.youtube.com/vi/4lr4R1bDbq0/0.jpg)](https://youtu.be/4lr4R1bDbq0)

---

## 🧩 Troubleshooting KMZ File Size

- If the KMZ is too large, Google Earth Pro might fail to open it.
- In that case:
  1. Rename `combined.kmz` to `combined.zip`
  2. Unzip it
  3. Open the `.kml` file inside using Google Earth Pro

---

## 📦 Installation & Dependencies

This script uses numerous Python libraries.
- Run the script once. It will indicate any missing modules. Then install them with 'pip install'

---

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

---

## ⚠️ Issues

- Depending on the terrain, sometimes the track is hidden behind terrain. Tried several ways to fix this by periodically changing the bearings, but still some parts are hidden.
- The camera position is changed periodically and when it changes, it is not very smooth. Not sure how to make it smooth throughout the tour.

If anyone finds solutions to these issues, please file a pull request to get it merged. Also, any other enhancements to the script are appreciated.

---

## 🙌 Acknowledgments
ChatGPT and Google Gemini were instrumental in brainstorming, debugging, and refining the logic for this script.

Icons used in the KMZ tour are from Flaticon.

GPX track editing and waypoint support were made easier using GPX Studio.

