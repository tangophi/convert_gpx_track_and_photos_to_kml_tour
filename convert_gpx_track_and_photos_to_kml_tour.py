#
# This script is used to create a KMZ file from a gpx track and photos taken
# during the track. The KMZ file can then be opened in Google Earth Pro and
# a video of the track as a progressive line with photos shown at the points
# they were taken.
#
# Input is the name of a folder that contains the following:
# - a file of a gpx track (with a .gpx extension).  This should contain track points
#   with latitude, longitude, elevation and timestamp
#   - The gpx file can be created with apps such as Strava or Gaia GPS during a hike
#     or even a multi-day trek.
#   - If there are several gpx files taken during a multi-day trek, all those gpx tracks
#     can be combined using https://gpx.studio/
#     - Also waypoints can be added to the track in https://gpx.studio/
#       - These waypoints can include places such as restaurants and hotels
# - image files of photos (jpg, jpeg and heic only) taken during the track.  These should
#   have proper timestamps in the EXIF metadata.
#   - The GPS data from the image files are not used in this script
#   - Photo timestamps are extracted using DateTimeOriginal from EXIF data for accurate
#     capture time.  Falls back to DateTime (file modification time) if DateTimeOriginal
#     is not available.
#   - The method by which the image files are embedded is solely based on the timestamp.
#     - Gpx tracks usually have timestamps in the UTC format whereas image files will have
#       timestamps based on the timezones where they were taken.
#     - In this script, the photos were taken in Nepal and hence the timestamps of the gpx
#       trackpoints were converted to Nepal time.  The script should be modified if photos
#       were taken in other regions.  LOCAL_TIME_OFFSET_FROM_UTC should be changed to reflect
#       the time delta from UTC.
#
# Output is a file called combined.kmz in the same folder.  This file can be opened in
# Google Earth Pro and a tour can be played from the 'Animated tour' element of the KML.
# Sometimes if there are lots of photos, then the kmz file can get huge and Google Earth Pro
# may not open the file properly giving some weird error.  In that case, rename combined.kmz
# to combined.zip and then unzip the file. Then open the .kml file.
#
# A video of the tour can then be made in Google Earth Pro.
#
# Camera behaviour:
#   - The camera heading uses exponential moving average (EMA) smoothing to avoid jarring
#     angle changes, especially on zigzag/switchback trails.  The raw bearing is calculated
#     towards a point 200 trackpoints ahead for general direction of travel.
#   - The camera targets a point 20 trackpoints ahead of the hiker so the progressing
#     track tip is always visible, even when terrain (mountains) would otherwise block it.
#   - Camera position updates every 20 trackpoints with a 1-second smooth fly-to transition.
#
# Text overlay:
#   - A transparent PNG image is generated every 10 trackpoints showing track details.
#   - If the track name contains a "Day N" pattern (e.g. "EBC Trek - Day 5 - To Tengboche"),
#     it is split into separate lines:
#       Line 1: Trek name and day (e.g. "EBC Trek - Day 5")
#       Line 2: Destination (e.g. "To Tengboche")
#       Line 3: Distance, altitude and time
#     If the destination text is too long, it wraps into two lines (4 lines total) and
#     the image height is increased to accommodate.
#   - If the track name does not match the "Day N" pattern, the original 2-line layout
#     is used (track name + stats).
#
# Other requirements:
#   <wpt lat="27.923474" lon="86.805625">
#     <ele>4597.1173153701775</ele>
#     <name>Thukla Fast Food &amp; Bakery, Thukla</name>
#     <cmt>Lunch on day 7</cmt>
#     <desc>Lunch on day 7</desc>
#     <sym>Restaurant</sym>
#   </wpt>    
#
# - There are several transparent icon files downloaded from https://www.flaticon.com/free-icons
#   that should also be present in the folder.  These should be named as Hiker.png, Bridge.png,
#   Hotel.png, Restaurant.png, Summit.png, Campground.png, Temple.png, etc.  These icons are
#   displayed for a waypoint defined like the above in the gpx track.
#   - If there are other types of waypoints in the gpx track, then download relevant icons and
#     save them as the same name displayed in <sym> field.
# - Also a transparent Title.png should be present.  This is used as the title of the tour/video.
# - Several python modules need to be installed before the script can be run.  Just run the script,
#   the script will throw an error listing the missing package - install them
#
#
# ChatGPT, Google Gemini and Windsurf Cascade helped a lot in creating this script !!!
#
    


import os
import sys
import gpxpy
import gpxpy.gpx
from datetime import datetime, timedelta, timezone
import piexif
import pyheif
import xml.etree.ElementTree as ET
from math import radians, sin, cos, sqrt, atan2, degrees
import zipfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import datetime
import re


#
# Change this to the proper offset based on where the gpx track was recorded and the photos taken
#
LOCAL_TIME_OFFSET_FROM_UTC = timedelta(hours=5, minutes=30)

#
# Duration for showing each photo
#
PHOTO_DURATION_TIME_IN_SECS=2

#
# Pause between displaying each track segment.  This controls how fast or slow the line progresses
# in a tour.  The smaller the number the faster the line progresses and vice versa.  
#
PAUSE_BETWEEN_LINE_SEGMENTS_IN_SECS=0.005

#
# Camera tilt angle in degrees.  If its 0 it means the camera is looking straight down - the terrain
# is not shown clearly though.
#
CAMERA_TILT_ANGLE=60

#
# Camera range in metres determines how far the view is shown from.
#
CAMERA_RANGE=2000
#
# How often to update the camera LookAt during the tour, expressed in number of
# trackpoints between updates. Larger values mean fewer transitions and a
# shorter/faster tour; smaller values mean more transitions and a longer/slower
# tour. Last year's value (2025) = 100.
#
UPDATE_CAMERA_FREQUENCY=100

