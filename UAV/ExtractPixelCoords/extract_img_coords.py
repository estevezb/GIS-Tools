"""
========================================================================================
    Image Pixel Coordinate Extraction Application for UAV Ground Control Point Workflows
========================================================================================
    A GUI application that allows manual marking of the positions of Ground Control Points
    within photos. Use this to create pixel coordinates for open drone map (ODM) gcp inputs.

    REQUIREMENTS: 
        - python-enabled environment and associated packages (pandas, open cv, easygui)
        - CSV file input populated with ground control point file names (e.g., image_name = DJI_0001) and corresponding GCP labels (e.g., 'GCP Label = POINT_01)
        - Image folder with drone photos containing ground control points 

    EXAMPLE INPUT CSV DATA FORMAT:
    ------------------------------
    Easting	    Northing	    Elevation   image_name	  GCP Label
    472946.1849 4953066.3993	243.503	    DJI_0104	  POINT_01

    EXAMPLE OUTPUT CSV FORMAT :
    ---------------------------
    Easting	    Northing	    Elevation   x	    y       image_name	    GCP Label
    472946.1849	4953066.3993	243.503	    1196	182	    DJI_0104.JPG	POINT_01

 """



import cv2
import os
import pandas as pd
import easygui

# Initialize variables
coordinates_dict = {}  # Stores latest clicks per (gcp_label, image)
image_list = []
current_index = 0
current_gcp_label = None  # User-selected GCP label

# Add these globals at the top
zoom_level = 1
zoom_center = None
WINDOW_W, WINDOW_H = 900, 600  # Set desired window size
SCALE_FACTOR = 0.25  # Display images at 1/4 size

def get_gcp_pairs_from_csv(gcp_input_df, image_list):
    gcp_label_col = gcp_input_df.attrs.get('gcp_label_col', None)
    if gcp_label_col is None:
        raise ValueError("No GCP label column specified in input CSV.")
    # If a Filename column exists, use it, else assign all GCPs to all images
    filename_col = None
    for col in gcp_input_df.columns:
        if col.strip().lower() == 'filename':
            filename_col = col
            break
    gcp_input_df.attrs['filename_col'] = filename_col
    pairs = []
    if filename_col:
        for _, row in gcp_input_df.iterrows():
            gcp_label = row[gcp_label_col]
            fname = row[filename_col]
            if pd.notna(gcp_label) and pd.notna(fname) and fname in image_list:
                pairs.append((fname, gcp_label))
    else:
        gcp_labels = list(gcp_input_df[gcp_label_col].dropna().unique())
        for fname in image_list:
            for gcp_label in gcp_labels:
                pairs.append((fname, gcp_label))
    return pairs

# Get folder path from user using easygui
def get_image_folder():
    folder = easygui.diropenbox(title="Select the folder containing images")
    if not folder:
        print("No folder selected. Exiting.")
        exit()
    return folder

folder_path = get_image_folder()

# Load all images from the folder
if os.path.exists(folder_path):
    image_list = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
else:
    print("Invalid folder path. Exiting.")
    exit()

# Add variables to track mouse position and clicked position
mouse_x, mouse_y = -1, -1
clicked_pos = {}

# Prompt for optional GCP CSV file (move this before any OpenCV or input() calls)
def prompt_for_gcp_csv():
    gcp_csv_path = easygui.fileopenbox(title="Select GCP CSV file (optional)", filetypes=["*.csv"])
    if gcp_csv_path:
        print(f"Loaded GCP input data from {gcp_csv_path}")
        df = pd.read_csv(gcp_csv_path)
        # Prompt for GCP label column name, showing available columns
        print("Available columns in CSV:")
        for col in df.columns:
            print(f"  - {col}")
        gcp_label_col = None
        for col in df.columns:
            if col.strip().lower() == 'gcp label':
                gcp_label_col = col
                break
        if not gcp_label_col:
            gcp_label_col = input("Enter the column name to use for GCP labels (see above): ").strip()
            if gcp_label_col not in df.columns:
                print(f"Column '{gcp_label_col}' not found. Proceeding without GCP label tracking.")
                return df  # Return anyway for fallback
        df.attrs['gcp_label_col'] = gcp_label_col
        return df
    else:
        print("No GCP CSV file selected. Proceeding without input merge.")
        return None
