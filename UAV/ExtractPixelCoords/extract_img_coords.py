import cv2
import os
import pandas as pd

# Initialize variables
coordinates_dict = {}  # Stores latest clicks per (gcp_label, image)
image_list = []
current_index = 0
current_gcp_label = None  # User-selected GCP label

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

# Get folder path from user
folder_path = input("Enter the folder containing images: ")

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
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)  # Make dialog appear on top
    gcp_csv_path = filedialog.askopenfilename(title="Select GCP CSV file (optional)", filetypes=[("CSV Files", "*.csv")])
    root.destroy()
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
    global mouse_x, mouse_y, current_gcp_label
    mouse_x, mouse_y = x, y
    if event == cv2.EVENT_LBUTTONDOWN:
        filename = image_list[current_index]
        if not current_gcp_label:
            print("No GCP Label selected. Press 'f' and enter a GCP Label before marking.")
            return
        coordinates_dict[(current_gcp_label, filename)] = (x, y)
        clicked_pos[(current_gcp_label, filename)] = (x, y)
        print(f"Updated {filename} [{current_gcp_label}]: {x}, {y}")
        display_image()  # Redraw to show permanent cross

def draw_cross(img, x, y, color=(255, 0, 0), size=6, thickness=2):
    cv2.line(img, (x - size, y), (x + size, y), color, thickness)
    cv2.line(img, (x, y - size), (x, y + size), color, thickness)

def display_image():
    global current_index, mouse_x, mouse_y, current_gcp_label
    filename = image_list[current_index]
    img_path = os.path.join(folder_path, filename)
    image = cv2.imread(img_path)
    max_dim = 2000
    h, w = image.shape[:2]
    scale = 1.0
    if h > max_dim or w > max_dim:
        scale = min(max_dim / h, max_dim / w)
        new_size = (int(w * scale), int(h * scale))
        image = cv2.resize(image, new_size, interpolation=cv2.INTER_LINEAR)
    else:
        new_size = (w, h)
    # Draw permanent crosses for all GCPs marked on this image
    for (gcp, fname), (cx, cy) in clicked_pos.items():
        if fname == filename:
            draw_cross(image, cx, cy, color=(255, 0, 0), size=6, thickness=1)
    # Draw temporary cross at mouse position
    if 0 <= mouse_x < new_size[0] and 0 <= mouse_y < new_size[1]:
        draw_cross(image, mouse_x, mouse_y, color=(255, 0, 0), size=6, thickness=1)
    # Display filename at the top left
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    font_thickness = 2
    text_color = (255, 255, 255)
    bg_color = (0, 0, 0)
    text = f"{filename}"
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, font_thickness)
    cv2.rectangle(image, (5, 5), (10 + tw, 10 + th), bg_color, -1)
    cv2.putText(image, text, (10, 10 + th - 5), font, font_scale, text_color, font_thickness, cv2.LINE_AA)
    # Display GCP count at bottom left
    gcp_count = sum(1 for (fname, _gcp_label) in clicked_pos if fname == filename)
    gcp_text = f"GCPs marked: {gcp_count}"
    (gw, gh), _ = cv2.getTextSize(gcp_text, font, 0.8, 2)
    cv2.rectangle(image, (5, new_size[1] - 10 - gh), (10 + gw, new_size[1] - 5), bg_color, -1)
    cv2.putText(image, gcp_text, (10, new_size[1] - 10), font, 0.8, text_color, 2, cv2.LINE_AA)
    # Display directions at the bottom right
    directions_lines = [
        "Directions:",
        "Press 'f' to select GCP label.",
        "Left-click to mark for current label.",
        "When completed hit e to export data. Hit q to quit"
    ]
    dir_font_scale = 0.7
    dir_color = (0, 255, 255)
    dir_line_height = 0
    dir_width = 0
    dir_sizes = [cv2.getTextSize(line, font, dir_font_scale, 2)[0] for line in directions_lines]
    dir_width = max(w for w, h in dir_sizes)
    dir_line_height = max(h for w, h in dir_sizes) + 6
    total_dir_height = dir_line_height * len(directions_lines)
    dx = new_size[0] - dir_width - 15
    dy = new_size[1] - total_dir_height - 15
    cv2.rectangle(image, (dx - 5, dy - 5), (dx + dir_width + 5, dy + total_dir_height + 5), bg_color, -1)
    for i, line in enumerate(directions_lines):
        y = dy + dir_line_height * (i + 1) - 3
        cv2.putText(image, line, (dx, y), font, dir_font_scale, dir_color, 2, cv2.LINE_AA)
    # Display user controls at top right
    controls = [
        "Controls:",
        "f: Select GCP label",
        "n: Next image",
        "s: Search filename",
        "e: Export CSV",
        "q: Quit"
    ]
    ctrl_font_scale = 0.8
    ctrl_color = (0, 255, 0)
    y_offset = 10
    for i, ctrl in enumerate(controls):
        (cw, ch), _ = cv2.getTextSize(ctrl, font, ctrl_font_scale, 2)
        x = new_size[0] - cw - 10
        y = y_offset + (ch + 5) * (i + 1)
        cv2.putText(image, ctrl, (x, y), font, ctrl_font_scale, ctrl_color, 2, cv2.LINE_AA)
    # Show current GCP label at the top center
    if current_gcp_label:
        gcp_label_text = f"Current GCP Label: {current_gcp_label}"
        (lw, lh), _ = cv2.getTextSize(gcp_label_text, font, 0.9, 2)
        lx = max(0, (new_size[0] - lw) // 2)
        ly = 30
        cv2.rectangle(image, (lx - 5, ly - lh - 5), (lx + lw + 5, ly + 5), bg_color, -1)
        cv2.putText(image, gcp_label_text, (lx, ly), font, 0.9, (0, 255, 255), 2, cv2.LINE_AA)
    cv2.imshow("Image Viewer", image)
    cv2.setMouseCallback("Image Viewer", get_pixel_coordinates)

import numpy as np

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
        # Prompt user to enter/select GCP Label, showing available unique values
        if gcp_input_df is not None:
            gcp_label_col = gcp_input_df.attrs.get('gcp_label_col', None)
            if not gcp_label_col:
                # Fallback: try to find it again
                for col in gcp_input_df.columns:
                    if col.strip().lower() == 'gcp label':
                        gcp_label_col = col
                        break
            if gcp_label_col:
                valid_labels = set(gcp_input_df[gcp_label_col].dropna().unique())
                print("Available GCP labels:")
                for v in sorted(valid_labels):
                    print(f"  - {v}")
            else:
                valid_labels = set()
        else:
            valid_labels = set()
        new_label = input("Enter GCP Label to mark (must match one of the above): ").strip()
        if valid_labels and new_label not in valid_labels:
            print(f"Label '{new_label}' not found in input file. Valid labels: {sorted(valid_labels)}")
            continue
        if new_label:
            current_gcp_label = new_label
            print(f"Now marking for GCP Label: {current_gcp_label}")
        else:
            print("No GCP Label entered. GCP marking disabled until a label is selected.")
    elif key == ord('n'):
        # Move to next image
        if current_index < len(image_list) - 1:
            current_index += 1
        else:
            print("End of image list.")
    elif key == ord('s'):
        search_name = input("Enter filename to search: ")
        if search_name in image_list:
            current_index = image_list.index(search_name)
        else:
            print("File not found.")
    elif key == ord('q'):
        break
    elif key == ord('e'):
        export_coordinates()

cv2.destroyAllWindows()