#
# Duration in seconds of each per-update camera FlyTo transition. Larger values
# produce smoother, slower moves and increase total tour length; smaller values
# are snappier and shorten the tour. Last year's value (2025) = 0.3 seconds.
#
CAMERA_FLYTO_DURATION_IN_SECS=0.3



#
# The time stored in gpx track is usually in UTC format.  Change that to
# the local time and return the local time as a string.
#
# Snippet of a gpx trackpoint
#       <trkpt lat="27.687622" lon="86.729066">
#         <ele>2823.8</ele>
#         <time>2025-04-05T08:10:08.000Z</time>
#       </trkpt>
#
def convert_to_local_time_string(utc_time):
    """
    Converts a UTC datetime object to local time and formats it as a string
    without timezone information.

    Args:
        utc_time: A datetime.datetime object representing time in UTC.

    Returns:
        A string representing the local time in 'YYYY-MM-DD HH:MM:SS' format.
        Returns None on error.
    """
    if not isinstance(utc_time, datetime.datetime):
        print("Error: Input must be a datetime.datetime object.")
        return None

    # Ensure the input datetime is timezone-aware and in UTC.
    if utc_time.tzinfo is None or utc_time.tzinfo != timezone.utc:
        utc_time = utc_time.replace(tzinfo=timezone.utc)

    # Convert the UTC time to local time
    local_time = utc_time + LOCAL_TIME_OFFSET_FROM_UTC

    # Format the local time as a string, excluding timezone info
    local_time_str = local_time.strftime('%Y-%m-%d %H:%M:%S')
    return local_time_str

        
def get_image_info(filepath, filename):
    ext = filepath.lower().split('.')[-1]
    if ext in ['jpg', 'jpeg']:
        img = Image.open(filepath)
        exif_data = piexif.load(img.info['exif'])
        # Use DateTimeOriginal for actual photo capture time, not DateTime (file modification time)
        if 'Exif' in exif_data and piexif.ExifIFD.DateTimeOriginal in exif_data['Exif']:
            dt_str = exif_data['Exif'][piexif.ExifIFD.DateTimeOriginal].decode()
        else:
            dt_str = exif_data['0th'][piexif.ImageIFD.DateTime].decode()
        dt = datetime.datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
        orientation = exif_data["0th"].get(piexif.ImageIFD.Orientation, "Not found")
        width, height = img.size
        #bbox = img.getbbox()
        #print(f"image:{filename} size:{width}x{height}")
        #print("Image bounding box (non-transparent content):", bbox)
    elif ext == 'heic':
        heif_file = pyheif.read(filepath)
        width = heif_file.size[0]
        height = heif_file.size[1]

        for metadata in heif_file.metadata or []:
            if metadata['type'] == 'Exif':
                exif_dict = piexif.load(metadata['data'])
                # Use DateTimeOriginal for actual photo capture time, not DateTime (file modification time)
                if 'Exif' in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict['Exif']:
                    dt_str = exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal].decode()
                else:
                    dt_str = exif_dict['0th'][piexif.ImageIFD.DateTime].decode()
                dt = datetime.datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                #print (f"datetime: {dt}")
                
                exif_dict = piexif.load(metadata['data'][6:])  # Skip "Exif\0\0"
                orientation = exif_dict["0th"].get(piexif.ImageIFD.Orientation, "Not found")
                break
        else:
            raise ValueError(f"No EXIF DateTime found in {filepath}")
    else:
        raise ValueError(f"Unsupported image format: {filepath}")
        
    image_info = {"filename":filename, "filepath":filepath, "timestamp":(dt - LOCAL_TIME_OFFSET_FROM_UTC).replace(tzinfo=timezone.utc), "width":width, "height":height, "orientation":orientation}
    #print(f"image_info: {image_info}")
    return image_info


def convert_heic_to_jpg(heic_path, jpg_path):
    heic_img = pyheif.read(heic_path)

    img = Image.frombytes(
        heic_img.mode, 
        heic_img.size, 
        heic_img.data, 
        "raw"
    )
    
    img.save(jpg_path, "JPEG")
        

def file_exists_case_insensitive(target_path):
    folder = os.path.dirname(target_path)
    target_file = os.path.basename(target_path).lower()

    try:
        return any(f.lower() == target_file for f in os.listdir(folder))
    except FileNotFoundError:
        return False
        
    
def get_info_of_all_images_files(folder):
    local_photo_images_info = []
    for filename in os.listdir(folder):
        if filename.lower().endswith(('.jpg', '.jpeg', '.heic')):
            filepath = os.path.join(folder, filename)
            try:
                if filename.lower().endswith(('.jpeg')):
                    #print (f"filename: {filename}")
                    base_name_img = os.path.splitext(os.path.basename(filepath))[0]
                    equivalent_heic_filename = f"{base_name_img}.heic"
                    equivalent_heic_filepath = os.path.join(folder, equivalent_heic_filename)
                    #print (f"equivalent_heic_filename: {equivalent_heic_filename}   equivalent_heic_filepath:{equivalent_heic_filepath}")
                    if file_exists_case_insensitive(equivalent_heic_filepath):
                        continue
                
                info = get_image_info(filepath, filename)
                
                #
                # Google Earth Pro doesnt display HEIC files.  Hence convert them to jpeg and store
                # the name and path of the jpeg file
                #
                if filename.lower().endswith(('.heic')):
                    #print ("Convert HEIC to jpeg")
                    base_name_img = os.path.splitext(os.path.basename(info["filepath"]))[0]
                    new_jpeg_filename = f"{base_name_img}.jpeg"
                    new_jpeg_filepath = os.path.join(folder, new_jpeg_filename)
                    convert_heic_to_jpg(filepath, new_jpeg_filepath)
                    info["filename"] = new_jpeg_filename
                    info["filepath"] = new_jpeg_filepath
                    #
                    # When the heic image is converted, its orientation is fixed in the jpeg version.
                    # Hence ignore the orientation data from the heic file.
                    #
                    info["orientation"] = 1
                
                local_photo_images_info.append(info)
            except Exception as e:
                print(f"Warning: Skipping {filename}: {e}")
    return sorted(local_photo_images_info, key=lambda info: info["filename"])


    