print("A file dialog will open. Please select your GCP CSV file or cancel to skip.")
gcp_input_df = prompt_for_gcp_csv()

# Build marking queue: list of (filename, gcp_label) pairs to mark
if gcp_input_df is not None:
    try:
        marking_queue = get_gcp_pairs_from_csv(gcp_input_df, image_list)
    except Exception as e:
        print(str(e))
        marking_queue = []
else:
    # If no CSV, just mark each image once with a dummy label
    marking_queue = [(fname, "GCP1") for fname in image_list]

current_marking_idx = 0  # Index in marking_queue

def get_pixel_coordinates(event, x, y, flags, param):
    global mouse_x, mouse_y, current_gcp_label, zoom_level, zoom_center
    filename = image_list[current_index]
    img_path = os.path.join(folder_path, filename)
    image = cv2.imread(img_path)
    h, w = image.shape[:2]
    # Always use the same display size for mapping
    disp_w = int(w * SCALE_FACTOR)
    disp_h = int(h * SCALE_FACTOR)
    if zoom_level > 1 and zoom_center is not None:
        zx, zy = zoom_center
        zh, zw = h // zoom_level, w // zoom_level
        x1 = max(zx - zw // 2, 0)
        y1 = max(zy - zh // 2, 0)
        x2 = min(x1 + zw, w)
        y2 = min(y1 + zh, h)
        crop_w, crop_h = x2 - x1, y2 - y1
        scale_x = disp_w / crop_w
        scale_y = disp_h / crop_h
        # Mouse coordinates map to crop, then to image
        img_x = int(x1 + min(max(int(x / scale_x), 0), crop_w - 1))
        img_y = int(y1 + min(max(int(y / scale_y), 0), crop_h - 1))
    else:
        x1, y1 = 0, 0
        x2, y2 = w, h
        scale_x = SCALE_FACTOR
        scale_y = SCALE_FACTOR
        img_x = min(max(int(x / scale_x), 0), w - 1)
        img_y = min(max(int(y / scale_y), 0), h - 1)
    mouse_x, mouse_y = img_x, img_y
    if event == cv2.EVENT_LBUTTONDOWN:
        if flags & cv2.EVENT_FLAG_CTRLKEY:
            zoom_level = min(zoom_level * 2, 8)  # Max 8x zoom
            zoom_center = (img_x, img_y)
            display_image()
            return
        if not current_gcp_label:
            print("No GCP Label selected. Press 'f' and enter a GCP Label before marking.")
            return
        coordinates_dict[(current_gcp_label, filename)] = (img_x, img_y)
        clicked_pos[(current_gcp_label, filename)] = (img_x, img_y)
        print(f"Updated {filename} [{current_gcp_label}]: {img_x}, {img_y}")
        display_image()  # Redraw to show permanent cross

def draw_cross(img, x, y, color=(255, 0, 0), size=6, thickness=2):
    # x, y are in display (resized) coordinates
    cv2.line(img, (x - size, y), (x + size, y), color, thickness)
    cv2.line(img, (x, y - size), (x, y + size), color, thickness)

def display_image():
    global current_index, mouse_x, mouse_y, current_gcp_label, zoom_level, zoom_center
    filename = image_list[current_index]
    img_path = os.path.join(folder_path, filename)
    image = cv2.imread(img_path)
    h, w = image.shape[:2]
    # Always display at fixed display size (full image at SCALE_FACTOR)
    disp_w = int(w * SCALE_FACTOR)
    disp_h = int(h * SCALE_FACTOR)
    # Only apply zoom if zoom_level > 1 and zoom_center is set
    if zoom_level > 1 and zoom_center is not None:
        zx, zy = zoom_center
        zh, zw = h // zoom_level, w // zoom_level
        x1 = max(zx - zw // 2, 0)
        y1 = max(zy - zh // 2, 0)
        x2 = min(x1 + zw, w)
        y2 = min(y1 + zh, h)
        image_disp = image[y1:y2, x1:x2].copy()
        # Resize the crop to the fixed display size
        image_disp_resized = cv2.resize(image_disp, (disp_w, disp_h), interpolation=cv2.INTER_AREA)
        crop_offset = (x1, y1)
        crop_w, crop_h = x2 - x1, y2 - y1
        scale_x = disp_w / crop_w
        scale_y = disp_h / crop_h
    else:
        x1, y1 = 0, 0
        x2, y2 = w, h
        image_disp = image.copy()
        image_disp_resized = cv2.resize(image_disp, (disp_w, disp_h), interpolation=cv2.INTER_AREA)
        crop_offset = (0, 0)
        scale_x = SCALE_FACTOR
        scale_y = SCALE_FACTOR
    # Draw permanent crosses for all GCPs marked for the current GCP label (across all images)
    if current_gcp_label is not None:
        for (gcp, fname), (cx, cy) in clicked_pos.items():
            if gcp == current_gcp_label and x1 <= cx < x2 and y1 <= cy < y2:
                # Draw at scaled position
                draw_cross(image_disp_resized, int((cx - x1) * scale_x), int((cy - y1) * scale_y), color=(255, 0, 0), size=6, thickness=2)
    # Draw temporary cross at mouse position (if visible)
    if x1 <= mouse_x < x2 and y1 <= mouse_y < y2:
        draw_cross(image_disp_resized, int((mouse_x - x1) * scale_x), int((mouse_y - y1) * scale_y), color=(0, 0, 255), size=6, thickness=1)
    # Display filename at the top left
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0 * scale_x + 0.2  # Adjust font size for smaller image
    font_thickness = max(1, int(2 * scale_x + 0.5))
    text_color = (255, 255, 255)
    bg_color = (0, 0, 0)
    text = f"{filename}"
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, font_thickness)
    cv2.rectangle(image_disp_resized, (5, 5), (10 + tw, 10 + th), bg_color, -1)
    cv2.putText(image_disp_resized, text, (10, 10 + th - 5), font, font_scale, text_color, font_thickness, cv2.LINE_AA)
    # Display running GCP count for current label (unique images marked for this label)
    if current_gcp_label is not None:
        unique_imgs = set(fname for (gcp, fname) in clicked_pos if gcp == current_gcp_label)
        gcp_count = len(unique_imgs)
        gcp_text = f"Images marked for '{current_gcp_label}': {gcp_count}"
    else:
        gcp_text = "No GCP label selected."
    (gw, gh), _ = cv2.getTextSize(gcp_text, font, 0.8 * scale_x + 0.1, font_thickness)
    cv2.rectangle(image_disp_resized, (5, disp_h - 10 - gh), (10 + gw, disp_h - 5), bg_color, -1)
    cv2.putText(image_disp_resized, gcp_text, (10, disp_h - 10), font, 0.8 * scale_x + 0.1, text_color, font_thickness, cv2.LINE_AA)
    # Display directions at the bottom right
    directions_lines = [
        "Directions:",
        "Press 'f' to select GCP label.",
        "Left-click to mark for current label.",
        "Ctrl+Left-click to zoom in.",
        "Press 'r' to reset zoom.",
        "When completed hit e to export data. Hit q to quit"
    ]
    dir_font_scale = 0.7 * scale_x + 0.1
    dir_color = (0, 255, 255)
    dir_sizes = [cv2.getTextSize(line, font, dir_font_scale, font_thickness)[0] for line in directions_lines]
    dir_width = max(w for w, h in dir_sizes)
    dir_line_height = max(h for w, h in dir_sizes) + 6
    total_dir_height = dir_line_height * len(directions_lines)
    dx = disp_w - dir_width - 15
    dy = disp_h - total_dir_height - 15
    cv2.rectangle(image_disp_resized, (dx - 5, dy - 5), (dx + dir_width + 5, dy + total_dir_height + 5), bg_color, -1)
    for i, line in enumerate(directions_lines):
        y = dy + dir_line_height * (i + 1) - 3
        cv2.putText(image_disp_resized, line, (dx, y), font, dir_font_scale, dir_color, font_thickness, cv2.LINE_AA)
    # Display user controls at top right
    controls = [
        "Controls:",
        "f: Select GCP label",
        "n: Next image",
        "s: Search filename",
        "e: Export CSV",
        "q: Quit",
        "r: Reset zoom"
    ]
    ctrl_font_scale = 0.8 * scale_x + 0.1
    ctrl_color = (0, 255, 0)
    y_offset = 10
    for i, ctrl in enumerate(controls):
        (cw, ch), _ = cv2.getTextSize(ctrl, font, ctrl_font_scale, font_thickness)
        x = disp_w - cw - 10
        y = y_offset + (ch + 5) * (i + 1)
        cv2.putText(image_disp_resized, ctrl, (x, y), font, ctrl_font_scale, ctrl_color, font_thickness, cv2.LINE_AA)
    # Show current GCP label at the top center
    if current_gcp_label:
        gcp_label_text = f"Current GCP Label: {current_gcp_label}"
        (lw, lh), _ = cv2.getTextSize(gcp_label_text, font, 0.9 * scale_x + 0.1, font_thickness)
        lx = max(0, (disp_w - lw) // 2)
        ly = 30
        cv2.rectangle(image_disp_resized, (lx - 5, ly - lh - 5), (lx + lw + 5, ly + 5), bg_color, -1)
        cv2.putText(image_disp_resized, gcp_label_text, (lx, ly), font, 0.9 * scale_x + 0.1, (0, 255, 255), font_thickness, cv2.LINE_AA)
    cv2.imshow("Image Viewer", image_disp_resized)
    cv2.setMouseCallback("Image Viewer", get_pixel_coordinates)

def export_coordinates():
    # For each GCP label, require it is marked on more than 1 image
    from collections import Counter
    label_image_counter = Counter()
    for (g, f) in coordinates_dict.keys():
        label_image_counter[g] += 1
    single_image_labels = [g for g, count in label_image_counter.items() if count <= 1]
    if single_image_labels:
        print("The following GCP labels are marked on only one image. Each GCP label must be marked on more than one image before export:")
        for g in single_image_labels:
            print(f"  - {g}")
        print("Please mark each GCP label on at least two images.")
        return
    if gcp_input_df is not None:
        gcp_df = gcp_input_df.copy()
        gcp_label_col = gcp_input_df.attrs.get('gcp_label_col', None)
        if gcp_label_col is None:
            print("No GCP label column specified in input CSV.")
            print(f"Available columns: {list(gcp_df.columns)}")
            print("Exporting only pixel coordinates.")
            df = pd.DataFrame([
                (g, f, x, y) for (g, f), (x, y) in coordinates_dict.items()
            ], columns=[gcp_label_col or "GCP Label", "Filename", "X", "Y"])
            df.to_csv("pixel_coordinates.csv", index=False)
            print("Final coordinates saved to pixel_coordinates.csv")
            return
        filename_col = gcp_input_df.attrs.get('filename_col', None)
        # If a Filename column exists, merge on both, else merge on GCP label and all images
        if filename_col:
            all_pairs = pd.DataFrame([
                (row[gcp_label_col], row[filename_col]) for _, row in gcp_df.iterrows() if row[filename_col] in image_list
            ], columns=[gcp_label_col, filename_col])
        else:
            all_pairs = pd.DataFrame([
                (gcp_label, fname) for gcp_label in gcp_df[gcp_label_col].unique() for fname in image_list
            ], columns=[gcp_label_col, "Filename"])
        # Merge with input GCP data (on GCP label and filename if present)
        if filename_col:
            merged = pd.merge(all_pairs, gcp_df, on=[gcp_label_col, filename_col], how="left")
        else:
            merged = pd.merge(all_pairs, gcp_df, on=[gcp_label_col], how="left")
        # Merge with marked coordinates (on GCP label and filename)
        coords_df = pd.DataFrame([
            (g, f, x, y) for (g, f), (x, y) in coordinates_dict.items()
        ], columns=[gcp_label_col, "Filename", "X", "Y"])
        if filename_col:
            merged = pd.merge(merged, coords_df, left_on=[gcp_label_col, filename_col], right_on=[gcp_label_col, "Filename"], how="left")
            merged = merged.drop(columns=["Filename"], errors='ignore')
        else:
            merged = pd.merge(merged, coords_df, on=[gcp_label_col, "Filename"], how="left")
        merged.to_csv("pixel_coordinates_merged.csv", index=False)
        print("Merged coordinates saved to pixel_coordinates_merged.csv")
    else:
        df = pd.DataFrame([
            (g, f, x, y) for (g, f), (x, y) in coordinates_dict.items()
        ], columns=["GCP Label", "Filename", "X", "Y"])
        df.to_csv("pixel_coordinates.csv", index=False)
        print("Final coordinates saved to pixel_coordinates.csv")

cv2.namedWindow("Image Viewer")
cv2.setMouseCallback("Image Viewer", get_pixel_coordinates)

while True:
    display_image()
    key = cv2.waitKey(20) & 0xFF
    if key == ord('f'):
        # Prompt user to enter/select GCP Label, showing available unique values using easygui
        if gcp_input_df is not None:
            gcp_label_col = gcp_input_df.attrs.get('gcp_label_col', None)
            if not gcp_label_col:
                for col in gcp_input_df.columns:
                    if col.strip().lower() == 'gcp label':
                        gcp_label_col = col
                        break
            if gcp_label_col:
                valid_labels = set(gcp_input_df[gcp_label_col].dropna().unique())
                label_list = sorted(valid_labels)
                msg = "Enter GCP Label to mark (must match one of the below):\n\n" + "\n".join(label_list)
            else:
                valid_labels = set()
                label_list = []
                msg = "Enter GCP Label to mark:"
        else:
            valid_labels = set()
            label_list = []
            msg = "Enter GCP Label to mark:"
        new_label = easygui.enterbox(msg, "Select GCP Label")
        if not new_label:
            print("No GCP Label entered. GCP marking disabled until a label is selected.")
            continue
        if valid_labels and new_label not in valid_labels:
            print(f"Label '{new_label}' not found in input file. Valid labels: {label_list}")
            continue
        current_gcp_label = new_label
        print(f"Now marking for GCP Label: {current_gcp_label}")
    elif key == ord('r'):
        zoom_level = 1
        zoom_center = None
        display_image()
    elif key == ord('n'):
        # Move to next image
        if current_index < len(image_list) - 1:
            current_index += 1
        else:
            print("End of image list.")
    elif key == ord('s'):
        # Prompt user to enter/search filename using easygui, show some filenames
        show_files = image_list[:10] if len(image_list) > 10 else image_list
        msg = "Enter filename to search. Example(s):\n\n" + "\n".join(show_files)
        search_name = easygui.enterbox(msg, "Search Filename")
        if not search_name:
            continue
        if search_name in image_list:
            current_index = image_list.index(search_name)
        else:
            print("File not found.")
    elif key == ord('q'):
        break
    elif key == ord('e'):
        export_coordinates()

cv2.destroyAllWindows()