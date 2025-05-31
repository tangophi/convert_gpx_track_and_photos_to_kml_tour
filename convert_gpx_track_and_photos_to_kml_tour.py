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
#   that should also be present in the folder.  These  should be named as Hiker.png, Bridge.png,
#   Hotel.png, Restaurant.png and Summit.png.  These icons are displayed for a waypoint defined
#   like the above in the gpx track.
#   - If there are other types of waypoints in the gpx track, then download relevant icons and
#     save them as the same name displayed in <sym> field.
# - Also a transparent Title.png should be present.  This is used as the title of the tour/video.
# - Several python modules need to be installed before the script can be run.  Just run the script,
#   the script will throw an error listing the missing package - install them
#
#
# ChatGPT and Google Gemini helped a lot in creating this script !!!
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
import glob
import zipfile
import svgwrite
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import datetime
import pytz


#
# Change this to the proper offset based on where the gpx track was recorded and the photos taken
#
LOCAL_TIME_OFFSET_FROM_UTC = timedelta(hours=5, minutes=45)

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
CAMERA_RANGE=1000







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
    #ET.SubElement(screen_overlay, "overlayXY", x="0.5", y="0.5", xunits="fraction", yunits="fraction")
    #ET.SubElement(screen_overlay, "screenXY", x="0.5", y="0.5", xunits="fraction", yunits="fraction")

    ET.SubElement(screen_overlay, "overlayXY", x="0", y="1", xunits="fraction", yunits="fraction")
    ET.SubElement(screen_overlay, "screenXY", x="0", y="1", xunits="fraction", yunits="fraction")
    
    #
    # If the image aspect ration is >= the usual screen aspect ratio, then fit the width of the image
    # to 80% of screen width while maintaining the aspect ratio.  Otherwise, fit the height of the image
    # to 80% of screen height while maintaing the aspect ratio.
    #
    if info["width"]/info["height"] >= 16/9:
        #ET.SubElement(screen_overlay, "size", x="0.8", y="0", xunits="fraction", yunits="fraction")
        ET.SubElement(screen_overlay, "size", x="0.9", y="0", xunits="fraction", yunits="fraction")
    else:
        #ET.SubElement(screen_overlay, "size", x="0", y="0.8", xunits="fraction", yunits="fraction")
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
    
    #ET.SubElement(screen_overlay, 'color').text = 'ffffffff'
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
# This function create a transparent png image for each trackpoint.  The image will contain
# details of the track name, distance from the start, altitude and the time.  These images
# will be shown one by one during the tour.
#    
#def create_text_image_png(text1, text2, text3, text4, filename):
def create_text_image_png(text1, text2, filename):
    width, height = 1600, 300
    font_size = 40
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Update if needed

#    texts = [text1, text2, text3, text4]
    texts = [text1, text2]
    line_spacing = 60