def create_photo_image_overlay_element(info):
    """
    Creates a KML <ScreenOverlay> element for displaying a photo image with a fixed size.

    Args:
        image_path (str): The path to the image file.
        overlay_id (str): A unique ID for the ScreenOverlay.

    Returns:
        ET.Element: The created <ScreenOverlay> element.
    """
    base_name_img = os.path.splitext(os.path.basename(info["filepath"]))[0]
    overlay_id = f"image_{base_name_img}"
    
    screen_overlay = ET.Element("ScreenOverlay", attrib={"id": overlay_id})
    ET.SubElement(screen_overlay, "name").text = f"ImageOverlay_{overlay_id}"
    icon = ET.SubElement(screen_overlay, "Icon")
    ET.SubElement(icon, "href").text = os.path.basename(info["filepath"])

    ET.SubElement(screen_overlay, "overlayXY", x="0", y="1", xunits="fraction", yunits="fraction")
    ET.SubElement(screen_overlay, "screenXY", x="0", y="1", xunits="fraction", yunits="fraction")
    
    #
    # If the image aspect ration is >= the usual screen aspect ratio, then fit the width of the image
    # to 80% of screen width while maintaining the aspect ratio.  Otherwise, fit the height of the image
    # to 80% of screen height while maintaing the aspect ratio.
    #
    if info["width"]/info["height"] >= 16/9:
        ET.SubElement(screen_overlay, "size", x="0.9", y="0", xunits="fraction", yunits="fraction")
    else:
        ET.SubElement(screen_overlay, "size", x="0", y="0.9", xunits="fraction", yunits="fraction")
    
    #
    # Some jpeg images taken from the phone have orientation set to values other than 1.  When these images
    # are seen on phone or computer, it is rotated based on this value and the image is shown properly.
    # But Google Earth Pro doesn't rotate based on the orientation value and hence the following code is
    # needed to rotate those images so that they are shown properly during a tour.
    #
    if info["orientation"] == 6:
        ET.SubElement(screen_overlay, "rotation").text = "-90"
    elif info["orientation"] == 8:
        ET.SubElement(screen_overlay, "rotation").text = "90"
    elif info["orientation"] == 3:
        ET.SubElement(screen_overlay, "rotation").text = "180"
    
    ET.SubElement(screen_overlay, "visibility").text = "0"
    return screen_overlay


def create_title_overlay_element(folder):
    filepath = os.path.join(folder, "Title.png")
    overlay_id = "title_overlay"
    
    screen_overlay = ET.Element("ScreenOverlay", attrib={"id": overlay_id})
    ET.SubElement(screen_overlay, "name").text = f"ImageOverlay_{overlay_id}"
    icon = ET.SubElement(screen_overlay, "Icon")
    ET.SubElement(icon, "href").text = os.path.basename(filepath)
    ET.SubElement(screen_overlay, "overlayXY", x="0.5", y="0.5", xunits="fraction", yunits="fraction")
    ET.SubElement(screen_overlay, "screenXY", x="0.5", y="0.5", xunits="fraction", yunits="fraction")
    ET.SubElement(screen_overlay, "size", x="1", y="0", xunits="fraction", yunits="fraction")
    ET.SubElement(screen_overlay, "visibility").text = "1"

    return screen_overlay
    
    
def create_text_image_overlay_element(text_image_path, overlay_id):
    """
    Creates a KML <ScreenOverlay> element for displaying a photo image with a fixed size.

    Args:
        image_path (str): The path to the image file.
        overlay_id (str): A unique ID for the ScreenOverlay.

    Returns:
        ET.Element: The created <ScreenOverlay> element.
    """
    screen_overlay = ET.Element("ScreenOverlay", attrib={"id": overlay_id})
    ET.SubElement(screen_overlay, "name").text = f"ImageOverlay_{overlay_id}"
    icon = ET.SubElement(screen_overlay, "Icon")
    ET.SubElement(icon, "href").text = os.path.basename(text_image_path)
    ET.SubElement(screen_overlay, "overlayXY", x="0.01", y="0.01", xunits="fraction", yunits="fraction")
    ET.SubElement(screen_overlay, "screenXY", x="0.01", y="0.01", xunits="fraction", yunits="fraction")
    ET.SubElement(screen_overlay, "size", x="0.7", y="0", xunits="fraction", yunits="fraction")
    ET.SubElement(screen_overlay, "visibility").text = "0"
    return screen_overlay
    
    
def smooth_bearing_ema(new_bearing, previous_bearing, alpha=0.1):
    """
    Smooths bearing using exponential moving average with circular angle handling.
    Handles the 0/360 degree wrap-around correctly.
    
    Args:
        new_bearing: The new raw bearing in degrees (0-360).
        previous_bearing: The previous smoothed bearing in degrees (0-360), or None.
        alpha: Smoothing factor (0-1). Lower = smoother. Default 0.1.
    
    Returns:
        The smoothed bearing in degrees (0-360).
    """
    if previous_bearing is None:
        return new_bearing
    
    diff = new_bearing - previous_bearing
    if diff > 180:
        diff -= 360
    elif diff < -180:
        diff += 360
    
    smoothed = previous_bearing + alpha * diff
    return smoothed % 360


