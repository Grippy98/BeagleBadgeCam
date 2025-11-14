import cv2
import numpy as np
import json
from datetime import datetime
import sys
import platform
import subprocess

def gameboy_effect(frame, threshold_value):
    # Downscale the frame to a low resolution
    h, w, _ = frame.shape
    small_frame = cv2.resize(frame, (w // 4, h // 4), interpolation=cv2.INTER_NEAREST)

    # Convert to grayscale
    gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)

    # Apply a threshold to create a 2-bit color depth
    _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)

    # Upscale back to the original size
    output = cv2.resize(thresh, (w, h), interpolation=cv2.INTER_NEAREST)

    return cv2.cvtColor(output, cv2.COLOR_GRAY2BGR)

def overlay_mustache(frame, gray, face_cascade, mustache_img):
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        # Region of Interest (ROI) for the face
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = frame[y:y+h, x:x+w]

        # Resize mustache to fit the face
        mustache_width = int(w * 0.6)
        mustache_height = int(mustache_width * mustache_img.shape[0] / mustache_img.shape[1])
        resized_mustache = cv2.resize(mustache_img, (mustache_width, mustache_height))

        # Position of the mustache
        mustache_x = int(x + w / 2 - mustache_width / 2)
        mustache_y = int(y + h * 0.55)

        # Overlay the mustache
        for i in range(resized_mustache.shape[0]):
            for j in range(resized_mustache.shape[1]):
                if resized_mustache[i, j][3] != 0:  # Check alpha channel
                    if mustache_y + i < frame.shape[0] and mustache_x + j < frame.shape[1]:
                        frame[mustache_y + i, mustache_x + j] = resized_mustache[i, j][:3]
    return frame

def main():
    with open('config.json', 'r') as f:
        config = json.load(f)

    if platform.system() == "Linux":
        if not config.get('bluetooth_mac_address'):
            print("Bluetooth MAC address not found in config.json.")
            response = input("Would you like to scan for Bluetooth devices now? (y/n): ")
            if response.lower() == 'y':
                subprocess.run([sys.executable, 'bluetooth_scanner.py'])
                with open('config.json', 'r') as f:
                    config = json.load(f)
                if not config.get('bluetooth_mac_address'):
                    print("No device was selected. Exiting.")
                    return
            else:
                print("Exiting.")
                return

    resolutions = [
        (128, 112),
        (160, 140),
        (192, 168),
        (224, 196),
        (256, 224),
        (288, 252)
    ]
    res_index = 0
    width, height = resolutions[res_index]

    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    mustache_img = cv2.imread('mustache.png', -1)

    if mustache_img is None:
        print("Error: Could not load mustache.png. Make sure the file is in the correct directory.")
        return

    cap = cv2.VideoCapture(0)
    mustache_on = False
    threshold_values = [64, 128, 192]
    threshold_index = 1
    threshold_value = threshold_values[threshold_index]

    if not cap.isOpened():
        print("Error: Could not open video stream. Please check camera permissions.")
        return

    # Allow time for camera to initialize
    cv2.waitKey(1000)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Can't receive frame (stream end?). Exiting ...")
            break

        # Resize the frame
        frame = cv2.resize(frame, (width, height))

        # Create a grayscale version for face detection before applying effects
        gray_for_detection = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if mustache_on:
            frame = overlay_mustache(frame, gray_for_detection, face_cascade, mustache_img)

        # Apply Game Boy effect
        output_frame = gameboy_effect(frame, threshold_value)

        # Resize for final output
        output_frame = cv2.resize(output_frame, (400, 200))

        # Create bezels
        top_bezel = np.zeros((50, 400, 3), dtype=np.uint8)
        bottom_bezel = np.zeros((50, 400, 3), dtype=np.uint8)

        # Add text to bezels
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(top_bezel, "Moustache Cam", (100, 35), font, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(bottom_bezel, "BeagleBadge", (120, 35), font, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

        # Combine bezels and frame
        final_frame = np.vstack((top_bezel, output_frame, bottom_bezel))

        cv2.imshow('BeagleBadgeCam', final_frame)

        key = cv2.waitKeyEx(1)  # Use waitKeyEx for special keys
        if key == -1:  # No key pressed
            pass
        elif key & 0xFF == ord('q'):
            break
        elif key & 0xFF == ord('m'):
            mustache_on = not mustache_on
        elif key & 0xFF == ord('+') or key & 0xFF == ord('='):
            res_index = min(len(resolutions) - 1, res_index + 1)
            width, height = resolutions[res_index]
            print(f"Resolution: {width}x{height}")
        elif key & 0xFF == ord('-'):
            res_index = max(0, res_index - 1)
            width, height = resolutions[res_index]
            print(f"Resolution: {width}x{height}")
        # Key code for arrow keys on this system
        elif key == 3:  # Arrow Key Pressed
            threshold_index = (threshold_index + 1) % len(threshold_values)
            threshold_value = threshold_values[threshold_index]
            print(f"Threshold: {threshold_value}")
        elif key & 0xFF == ord(' '):
            filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(filename, final_frame)
            print(f"Saved {filename}")
            if platform.system() == "Linux":
                mac_address = config.get('bluetooth_mac_address')
                channel = config.get('bluetooth_channel')
                if mac_address and channel:
                    try:
                        subprocess.run(['phomemo_printer', '-a', mac_address, '-c', str(channel), '-i', filename])
                    except Exception as e:
                        print(f"Error printing: {e}")
            else:
                print("Printing is not supported on this operating system.")
        else:
            if key != -1:
                print(f"Unrecognized key code: {key}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
