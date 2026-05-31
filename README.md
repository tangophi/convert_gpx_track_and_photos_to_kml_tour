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
  - Use the 'Merge the contents and keep traces disconnected' option in the Merge operation to keep the track segments separate in the same gpx file.
  - Edit Appearance of each segment to change the color to differentiate between days.
  - Edit Info of each segment to give a name to each day's track in the format such as "Audens Col Trek - Day 4 - To Sukhatal (4773m)" or "EBC Trek - Day 5 - To Tengboche".  The script will then extract "Audens Col Trek - Day 4" or "EBC Trek - Day 5" and display that as the first line.  The rest will be line 2.
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
- In Gpx studio, sometimes for waypoints, a suitable custom icon may not be available and the sym tag is not added for such waypoints.  For example, a Temple icon is not available in Gpx studio.  In such cases, after the gpx file is created, manually edit the file and add something like the following sym tag to the waypoint.  Ensure that a Temple.png icon file is also available in the same folder.
  ```xml
    <wpt lat="30.994463" lon="78.941278">
      <ele>3054.6204168133636</ele>
      <name>Gangotri Temple</name>
      <sym>Temple</sym>
    </wpt>
  ```

### 4. Title Image
- A transparent `Title.png` image shown at the beginning of the tour.
  - Use Inkscape to create a transparent PNG image with your desired title text.

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
user@ubuntu22:~$ source myenv/bin/activate
(myenv) user@ubuntu22:~$

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

Alternatively, you can use the following command to run the script.  Ensure that all the icon png files are copied to the same directory (./Audens_Col_photo_tour) as the image files and gpx file.  The Title.png file should also be in this directory.
```bash
user@ubuntu22:~$ source myenv/bin/activate
(myenv) user@ubuntu22:~$ python3 convert_gpx_track_and_photos_to_kml_tour.py ./Audens_Col_photo_tour
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

## 🔧 Script Customization

The following section of the script can be customized based on your preferences and data:

```python
#
# Change this to the proper offset based on where the GPX track was recorded and the photos taken
#
LOCAL_TIME_OFFSET_FROM_UTC = timedelta(hours=5, minutes=30)

#
# Duration for showing each photo
#
PHOTO_DURATION_TIME_IN_SECS = 2

#
# Pause between displaying each track segment. This controls how fast or slow the line progresses
# in a tour. The smaller the number, the faster the line progresses, and vice versa.
#
PAUSE_BETWEEN_LINE_SEGMENTS_IN_SECS = 0.005

#
# Camera tilt angle in degrees. If it's 0, it means the camera is looking straight down — the terrain
# is not shown clearly though.
#
CAMERA_TILT_ANGLE = 60

#
# Camera range in meters determines how far the view is shown from.
#
CAMERA_RANGE = 1000
```

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

