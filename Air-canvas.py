import cv2
import numpy as np
import mediapipe as mp
from collections import deque
import math
import threading
import tkinter as tk
from tkinter import filedialog
# hide the root Tk window
root = tk.Tk()
root.withdraw()

import firebase_admin
from firebase_admin import credentials, storage

# Initialize Firebase app
cred = credentials.Certificate("C:/Users/Public/Air-Canvas-project-master/Air-Canvas-project-master/keys/serviceAccountKey.json")  # Ensure this path is correct
firebase_admin.initialize_app(cred, {
    'storageBucket': 'aircanvasstorage.firebasestorage.app'  
})

# Reference to the Firebase Storage bucket
bucket = storage.bucket()

from datetime import datetime

def save_to_firebase(image_path):
    # Get current date in YYYY-MM-DD format
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Save to a subfolder named after today's date
    blob = bucket.blob(f"drawings/{current_date}/{image_path}")
    
    blob.upload_from_filename(image_path)
    blob.make_public()  # Optional: make file publicly accessible
    print(f"File uploaded to: {blob.public_url}")  # Prints public URL

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import os

SCOPES = ['https://www.googleapis.com/auth/drive.file']

from datetime import datetime

def upload_to_drive(file_path, file_name):
    creds = None

    # Check if token already exists
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If no valid credentials, prompt login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('keys/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Build Drive service
    service = build('drive', 'v3', credentials=creds)

    # Step 1: Get/create 'Drawings' folder
    drawings_folder_id = get_or_create_folder(service, 'Drawings', parent_id=None)

    # Step 2: Get/create today's folder inside 'Drawings'
    today = datetime.now().strftime('%Y-%m-%d')
    date_folder_id = get_or_create_folder(service, today, parent_id=drawings_folder_id)

    # Step 3: Upload file into the date folder
    file_metadata = {'name': file_name, 'parents': [date_folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    print('✅ File uploaded to Google Drive with ID:', file.get('id'))

def get_or_create_folder(service, folder_name, parent_id=None):
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])

    if items:
        return items[0]['id']
    else:
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
        }
        if parent_id:
            folder_metadata['parents'] = [parent_id]
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')



# Initialize window settings
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# Giving different arrays to handle colour points of different colour
bpoints = [deque(maxlen=1024)]
gpoints = [deque(maxlen=1024)]
rpoints = [deque(maxlen=1024)]
ypoints = [deque(maxlen=1024)]
ppoints = [deque(maxlen=1024)]  # Purple
opoints = [deque(maxlen=1024)]  # Orange
cpoints = [deque(maxlen=1024)]  # Cyan
pinkpoints = [deque(maxlen=1024)]  # Pink

# These indexes will be used to mark the points in particular arrays of specific colour
blue_index = 0
green_index = 0
red_index = 0
yellow_index = 0
purple_index = 0
orange_index = 0
cyan_index = 0
pink_index = 0

# The kernel to be used for dilation purpose 
kernel = np.ones((5, 5), np.uint8)

# Colors in BGR format
colors = [
    (255, 0, 0),     # Blue
    (0, 255, 0),     # Green
    (0, 0, 255),     # Red
    (0, 255, 255),   # Yellow
    (255, 0, 255),   # Purple
    (0, 165, 255),   # Orange
    (255, 255, 0),   # Cyan
    (203, 192, 255)  # Pink
]
color_names = ["BLUE", "GREEN", "RED", "YELLOW", "PURPLE", "ORANGE", "CYAN", "PINK"]
colorIndex = 0

# Brush and canvas settings
brush_size = 5  # Default brush size
eraser_mode = False
canvas_color = (255, 255, 255)  # White canvas