#    base_y = 80
    base_y = 180

    # Load font
    font = ImageFont.truetype(font_path, font_size)

    # --- STROKE VERSION ---
    #img_stroke = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    #draw_stroke = ImageDraw.Draw(img_stroke)

    #for i, txt in enumerate(texts):
    #    y = base_y + i * line_spacing
    #    x = 50
    #    # Draw stroke (outline)
    #    for dx in [-2, 0, 2]:
    #        for dy in [-2, 0, 2]:
    #            if dx != 0 or dy != 0:
    #                draw_stroke.text((x + dx, y + dy), txt, font=font, fill="black")
    #    # Draw fill
    #    draw_stroke.text((x, y), txt, font=font, fill="white")

    #img_stroke.save(f"{filename}-stroke.png")

    # --- SHADOW VERSION ---
    img_shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_shadow = ImageDraw.Draw(img_shadow)

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

    #for info in photo_images_info:
    #    print(f'filename: {info["filename"]}')

      
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
    #ET.SubElement(lookat, 'heading').text = '0'
    ET.SubElement(lookat, 'tilt').text = '0'
    #ET.SubElement(lookat, 'tilt').text = '0'
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
    #ET.SubElement(lookat, 'heading').text = '0'
    ET.SubElement(lookat, 'tilt').text = '0'
    #ET.SubElement(lookat, 'tilt').text = '0'
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
        change_hide = ET.SubElement(update_hide, "Change")
        screen_overlay_hide = ET.SubElement(change_hide, "ScreenOverlay", attrib={"targetId": "title_overlay"})
        ET.SubElement(screen_overlay_hide, "visibility", attrib={"xmlns":"http://www.opengis.net/kml/2.2"}).text = "0"        

    # Show all the waypoints encountered only on the ascent at the beginning of the tour
    for i, waypoint in enumerate(gpx.waypoints):
        animated_update_show = ET.SubElement(playlist, 'gx:AnimatedUpdate')
        update_show = ET.SubElement(animated_update_show, "Update")
        ET.SubElement(update_show, 'targetHref')
        change_show = ET.SubElement(update_show, "Change")
        placemark_show = ET.SubElement(change_show, "Placemark", attrib={"targetId": f'waypoint{i}'})
        ET.SubElement(placemark_show, "visibility").text = "1"

        #
        # There were only 13 way points on the ascent.
        #
        if i==12:
            break

    # Change camera position every this number of points 
    update_camera_frequency = 100

    image_index = 0
    previous_text_image_overlay_id = ""
    
    #    
    # Create animated elements
    # - Show all the photos between the previous trackpoint and the current trackpoint, each for 2 seconds
    # - Change the camera position
    # - Show a line between the current trackpoint and the next trackpoint
    # - Show the transparent png that has details of the track name, distance, elevation and time.  Before
    #   that hide the previous such image.
    #
    for i in range(len(points) - 1):
        # lon, lat, elevation, color, time, track_name = points[i]
        lon, lat, elevation, color, time, track_name = (
            points[i]["longitude"],
            points[i]["latitude"],
            points[i]["elevation"],
            points[i]["color"],
            points[i]["time"],
            points[i]["name"]
        )
       
        bearing = calculate_bearing(points, i, 50)
        #print(f"image_index: {image_index}   len:{len(photo_images_info)}   photo_time:{photo_images_info[image_index]["timestamp"]}   time:{time}")
    
        # Show all photos before the current trackpoint apart from the ones already shown.
        # This also ensures that all the photos taken before the tracking had begun will be
        # shown initially.        
        while image_index < len(photo_images_info) and photo_images_info[image_index]["timestamp"] < time:
            img_base_name = os.path.splitext(os.path.basename(photo_images_info[image_index]["filename"]))[0]
            overlay_id = f"image_{img_base_name}"
                
            animated_update_show = ET.SubElement(playlist, 'gx:AnimatedUpdate')
            update_show = ET.SubElement(animated_update_show, "Update")
            change_show = ET.SubElement(update_show, "Change")
            screen_overlay_show = ET.SubElement(change_show, "ScreenOverlay", attrib={"targetId": overlay_id})
            ET.SubElement(screen_overlay_show, "visibility", attrib={"xmlns": "http://www.opengis.net/kml/2.2"}).text = "1"

            wait_element = ET.SubElement(playlist, "gx:Wait")
            ET.SubElement(wait_element, "gx:duration").text = str(PHOTO_DURATION_TIME_IN_SECS)

            animated_update_hide = ET.SubElement(playlist, 'gx:AnimatedUpdate')
            update_hide = ET.SubElement(animated_update_hide, "Update")
            change_hide = ET.SubElement(update_hide, "Change")
            screen_overlay_hide = ET.SubElement(change_hide, "ScreenOverlay", attrib={"targetId": overlay_id})
            ET.SubElement(screen_overlay_hide, "visibility", attrib={"xmlns": "http://www.opengis.net/kml/2.2"}).text = "0"
            
            image_index += 1                    

        # Show the transparent png image that has the following details.
        # The name of the segment, distance travelled so far, current altitue and current time.
        if i==0 or i%10 == 0:
            text_image_file_name = os.path.join(folder, "text_img_" + str(i))
            text_image_base_name = os.path.splitext(os.path.basename(text_image_file_name))[0]
            text_image_overlay_id = f"image_{text_image_base_name}"

            # first hide the previous text image overlay
            if previous_text_image_overlay_id != "":
                animated_update_hide = ET.SubElement(playlist, 'gx:AnimatedUpdate')
                update_hide = ET.SubElement(animated_update_hide, "Update")
                change_hide = ET.SubElement(update_hide, "Change")
                screen_overlay_hide = ET.SubElement(change_hide, "ScreenOverlay", attrib={"targetId": previous_text_image_overlay_id})
                ET.SubElement(screen_overlay_hide, "visibility", attrib={"xmlns": "http://www.opengis.net/kml/2.2"}).text = "0"
                
            animated_update_show = ET.SubElement(playlist, 'gx:AnimatedUpdate')
            update_show = ET.SubElement(animated_update_show, "Update")
            change_show = ET.SubElement(update_show, "Change")
            screen_overlay_show = ET.SubElement(change_show, "ScreenOverlay", attrib={"targetId": text_image_overlay_id})
            ET.SubElement(screen_overlay_show, "visibility", attrib={"xmlns": "http://www.opengis.net/kml/2.2"}).text = "1"
            previous_text_image_overlay_id = text_image_overlay_id
            
        # Change camera position
        if i%update_camera_frequency == 0:
            flyto = ET.SubElement(playlist, 'gx:FlyTo')
            ET.SubElement(flyto, 'gx:duration').text = '.3'
            ET.SubElement(flyto, 'gx:flyToMode').text = 'smooth'
            lookat = ET.SubElement(flyto, 'LookAt')
            ET.SubElement(lookat, 'longitude').text = str(lon)
            ET.SubElement(lookat, 'latitude').text = str(lat)
            ET.SubElement(lookat, 'altitude').text = '0'
            ET.SubElement(lookat, 'heading').text = str(bearing)
            #ET.SubElement(lookat, 'heading').text = '0'
            ET.SubElement(lookat, 'tilt').text = str(CAMERA_TILT_ANGLE)
            #ET.SubElement(lookat, 'tilt').text = '0'
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
        #ET.SubElement(placemark, 'styleUrl').text = f'#{style_id}'  # Use the new style ID
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
        if "descent".lower() in track_name.lower():
            for i, waypoint in enumerate(gpx.waypoints):
                if i<=11:
                    animated_update_hide = ET.SubElement(playlist, 'gx:AnimatedUpdate')
                    update_hide = ET.SubElement(animated_update_hide, "Update")
                    change_hide = ET.SubElement(update_hide, "Change")
                    placemark_hide = ET.SubElement(change_hide, "Placemark", attrib={"targetId": f'waypoint{i}'})
                    ET.SubElement(placemark_hide, "visibility").text = "0"
                else:
                    animated_update_show = ET.SubElement(playlist, 'gx:AnimatedUpdate')
                    update_show = ET.SubElement(animated_update_show, "Update")
                    change_show = ET.SubElement(update_show, "Change")
                    placemark_show = ET.SubElement(change_show, "Placemark", attrib={"targetId": f'waypoint{i}'})
                    ET.SubElement(placemark_show, "visibility").text = "1"


    # Add images taken after the timestamp of the last trackpoint
    while image_index < len(photo_images_info):
        img_base_name = os.path.splitext(os.path.basename(photo_images_info[image_index]["filename"]))[0]
        overlay_id = f"image_{img_base_name}"
                
        animated_update_show = ET.SubElement(playlist, 'gx:AnimatedUpdate')
        update_show = ET.SubElement(animated_update_show, "Update")
        change_show = ET.SubElement(update_show, "Change")
        screen_overlay_show = ET.SubElement(change_show, "ScreenOverlay", attrib={"targetId": overlay_id})
        ET.SubElement(screen_overlay_show, "visibility", attrib={"xmlns": "http://www.opengis.net/kml/2.2"}).text = "1"

        wait_element = ET.SubElement(playlist, "gx:Wait")
        ET.SubElement(wait_element, "gx:duration").text = str(PHOTO_DURATION_TIME_IN_SECS)

        animated_update_hide = ET.SubElement(playlist, 'gx:AnimatedUpdate')
        update_hide = ET.SubElement(animated_update_hide, "Update")
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
    
    # Add the line segments and the text images (hidden initially - will be shown during the tour)
    # to the kml doc
    for i in range(len(points) - 1):
      
        placemark = ET.SubElement(document, 'Placemark', id=f'seg{i}')

        #ET.SubElement(placemark, 'styleUrl').text = '#yellowLine'
        style_id = f'track_style_{points[i]["color"]}'  # Unique style ID
        style = ET.SubElement(placemark, 'Style', id=style_id)
        line_style = ET.SubElement(style, 'LineStyle')
        ET.SubElement(line_style, 'color').text = 'ff' + str(points[i]["color"])  # KML color format is aabbggrr
        ET.SubElement(line_style, 'width').text = '6'

        ET.SubElement(placemark, 'visibility').text = '0'
        linestring = ET.SubElement(placemark, 'LineString')
        ET.SubElement(linestring, 'tessellate').text = '1'
        coords = f"{points[i]["longitude"]},{points[i]["latitude"]},{points[i]["elevation"]} {points[i+1]["longitude"]},{points[i+1]["latitude"]},{points[i+1]["elevation"]}"
        ET.SubElement(linestring, 'coordinates').text = coords

        distance = calculate_distance(points[i]["latitude"], points[i]["longitude"], points[i+1]["latitude"], points[i+1]["longitude"])
        total_distance += distance/1000
        #print(f"count: {i} Distance between point {i} and {i+1}: {distance:.2f} meters")

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
                create_text_image_png(f"{points[i]["name"]}", f"0km    {points[i]["elevation"]}m    {time_str}", text_image_file_name)
            else:
                create_text_image_png(f"{points[i]["name"]}", f"{total_distance:0.2f}km    {points[i]["elevation"]}m    {time_str}", text_image_file_name)
                
            text_image_base_name = os.path.splitext(os.path.basename(text_image_file_name))[0]
            text_image_overlay_id = f"image_{text_image_base_name}"
            text_image_overlay_element = create_text_image_overlay_element(text_image_file_name, text_image_overlay_id)
            # text_image_overlays_elements.append(text_image_overlay_element)
            document.append(text_image_overlay_element)


    

    #
    # Add icons for waypoints as 'styles'.  And the waypoint placemarks are
    # added with the relevant style later.  So that when these waypoints are
    # shown during the tour, the appropriate icon is displayed instead of just
    # a pin.
    #
    icon_names = ["Hiker", "Heliport", "Hotel", "Restaurant", "Summit", "Bridge", "Airport"]
    for icon_name in icon_names:
        icon_image_filepath = os.path.join(folder, icon_name + ".png")
        
        style = ET.SubElement(document, 'Style', id=f"{icon_name}Style")
        icon_style = ET.SubElement(style, 'IconStyle')
        icon = ET.SubElement(icon_style, 'Icon')
        
        if os.path.exists(icon_image_filepath):
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
    #ET.SubElement(placemark, 'name').text = "Hiker"
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
    #print(f"kml_output: {kml_output} tree: {tree}")
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
            #print(f"Including {os.path.basename(info["filepath"])} inside KMZ file...")
            kmz_file.write(info["filepath"], os.path.basename(info["filepath"]))
            
        for img_file in text_image_files:
            kmz_file.write(img_file, os.path.basename(img_file))
            
        for icon_name in icon_names:
            icon_image_filepath = os.path.join(folder, icon_name + ".png")
            if os.path.exists(icon_image_filepath):
                kmz_file.write(icon_image_filepath, os.path.basename(icon_image_filepath))
            else:
                print(f"Icon image file {icon_image_filepath} doesn't exist.")
            
    
    
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_kmz.py <folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]
    if not os.path.isdir(folder_path):
        print(f"Invalid folder: {folder_path}")
        sys.exit(1)

    create_kmz_from_gpx_and_photos(folder_path)