def calculate_bearing(points, current_index, points_to_consider=100):
    """
    Calculates the bearing from the current track point to a point
    further along the track.

    Args:
        points: A list of tuples, where each tuple contains coordinate data.
                The order of elements in the tuple is (longitude, latitude, ...).
        current_index: The index of the starting track point.
        points_to_consider: The number of subsequent track points to consider
                            as the end point for bearing calculation (default is 100).

    Returns:
        The bearing in degrees (0-360) from the current point to the
        point `points_to_consider` steps ahead, or None if there are
        fewer than 2 points within the specified range.
    """
    num_points = len(points)

    if current_index >= num_points - 1:
        return None

    end_index = min(current_index + points_to_consider, num_points - 1)

    if end_index <= current_index:
        return None

    lon1_deg = points[current_index]["longitude"]
    lat1_deg = points[current_index]["latitude"]
    lon2_deg = points[end_index]["longitude"]
    lat2_deg = points[end_index]["latitude"]

    lon1 = radians(float(lon1_deg))
    lat1 = radians(float(lat1_deg))
    lon2 = radians(float(lon2_deg))
    lat2 = radians(float(lat2_deg))

    dLon = lon2 - lon1

    y = sin(dLon) * cos(lat2)
    x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dLon)

    bearing_rad = atan2(y, x)
    bearing_deg = (degrees(bearing_rad) + 360) % 360
    return bearing_deg


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the distance in meters between two GPS coordinates.
    Uses the Haversine formula for accuracy on a sphere.
    """
    R = 6371000  # Radius of the Earth in meters
    #print(f"lat1: {lat1} lon1: {lon1} lat2: {lat2} lon2: {lon2}")
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance

#
# This function creates a transparent png image for each trackpoint.  The image will contain
# details of the track name, destination, distance from the start, altitude and the time.
# These images will be shown one by one during the tour.
#
# If text1 matches the "Day N" pattern (e.g. "EBC Trek - Day 5 - To Tengboche"), it is
# split into: Line 1 = "EBC Trek - Day 5", Line 2 = "To Tengboche", Line 3 = text2 (stats).
# If the destination text (Line 2) is too long to fit in one line, it wraps into two lines,
# producing 4 lines total and a taller image (360px instead of 300px).
# If text1 does not match the pattern, the original 2-line layout is used.
#
def create_text_image_png(text1, text2, filename):
    width = 1600
    font_size = 40
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Update if needed
    font = ImageFont.truetype(font_path, font_size)
    line_spacing = 60
    max_text_width = width - 2 * 20

    # Try to split text1 on "Day <number>" pattern
    match = re.search(r'(.*Day\s+\d+)\s*-\s*(.*)', text1)
    if match:
        header_text = match.group(1).strip()
        destination_text = match.group(2).strip()

        # Check if destination text fits in one line; if not, wrap at word boundary
        bbox = font.getbbox(destination_text)
        text_width = bbox[2] - bbox[0]
        if text_width > max_text_width:
            words = destination_text.split()
            line1_words = []
            for word in words:
                test_line = ' '.join(line1_words + [word])
                tw = font.getbbox(test_line)[2] - font.getbbox(test_line)[0]
                if tw > max_text_width and line1_words:
                    break
                line1_words.append(word)
            dest_line1 = ' '.join(line1_words)
            dest_line2 = ' '.join(words[len(line1_words):])
            texts = [header_text, dest_line1, dest_line2, text2]
            height = 360
        else:
            texts = [header_text, destination_text, text2]
            height = 300
        base_y = 120
    else:
        texts = [text1, text2]
        height = 300
        base_y = 180

    # --- SHADOW VERSION ---
    img_shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    shadow_offset = (2, 2)
    blur_radius = 2

    for i, txt in enumerate(texts):
        y = base_y + i * line_spacing
        x = 20

        # Create a temporary image for the shadow
        tmp_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        tmp_draw = ImageDraw.Draw(tmp_img)
        tmp_draw.text((x + shadow_offset[0], y + shadow_offset[1]), txt, font=font, fill="black")

        # Blur and paste
        blurred = tmp_img.filter(ImageFilter.GaussianBlur(blur_radius))
        img_shadow = Image.alpha_composite(img_shadow, blurred)

        # Draw the white text on top
        draw_shadow = ImageDraw.Draw(img_shadow)
        draw_shadow.text((x, y), txt, font=font, fill="white")

    img_shadow.save(f"{filename}")




#
# The main function of the script
#        
def create_kmz_from_gpx_and_photos(folder):

    #
    # Find the gpx file in the folder.  There should be only one gpx file.  Even if there are other gpx
    # files, they will be ignored.  Get the data from the gpx file into gpx variable.
    #
    for file in os.listdir(folder):
        # print(f"folder: {folder} file: {file}")
        if file.lower().endswith('.gpx'):
            gpx_file_name = file
            with open(os.path.join(folder, file), 'r', encoding='utf-8') as gpx_file:
                print(f"Found gpx file: {gpx_file.name}.  Converting it to kml and embedding photos and track details inside it...")
                gpx = gpxpy.parse(gpx_file)
                break
                
    if not 'gpx' in locals() or 'gpx' in globals():
        print("No GPX file found in folder")
        return

    photo_images_info = get_info_of_all_images_files(folder)

    script_folder = os.path.dirname(os.path.abspath(__file__))

    default_color = 'FFFFFFFF'  # White 
    points = []
    
    #
    # Get the points data from the GPX file into points variable
    #
    for track in gpx.tracks:
        # Get color from GPX track extensions.  Handles missing color.
        track_color = default_color
        if track.extensions:
            for extension in track.extensions:
                if extension.tag.endswith('line'):
                    for sub_extension in extension:
                        if sub_extension.tag.endswith('color') and sub_extension.text:
                            track_color = sub_extension.text
                            break  # Exit inner loop
                    break  # Exit outer loop
        for segment in track.segments:
            for point in segment.points:
                points.append( {"longitude":point.longitude, "latitude":point.latitude, "elevation":point.elevation or 0, "color":track_color, "time":point.time, "name":track.name} )

    if len(points) < 2:
        return  # Skip if not enough points to form a line


    #
    # Define the beginning of the kml doc
    #
    doc = ET.Element('kml', {
        'xmlns': "http://www.opengis.net/kml/2.2",
        'xmlns:gx': "http://www.google.com/kml/ext/2.2"
    })
    document = ET.SubElement(doc, 'Document')
    ET.SubElement(document, 'name').text = gpx_file_name
    
    # gx:Tour
    tour = ET.SubElement(document, 'gx:Tour')
    ET.SubElement(tour, 'name').text = 'Animated tour'
    playlist = ET.SubElement(tour, 'gx:Playlist')
    
    #
    # This is to show the globe with India at the center from 4000km range.
    #
    flyto = ET.SubElement(playlist, 'gx:FlyTo')
    ET.SubElement(flyto, 'gx:duration').text = '0'
    ET.SubElement(flyto, 'gx:flyToMode').text = 'smooth'
    lookat = ET.SubElement(flyto, 'LookAt')
    ET.SubElement(lookat, 'longitude').text = '78.9629'
    ET.SubElement(lookat, 'latitude').text = '20.5937'
    ET.SubElement(lookat, 'altitude').text = '0'
    ET.SubElement(lookat, 'heading').text = '0'
    ET.SubElement(lookat, 'tilt').text = '0'
    ET.SubElement(lookat, 'range').text = '40000000'
    ET.SubElement(lookat, 'altitudeMode').text = 'relativeToGround'
            
    #
    # This is to zoom to the starting point of the track.
    #
    flyto = ET.SubElement(playlist, 'gx:FlyTo')
    ET.SubElement(flyto, 'gx:duration').text = '5'
    ET.SubElement(flyto, 'gx:flyToMode').text = 'smooth'
    lookat = ET.SubElement(flyto, 'LookAt')
    ET.SubElement(lookat, 'longitude').text = str(points[0]["longitude"])
    ET.SubElement(lookat, 'latitude').text = str(points[0]["latitude"])
    ET.SubElement(lookat, 'altitude').text = '0'
    ET.SubElement(lookat, 'heading').text = '0'
    ET.SubElement(lookat, 'tilt').text = '0'
    ET.SubElement(lookat, 'range').text = '1000'
    ET.SubElement(lookat, 'altitudeMode').text = 'relativeToGround'

    wait_element = ET.SubElement(playlist, "gx:Wait")
    ET.SubElement(wait_element, "gx:duration").text = "1"
    
    #
    # Hide the title after the camera has zoomed into the starting point of the track that should
    # have happened now.
    #
    title_filepath = os.path.join(folder, "Title.png")
    if os.path.exists(title_filepath):
        animated_update_hide = ET.SubElement(playlist, 'gx:AnimatedUpdate')
        update_hide = ET.SubElement(animated_update_hide, "Update")
        ET.SubElement(update_hide, 'targetHref')
        change_hide = ET.SubElement(update_hide, "Change")
        screen_overlay_hide = ET.SubElement(change_hide, "ScreenOverlay", attrib={"targetId": "title_overlay"})
        ET.SubElement(screen_overlay_hide, "visibility", attrib={"xmlns":"http://www.opengis.net/kml/2.2"}).text = "0"        

    # Show all the waypoints at the beginning of the tour
    for i, waypoint in enumerate(gpx.waypoints):
        animated_update_show = ET.SubElement(playlist, 'gx:AnimatedUpdate')
        update_show = ET.SubElement(animated_update_show, "Update")
        ET.SubElement(update_show, 'targetHref')
        change_show = ET.SubElement(update_show, "Change")
        placemark_show = ET.SubElement(change_show, "Placemark", attrib={"targetId": f'waypoint{i}'})
        ET.SubElement(placemark_show, "visibility").text = "1"

    # Change camera position every this number of points.
    # The bearing is smoothed using EMA (exponential moving average) to avoid jarring
    # camera angle changes on zigzag/switchback trails.  The camera targets a point
    # 20 trackpoints ahead of the hiker to keep the progressing track tip visible.
    update_camera_frequency = UPDATE_CAMERA_FREQUENCY

    image_index = 0
    previous_text_image_overlay_id = ""
    smoothed_bearing = None
    
    #    
    # Create animated elements
    # - Show all the photos between the previous trackpoint and the current trackpoint, each for 2 seconds
    # - Change the camera position
    # - Show a line between the current trackpoint and the next trackpoint
    # - Show the transparent png that has details of the track name, distance, elevation and time.  Before
    #   that hide the previous such image.
    #
    for i in range(len(points) - 1):
        lon, lat, elevation, color, time, track_name = (
            points[i]["longitude"],
            points[i]["latitude"],
            points[i]["elevation"],
            points[i]["color"],
            points[i]["time"],
            points[i]["name"]
        )
       
        raw_bearing = calculate_bearing(points, i, 200)
        if raw_bearing is not None:
            smoothed_bearing = smooth_bearing_ema(raw_bearing, smoothed_bearing, alpha=0.1)
        bearing = smoothed_bearing if smoothed_bearing is not None else 0

        # Show all photos before the current trackpoint apart from the ones already shown.
        # This also ensures that all the photos taken before the tracking had begun will be
        # shown initially.
        while image_index < len(photo_images_info) and photo_images_info[image_index]["timestamp"] < time:
            img_base_name = os.path.splitext(os.path.basename(photo_images_info[image_index]["filename"]))[0]
            overlay_id = f"image_{img_base_name}"
                
            animated_update_show = ET.SubElement(playlist, 'gx:AnimatedUpdate')
            update_show = ET.SubElement(animated_update_show, "Update")
            ET.SubElement(update_show, 'targetHref')
            change_show = ET.SubElement(update_show, "Change")
            screen_overlay_show = ET.SubElement(change_show, "ScreenOverlay", attrib={"targetId": overlay_id})
            ET.SubElement(screen_overlay_show, "visibility", attrib={"xmlns": "http://www.opengis.net/kml/2.2"}).text = "1"

            wait_element = ET.SubElement(playlist, "gx:Wait")
            ET.SubElement(wait_element, "gx:duration").text = str(PHOTO_DURATION_TIME_IN_SECS)

            animated_update_hide = ET.SubElement(playlist, 'gx:AnimatedUpdate')
            update_hide = ET.SubElement(animated_update_hide, "Update")
            ET.SubElement(update_hide, 'targetHref')
            change_hide = ET.SubElement(update_hide, "Change")
            screen_overlay_hide = ET.SubElement(change_hide, "ScreenOverlay", attrib={"targetId": overlay_id})
            ET.SubElement(screen_overlay_hide, "visibility", attrib={"xmlns": "http://www.opengis.net/kml/2.2"}).text = "0"
            
            image_index += 1

        # Show the transparent png image that has the following details.
        # Line 1: Trek name and day (if "Day N" pattern found in track name)
        # Line 2: Destination (or the full track name if no pattern match)
        # Line 3: Distance travelled so far, current altitude and current time.
        if i==0 or i%10 == 0:
            text_image_file_name = os.path.join(folder, "text_img_" + str(i))
            text_image_base_name = os.path.splitext(os.path.basename(text_image_file_name))[0]
            text_image_overlay_id = f"image_{text_image_base_name}"

            # first hide the previous text image overlay
            if previous_text_image_overlay_id != "":
                animated_update_hide = ET.SubElement(playlist, 'gx:AnimatedUpdate')
                update_hide = ET.SubElement(animated_update_hide, "Update")
                ET.SubElement(update_hide, 'targetHref')
                change_hide = ET.SubElement(update_hide, "Change")
                screen_overlay_hide = ET.SubElement(change_hide, "ScreenOverlay", attrib={"targetId": previous_text_image_overlay_id})
                ET.SubElement(screen_overlay_hide, "visibility", attrib={"xmlns": "http://www.opengis.net/kml/2.2"}).text = "0"
                
            animated_update_show = ET.SubElement(playlist, 'gx:AnimatedUpdate')
            update_show = ET.SubElement(animated_update_show, "Update")
            ET.SubElement(update_show, 'targetHref')
            change_show = ET.SubElement(update_show, "Change")
            screen_overlay_show = ET.SubElement(change_show, "ScreenOverlay", attrib={"targetId": text_image_overlay_id})
            ET.SubElement(screen_overlay_show, "visibility", attrib={"xmlns": "http://www.opengis.net/kml/2.2"}).text = "1"
            previous_text_image_overlay_id = text_image_overlay_id
            
        # Change camera position
        if i%update_camera_frequency == 0:
            flyto = ET.SubElement(playlist, 'gx:FlyTo')
            ET.SubElement(flyto, 'gx:duration').text = str(CAMERA_FLYTO_DURATION_IN_SECS)
            ET.SubElement(flyto, 'gx:flyToMode').text = 'smooth'
            lookat = ET.SubElement(flyto, 'LookAt')
            # Look ahead 20 points so the track tip stays visible
            look_ahead_index = min(i + 20, len(points) - 1)
            ET.SubElement(lookat, 'longitude').text = str(points[look_ahead_index]["longitude"])
            ET.SubElement(lookat, 'latitude').text = str(points[look_ahead_index]["latitude"])
            ET.SubElement(lookat, 'altitude').text = '0'
            ET.SubElement(lookat, 'heading').text = str(bearing)
            ET.SubElement(lookat, 'tilt').text = str(CAMERA_TILT_ANGLE)
            ET.SubElement(lookat, 'range').text = str(CAMERA_RANGE)
            ET.SubElement(lookat, 'altitudeMode').text = 'relativeToGround'

        # show the line segment
        update = ET.SubElement(playlist, 'gx:AnimatedUpdate')
        # This duration doesn't seem to have any effect when the tour is played
        # ET.SubElement(update, 'gx:duration').text = '5'
        update_tag = ET.SubElement(update, 'Update')
        ET.SubElement(update_tag, 'targetHref')
        change = ET.SubElement(update_tag, 'Change')
        placemark = ET.SubElement(change, 'Placemark', targetId=f'seg{i}')
        ET.SubElement(placemark, 'visibility').text = '1'

        # Change the position of the Hiker icon
        animated_update_show = ET.SubElement(playlist, 'gx:AnimatedUpdate')
        update_show = ET.SubElement(animated_update_show, "Update")
        ET.SubElement(update_show, 'targetHref')
        change_show = ET.SubElement(update_show, "Change")
        placemark_show = ET.SubElement(change_show, "Placemark", attrib={"targetId": "Hiker"})
        point = ET.SubElement(placemark_show, 'Point')
        ET.SubElement(point, 'coordinates').text = f"{lon},{lat},{elevation}"
        ET.SubElement(placemark_show, "visibility").text = "1"

        # Wait for a very short time.  Without this wait, the progressive line goes very, very fast
        wait_element = ET.SubElement(playlist, "gx:Wait")
        ET.SubElement(wait_element, "gx:duration").text = str(PAUSE_BETWEEN_LINE_SEGMENTS_IN_SECS)

        #
        # This is a hack to hide all way points on the ascent when the descent begins.
        # On the descent, we didnt stay in some of the places we stayed on the ascent
        # and hence better not show them.
        #
        if "descent" in track_name.lower():
            for j, waypoint in enumerate(gpx.waypoints):
                if j<=11:
                    animated_update_hide = ET.SubElement(playlist, 'gx:AnimatedUpdate')
                    update_hide = ET.SubElement(animated_update_hide, "Update")
                    ET.SubElement(update_hide, 'targetHref')
                    change_hide = ET.SubElement(update_hide, "Change")
                    placemark_hide = ET.SubElement(change_hide, "Placemark", attrib={"targetId": f'waypoint{j}'})
                    ET.SubElement(placemark_hide, "visibility").text = "0"
                else:
                    animated_update_show = ET.SubElement(playlist, 'gx:AnimatedUpdate')
                    update_show = ET.SubElement(animated_update_show, "Update")
                    ET.SubElement(update_show, 'targetHref')
                    change_show = ET.SubElement(update_show, "Change")
                    placemark_show = ET.SubElement(change_show, "Placemark", attrib={"targetId": f'waypoint{j}'})
                    ET.SubElement(placemark_show, "visibility").text = "1"


    # Add images taken after the timestamp of the last trackpoint
    while image_index < len(photo_images_info):
        img_base_name = os.path.splitext(os.path.basename(photo_images_info[image_index]["filename"]))[0]
        overlay_id = f"image_{img_base_name}"
                
        animated_update_show = ET.SubElement(playlist, 'gx:AnimatedUpdate')
        update_show = ET.SubElement(animated_update_show, "Update")
        ET.SubElement(update_show, 'targetHref')
        change_show = ET.SubElement(update_show, "Change")
        screen_overlay_show = ET.SubElement(change_show, "ScreenOverlay", attrib={"targetId": overlay_id})
        ET.SubElement(screen_overlay_show, "visibility", attrib={"xmlns": "http://www.opengis.net/kml/2.2"}).text = "1"

        wait_element = ET.SubElement(playlist, "gx:Wait")
        ET.SubElement(wait_element, "gx:duration").text = str(PHOTO_DURATION_TIME_IN_SECS)

        animated_update_hide = ET.SubElement(playlist, 'gx:AnimatedUpdate')
        update_hide = ET.SubElement(animated_update_hide, "Update")
        ET.SubElement(update_hide, 'targetHref')
        change_hide = ET.SubElement(update_hide, "Change")
        screen_overlay_hide = ET.SubElement(change_hide, "ScreenOverlay", attrib={"targetId": overlay_id})
        ET.SubElement(screen_overlay_hide, "visibility", attrib={"xmlns": "http://www.opengis.net/kml/2.2"}).text = "0"
            
        image_index += 1
 
    #
    # This is to wait at the end of the tour so a recorded video doesnt end abruptly
    #
    wait_element = ET.SubElement(playlist, "gx:Wait")
    ET.SubElement(wait_element, "gx:duration").text = "3"

    # Create image overlays (hidden initially - will be shown during the tour)
    for info in photo_images_info:
        image_overlay_element = create_photo_image_overlay_element(info)
        document.append(image_overlay_element)

    # Create and append a overlay for the title
    if os.path.exists(title_filepath):
        title_overlay = create_title_overlay_element(folder)
        document.append(title_overlay)
    
    total_distance = 0
    text_image_files = []

    # Create shared track line styles (one per unique color) to avoid duplicating
    # style definitions in every segment placemark.  KML color format is aabbggrr.
    unique_colors = set(p["color"] for p in points)
    for color in unique_colors:
        style = ET.SubElement(document, 'Style', id=f'track_style_{color}')
        line_style = ET.SubElement(style, 'LineStyle')
        ET.SubElement(line_style, 'color').text = 'ff' + str(color)
        ET.SubElement(line_style, 'width').text = '6'

    # Add the line segments and the text images (hidden initially - will be shown during the tour)
    # to the kml doc
    for i in range(len(points) - 1):

        placemark = ET.SubElement(document, 'Placemark', id=f'seg{i}')
        ET.SubElement(placemark, 'styleUrl').text = f'#track_style_{points[i]["color"]}'
        ET.SubElement(placemark, 'visibility').text = '0'
        linestring = ET.SubElement(placemark, 'LineString')
        ET.SubElement(linestring, 'tessellate').text = '1'
        coords = f"{points[i]["longitude"]},{points[i]["latitude"]},{points[i]["elevation"]} {points[i+1]["longitude"]},{points[i+1]["latitude"]},{points[i+1]["elevation"]}"
        ET.SubElement(linestring, 'coordinates').text = coords

        distance = calculate_distance(points[i]["latitude"], points[i]["longitude"], points[i+1]["latitude"], points[i+1]["longitude"])
        total_distance += distance/1000

        #
        # Create transparent png images every 10 trackpoints that show the details of the current segment, the distance
        # covered so far, the current altitude and the time.
        #        
        if i==0 or i%10 == 0:
            text_image_file_name = os.path.join(folder, "text_img_" + str(i) + ".png")
            text_image_files.append(text_image_file_name)
        
            time_str = convert_to_local_time_string(points[i]["time"])
            
            # A small hack to show the distance as 0km initially
            if (i==0):        
                create_text_image_png(f"{points[i]["name"]}", f"0km    {int(round(points[i]["elevation"]))}m    {time_str}", text_image_file_name)
            else:
                create_text_image_png(f"{points[i]["name"]}", f"{total_distance:0.2f}km    {int(round(points[i]["elevation"]))}m    {time_str}", text_image_file_name)
                
            text_image_base_name = os.path.splitext(os.path.basename(text_image_file_name))[0]
            text_image_overlay_id = f"image_{text_image_base_name}"
            text_image_overlay_element = create_text_image_overlay_element(text_image_file_name, text_image_overlay_id)
            document.append(text_image_overlay_element)

    #
    # Add icons for waypoints as 'styles'.  The icon names are auto-discovered
    # from the waypoint <sym> tags in the GPX file, plus "Hiker" is always included.
    # Icon files are looked up first in the script's folder, then in the GPX/images
    # folder.  If an icon is not found in either location, the script exits with an error.
    # The waypoint placemarks are added with the relevant style later.  So that when
    # these waypoints are shown during the tour, the appropriate icon is displayed
    # instead of just a pin.
    #
    icon_names = {"Hiker"}
    for waypoint in gpx.waypoints:
        if waypoint.symbol:
            icon_names.add(waypoint.symbol)
    icon_names = sorted(icon_names)

    # Resolve each icon to its actual file path (script folder first, then GPX folder)
    icon_paths = {}
    for icon_name in icon_names:
        script_path = os.path.join(script_folder, icon_name + ".png")
        folder_path = os.path.join(folder, icon_name + ".png")
        if os.path.exists(script_path):
            icon_paths[icon_name] = script_path
        elif os.path.exists(folder_path):
            icon_paths[icon_name] = folder_path
        else:
            print(f"Error: Icon file '{icon_name}.png' not found in either:")
            print(f"  Script folder: {script_folder}")
            print(f"  GPX/images folder: {folder}")
            sys.exit(1)

    for icon_name in icon_names:
        style = ET.SubElement(document, 'Style', id=f"{icon_name}Style")
        icon_style = ET.SubElement(style, 'IconStyle')
        icon = ET.SubElement(icon_style, 'Icon')
        ET.SubElement(icon, "href").text = icon_name + ".png"

        label_style = ET.SubElement(style, 'LabelStyle')
        if icon_name == "Hiker":
            ET.SubElement(icon_style, 'scale').text = '2'
            ET.SubElement(label_style, 'scale').text = '0'
        else:
            ET.SubElement(icon_style, 'scale').text = '4'
            ET.SubElement(label_style, 'scale').text = '2'

    #
    # Add a placemark for a hiker icon.  This is shown at the leading edge of the
    # progressive line.  Its position is updated regularly when the line extends.
    #
    placemark = ET.SubElement(document, 'Placemark', id='Hiker')
    ET.SubElement(placemark, 'styleUrl').text = "#HikerStyle"
    point = ET.SubElement(placemark, 'Point')
    ET.SubElement(point, 'coordinates').text = f"{points[0]["longitude"]},{points[0]["latitude"]},{points[0]["elevation"]}"  #lon,lat,ele
    ET.SubElement(placemark, "visibility").text = "0"

    #
    # Add the waypoints as placemarks with the appropriate style.
    #
    for i, waypoint in enumerate(gpx.waypoints):
        placemark = ET.SubElement(document, 'Placemark', id=f'waypoint{i}')
        ET.SubElement(placemark, 'name').text = waypoint.name if waypoint.name else "Waypoint"
        point = ET.SubElement(placemark, 'Point')
        ET.SubElement(point, 'coordinates').text = f"{waypoint.longitude},{waypoint.latitude},{waypoint.elevation or 0}"  #lon,lat,ele

        if waypoint.description:
            ET.SubElement(placemark, 'description').text = waypoint.description   
            
        ET.SubElement(placemark, 'styleUrl').text = f"#{waypoint.symbol}Style"
        ET.SubElement(placemark, "visibility").text = "0"

    # Create the KML file
    tree = ET.ElementTree(doc)
    ET.indent(tree, space="  ", level=0)
    kml_output = os.path.join(folder, gpx_file_name + ".kml")
    tree.write(kml_output, encoding='utf-8', xml_declaration=True)

    # Create the KMZ
    output_kmz_path = os.path.join(folder, "combined.kmz")
    print(f"Combining the KML file along with the images and creating KMZ file - {output_kmz_path}...")

    with zipfile.ZipFile(output_kmz_path, 'w', zipfile.ZIP_DEFLATED) as kmz_file:
        kmz_file.write(kml_output, gpx_file_name + ".kml")
        
        if os.path.exists(title_filepath):
            kmz_file.write(title_filepath, "Title.png")
        else:
            print(f"Title image file {title_filepath} doesn't exist.")
        
        for info in photo_images_info:
            kmz_file.write(info["filepath"], os.path.basename(info["filepath"]))
            
        for img_file in text_image_files:
            kmz_file.write(img_file, os.path.basename(img_file))
            
        for icon_name in icon_names:
            kmz_file.write(icon_paths[icon_name], icon_name + ".png")

    # Clean up temporary text image files
    for img_file in text_image_files:
        if os.path.exists(img_file):
            os.remove(img_file)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]
    if not os.path.isdir(folder_path):
        print(f"Invalid folder: {folder_path}")
        sys.exit(1)

    create_kmz_from_gpx_and_photos(folder_path)