# Create a function to draw color palette
def draw_color_palette(frame, selected_color):
    global brush_size, eraser_mode
    
    # Calculate dimensions
    palette_height = 100
    color_radius = 30
    spacing = 20
    start_x = spacing
    start_y = spacing
    
    # Draw palette background
    cv2.rectangle(frame, (0, 0), (WINDOW_WIDTH, palette_height), (240, 240, 240), -1)
    cv2.line(frame, (0, palette_height), (WINDOW_WIDTH, palette_height), (200, 200, 200), 2)
    
    # Draw color circles
    for i, color in enumerate(colors):
        center_x = start_x + i * (color_radius * 2 + spacing) + color_radius
        center_y = start_y + color_radius
        
        # Draw outer circle if selected
        if i == selected_color and not eraser_mode:
            cv2.circle(frame, (center_x, center_y), color_radius + 5, (255, 255, 255), 2)
        
        # Draw color circle
        cv2.circle(frame, (center_x, center_y), color_radius, color, -1)
        
        # Add color name
        text_size = cv2.getTextSize(color_names[i], cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        text_x = center_x - text_size[0] // 2
        cv2.putText(frame, color_names[i], (text_x, center_y + color_radius + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    
    # Draw brush size slider
    slider_start_x = start_x + len(colors) * (color_radius * 2 + spacing) + spacing
    slider_width = 200
    slider_height = 20
    slider_y = start_y + color_radius - slider_height // 2
    
    # Draw slider background
    cv2.rectangle(frame, (slider_start_x, slider_y), 
                 (slider_start_x + slider_width, slider_y + slider_height), (200, 200, 200), -1)
    
    # Draw slider position
    position = int(slider_start_x + (brush_size / 25) * slider_width)
    cv2.circle(frame, (position, slider_y + slider_height // 2), 10, (0, 0, 0), -1)
    
    # Draw brush size text
    cv2.putText(frame, f"Brush Size: {brush_size}", (slider_start_x, slider_y - 10), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
    
    # Button dimensions 
    button_width = 80
    button_height = 25
    button_spacing = 15

    # Draw eraser button
    spacing = 20
    eraser_x = slider_start_x + slider_width + spacing
    eraser_y = start_y + color_radius - 12
    cv2.rectangle(frame, (eraser_x, eraser_y), (eraser_x + button_width, eraser_y + button_height),
                  (50, 50, 50) if eraser_mode else (200, 200, 200), -1)
    cv2.putText(frame, "ERASER", (eraser_x + 8, eraser_y + 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255) if eraser_mode else (0, 0, 0), 1, cv2.LINE_AA)

    # Draw clear button
    clear_x = eraser_x + button_width + button_spacing
    clear_y = eraser_y
    cv2.rectangle(frame, (clear_x, clear_y), (clear_x + button_width, clear_y + button_height), (240, 100, 100), -1)
    cv2.putText(frame, "CLEAR", (clear_x + 10, clear_y + 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    # Draw save button
    save_x = clear_x + button_width + button_spacing
    save_y = clear_y
    cv2.rectangle(frame, (save_x, save_y), (save_x + button_width, save_y + button_height), (100, 240, 100), -1)
    cv2.putText(frame, "SAVE", (save_x + 15, save_y + 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    # Draw upload button
    upload_x = save_x + button_width + button_spacing
    upload_y = save_y
    cv2.rectangle(frame, (upload_x, upload_y), (upload_x + button_width, upload_y + button_height), (100, 100, 240), -1)
    cv2.putText(frame, "UPLOAD", (upload_x + 5, upload_y + 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)



    
    return frame

# Function to draw brush preview
def draw_brush_preview(frame, position, color, size):
    cv2.circle(frame, position, size, color, -1)
    cv2.circle(frame, position, size, (0, 0, 0), 1)  # Outline
    return frame

# Function to check if a point is inside a rectangle
def is_point_in_rect(point, rect_start, rect_end):
    return rect_start[0] <= point[0] <= rect_end[0] and rect_start[1] <= point[1] <= rect_end[1]

# Initialize mediapipe
mpHands = mp.solutions.hands
hands = mpHands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mpDraw = mp.solutions.drawing_utils

# Setup canvas
canvas = np.ones((WINDOW_HEIGHT, WINDOW_WIDTH, 3), dtype=np.uint8) * 255

# Initialize the webcam
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, WINDOW_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, WINDOW_HEIGHT)

# Variables for cursor state
cursor_visible = True
cursor_timer = 0
is_drawing = False
previous_finger_position = None
finger_up = True
save_counter = 0
stroke_started = False  # NEW
background_image = None
button_cooldown = 0
BUTTON_COOLDOWN_TIME = 30



# UNDO Feature
undo_stack = []
drawing_points = []

def save_undo(canvas):
    # Save a deep copy of the canvas to undo stack
    if len(undo_stack) > 100:  
        undo_stack.pop(0)
    undo_stack.append(canvas.copy())


# Status message
status_message = "Welcome to Air Canvas! Move your hand to draw."
status_timer = 0

ret = True
while ret:
    # Read each frame from the webcam
    ret, frame = cap.read()
    if not ret:
        break

    if button_cooldown > 0:
        button_cooldown -= 1

    # Resize frame
    frame = cv2.resize(frame, (WINDOW_WIDTH, WINDOW_HEIGHT))
    
    # Flip the frame horizontally
    frame = cv2.flip(frame, 1)
    framergb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Show background image if available
    canvas_height = frame.shape[0] - 100
    canvas_width = frame.shape[1]
    if canvas.shape[:2] != (canvas_height, canvas_width):
        canvas = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 255

    if background_image is not None:
        resized_bg = cv2.resize(background_image, (canvas_width, canvas_height))
        frame[100:, :] = cv2.addWeighted(resized_bg, 0.5, canvas[:canvas_height, :canvas_width], 0.5, 0)
    else:
        frame[100:, :] = cv2.addWeighted(frame[100:, :], 0.3, canvas[:canvas_height, :canvas_width], 0.7, 0)

    # Show background image if available
    if background_image is not None:
        # Make sure the sizes match
        if background_image.shape[0] != canvas_height or background_image.shape[1] != canvas_width:
            background_image = cv2.resize(background_image, (canvas_width, canvas_height))
    
        # Overlay the background image with the canvas
        frame[100:, :] = cv2.addWeighted(background_image, 0.5, canvas, 0.5, 0)
    else:
        frame[100:, :] = cv2.addWeighted(frame[100:, :], 0.3, canvas, 0.7, 0)

    
    # Apply the palette UI
    frame = draw_color_palette(frame, colorIndex)
    
    # Copy the canvas to the frame below the palette
    canvas_height = frame.shape[0] - 100
    canvas_width = frame.shape[1]
    if canvas.shape[:2] != (canvas_height, canvas_width):
    # Resize canvas to match the required dimensions
      canvas = np.ones((canvas_height, canvas_width, 3), dtype=np.uint8) * 255

# Then use only the portion of canvas that will fit
    frame[100:, :] = cv2.addWeighted(frame[100:, :], 0.3, canvas[:frame.shape[0]-100, :frame.shape[1]], 0.7, 0)    
    # Get hand landmark prediction
    result = hands.process(framergb)
    
    # Display status message
    if status_timer > 0:
        cv2.rectangle(frame, (WINDOW_WIDTH // 2 - 200, WINDOW_HEIGHT - 50), 
                     (WINDOW_WIDTH // 2 + 200, WINDOW_HEIGHT - 20), (0, 0, 0, 100), -1)
        cv2.putText(frame, status_message, (WINDOW_WIDTH // 2 - 190, WINDOW_HEIGHT - 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        status_timer -= 1
    
    # Post process the result
    if result.multi_hand_landmarks:
        landmarks = []
        for handslms in result.multi_hand_landmarks:
            for lm in handslms.landmark:
                lmx = int(lm.x * WINDOW_WIDTH)
                lmy = int(lm.y * WINDOW_HEIGHT)
                landmarks.append([lmx, lmy])
            
            # Draw landmarks on frames with transparent effect
            mpDraw.draw_landmarks(frame, handslms, mpHands.HAND_CONNECTIONS,
                                 mpDraw.DrawingSpec(color=(255, 255, 255), thickness=1, circle_radius=1),
                                 mpDraw.DrawingSpec(color=(0, 153, 255), thickness=1, circle_radius=1))
        
        # Get index and middle finger positions
        index_finger_tip = (landmarks[8][0], landmarks[8][1])
        middle_finger_tip = (landmarks[12][0], landmarks[12][1])
        thumb_tip = (landmarks[4][0], landmarks[4][1])
        
        # Calculate distance between fingers for pinch/draw gesture
        index_middle_distance = math.sqrt((index_finger_tip[0] - middle_finger_tip[0])**2 + 
                                         (index_finger_tip[1] - middle_finger_tip[1])**2)
        
        # Check if index finger is up and middle finger is down (drawing gesture)
        if index_finger_tip[1] < landmarks[6][1] and middle_finger_tip[1] > landmarks[10][1]:
            # Drawing mode
            cursor_visible = True
            cursor_timer = 10
            
            # Check if finger is in palette area
            if index_finger_tip[1] < 100:
                # Check color selection
                for i in range(len(colors)):
                    center_x = 20 + i * (60 + 20) + 30
                    center_y = 20 + 30
                    distance = math.sqrt((index_finger_tip[0] - center_x)**2 + (index_finger_tip[1] - center_y)**2)
                    if distance < 30:
                        colorIndex = i
                        eraser_mode = False
                        status_message = f"Selected color: {color_names[i]}"
                        status_timer = 30
                
                # Check slider for brush size
                slider_start_x = 20 + len(colors) * (60 + 20) + 20
                slider_width = 200
                slider_y = 20 + 30 - 10
                if is_point_in_rect(index_finger_tip, (slider_start_x, slider_y), 
                                   (slider_start_x + slider_width, slider_y + 20)):
                    rel_x = index_finger_tip[0] - slider_start_x
                    brush_size = max(1, min(25, int((rel_x / slider_width) * 25)))
                    status_message = f"Brush size: {brush_size}"
                    status_timer = 30
                
                # Check eraser button (smaller size)
                spacing = 20
                start_y = 20
                color_radius = 30
                eraser_x = slider_start_x + slider_width + spacing
                eraser_y = start_y + color_radius - 15
                if is_point_in_rect(index_finger_tip, (eraser_x, eraser_y), (eraser_x + 80, eraser_y + 25))and button_cooldown == 0:
                    eraser_mode = not eraser_mode
                    status_message = "Eraser mode: " + ("ON" if eraser_mode else "OFF")
                    status_timer = 30
                    button_cooldown = BUTTON_COOLDOWN_TIME  # Set cooldown

                # Check clear button (smaller size)
                clear_x = eraser_x + 100  # 80 (button width) + 20 (spacing between buttons)
                clear_y = eraser_y
                if is_point_in_rect(index_finger_tip, (clear_x, clear_y), (clear_x + 80, clear_y + 25))and button_cooldown == 0:
                    canvas = np.ones((WINDOW_HEIGHT, WINDOW_WIDTH, 3), dtype=np.uint8) * 255
                    uploaded_image = None  # Also reset uploaded image if you are using upload feature
                    status_message = "Canvas cleared!"
                    status_timer = 30
                    button_cooldown = BUTTON_COOLDOWN_TIME  # Set cooldown

                # Check save button (smaller size)
                save_x = clear_x + 100
                save_y = clear_y
                if is_point_in_rect(index_finger_tip, (save_x, save_y), (save_x + 80, save_y + 25))and button_cooldown == 0:
                    save_filename = f"air_canvas_{save_counter}.png"
    
                    # Create final image by properly combining background and canvas
                    if background_image is not None:
                        # Ensure background image is resized to match canvas dimensions
                        resized_bg = cv2.resize(background_image, (canvas.shape[1], canvas.shape[0]))
                        # Combine background with canvas
                        final_image = cv2.addWeighted(resized_bg, 0.5, canvas, 0.5, 0)
                    else:
                        final_image = canvas.copy()
    
                    # Save the combined image
                    cv2.imwrite(save_filename, final_image)
    
                    def upload_task():
                        try:
                            save_to_firebase(save_filename)
                            upload_to_drive(save_filename, os.path.basename(save_filename))
                        except Exception as e:
                            print(f"Upload error: {e}")
    
                    upload_thread = threading.Thread(target=upload_task)
                    upload_thread.daemon = True
                    upload_thread.start()
    
                    status_message = f"Saved as {save_filename}!"
                    status_timer = 60
                    save_counter += 1
                    button_cooldown = BUTTON_COOLDOWN_TIME  # Set cooldown


                # Check Upload Image button
                button_width = 80
                button_spacing = 15
                button_height = 25
                upload_x = save_x + button_width + button_spacing
                upload_y = save_y
                if is_point_in_rect(index_finger_tip, (upload_x, upload_y), (upload_x + button_width, upload_y + button_height))and button_cooldown == 0:
                    filename = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
                    if filename:
                        try:
                            # Load the image and ensure it's properly read
                            background_image = cv2.imread(filename)
                            if background_image is not None:
                                # Resize image to match canvas dimensions
                                background_image = cv2.resize(background_image, (canvas_width, canvas_height))
                                status_message = "Background image loaded successfully!"
                            else:
                                status_message = "Failed to load image. Try another file."
                        except Exception as e:
                            status_message = f"Error loading image: {str(e)}"
                        status_timer = 30
                        button_cooldown = BUTTON_COOLDOWN_TIME  # Set cooldown


                
                # Reset drawing state
                is_drawing = False
                previous_finger_position = None
            
            # Drawing area
            elif index_finger_tip[1] > 100:
                # Show brush preview
                current_color = (255, 255, 255) if eraser_mode else colors[colorIndex]
                draw_brush_preview(frame, index_finger_tip, current_color, brush_size)
                
                if previous_finger_position is not None:
                    if not stroke_started:
                        undo_stack.append(canvas.copy())  # Save before first stroke
                        stroke_started = True  # Mark that stroke has started
    
                    # Adjust finger positions to account for canvas offset
                    canvas_finger_position = (index_finger_tip[0], index_finger_tip[1] - 100)
                    canvas_previous_position = (previous_finger_position[0], previous_finger_position[1] - 100)
    
                    # Only draw if the position is within the canvas area
                    if 0 <= canvas_finger_position[1] < canvas.shape[0] and 0 <= canvas_previous_position[1] < canvas.shape[0]:
                        if eraser_mode:
                            cv2.line(canvas, canvas_previous_position, canvas_finger_position, (255, 255, 255), brush_size * 2)
                        else:
                            cv2.line(canvas, canvas_previous_position, canvas_finger_position, colors[colorIndex], brush_size)

                
                previous_finger_position = index_finger_tip
                is_drawing = True
        else:
            # Not in drawing mode
            previous_finger_position = None
            stroke_started = False
            is_drawing = False
            thumb_index_distance = math.sqrt((index_finger_tip[0] - thumb_tip[0]) ** 2 +
                                     (index_finger_tip[1] - thumb_tip[1]) ** 2)
            if thumb_index_distance < 30:
                if cursor_timer <= 0:
                    cursor_visible = not cursor_visible
                    cursor_timer = 30
                    status_message = "Cursor visibility toggled"
                    status_timer = 30

            
            # Check if gesture is a pinch (for special actions)
            thumb_index_distance = math.sqrt((index_finger_tip[0] - thumb_tip[0])**2 + 
                    (index_finger_tip[1] - thumb_tip[1])**2)
            
            if thumb_index_distance < 30:  # Pinch gesture
                if cursor_timer <= 0:
                    cursor_visible = not cursor_visible
                    cursor_timer = 30
                    status_message = "Cursor visibility toggled"
                    status_timer = 30
    else:
        # No hand detected
        previous_finger_position = None
        is_drawing = False
    
    # Decrease cursor timer
    if cursor_timer > 0:
        cursor_timer -= 1
    
    # Show drawing guides
    if is_drawing:
        cv2.putText(frame, "DRAWING", (WINDOW_WIDTH - 150, WINDOW_HEIGHT - 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
    
    # Display current tool info
    tool_info = f"Tool: {'Eraser' if eraser_mode else color_names[colorIndex]} | Size: {brush_size}"
    cv2.putText(frame, tool_info, (10, WINDOW_HEIGHT - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
    
    # Add help text
    cv2.putText(frame, "Index finger to draw, pinch to toggle cursor", (WINDOW_WIDTH // 2 - 200, 130), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
    
    # Display the frame
    cv2.imshow("Air Canvas", frame)
    
    # Check for key press
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('c'):
        save_undo(canvas)
        canvas = np.ones((WINDOW_HEIGHT, WINDOW_WIDTH, 3), dtype=np.uint8) * 255
        status_message = "Canvas cleared!"
        status_timer = 30
    
    elif key == ord('s'):
        save_filename = f"air_canvas_{save_counter}.png"
    
        # Combine background and canvas before saving
        if background_image is not None:
            resized_bg = cv2.resize(background_image, (canvas.shape[1], canvas.shape[0]))
            final_image = cv2.addWeighted(resized_bg, 0.5, canvas, 0.5, 0)
        else:
            final_image = canvas.copy()
    
        cv2.imwrite(save_filename, final_image)

    elif key == ord('z'):
        if undo_stack:
            canvas[:] = undo_stack.pop()
            status_message = "Undo successful!"
            status_timer = 30
        else:
            status_message = "Nothing to undo!"
            status_timer = 30


    

# Release the webcam and destroy all active windows
cap.release()
cv2.destroyAllWindows()