# Air Canvas 🖌️

A virtual drawing board where you can draw by simply waving your fingers in the air, using your webcam! Built with Python, OpenCV, and MediaPipe, this project tracks hand movements to let you paint in the air, and it even supports saving your art to Firebase and Google Drive.

## 🎯 Features

- Draw in air using index finger tracked via webcam
- Color and brush size selection via on-screen palette
- Eraser and Clear tools
- Upload background image
- Save drawings locally and to:
  - 🔥 Firebase Cloud Storage
  - 📁 Google Drive (with OAuth2 support)
- Undo functionality
- Smooth UI with real-time feedback

## 🧠 How it Works

1. Uses MediaPipe to detect hand and fingers.
2. Tracks the index finger tip to detect motion.
3. Maps the motion onto a virtual canvas.
4. UI allows color/size selection, eraser, background image, and more.

## 🧪 Requirements

- Python 3.8+
- OpenCV
- numpy
- mediapipe
- firebase-admin
- google-auth, google-api-python-client, google-auth-oauthlib

Install via:

```bash
pip install opencv-python mediapipe firebase-admin google-auth google-auth-oauthlib google-api-python-client numpy
