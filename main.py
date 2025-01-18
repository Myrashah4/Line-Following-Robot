import cv2
import numpy as np
import RPi.GPIO as GPIO
import time

# Motor Pin Definitions
AIN1 = 12
AIN2 = 13
BIN1 = 20
BIN2 = 21
ENA = 6
ENB = 26

# GPIO Setup
GPIO.cleanup()
GPIO.setmode(GPIO.BCM)
GPIO.setup(AIN1, GPIO.OUT)
GPIO.setup(AIN2, GPIO.OUT)
GPIO.setup(BIN1, GPIO.OUT)
GPIO.setup(BIN2, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(ENB, GPIO.OUT)

pwm_ena = GPIO.PWM(ENA, 100)
pwm_enb = GPIO.PWM(ENB, 100)
pwm_ena.start(40)  # Start with lower speed
pwm_enb.start(40)

# Motor Control
def control_motors(left_speed, right_speed):
    """Adjust motor speeds."""
    left_speed = max(20, min(60, left_speed))  # Clamp speed to keep it slow (20-60)
    right_speed = max(20, min(60, right_speed))

    GPIO.output(AIN1, GPIO.HIGH)
    GPIO.output(AIN2, GPIO.LOW)
    GPIO.output(BIN1, GPIO.HIGH)
    GPIO.output(BIN2, GPIO.LOW)

    pwm_ena.ChangeDutyCycle(left_speed)
    pwm_enb.ChangeDutyCycle(right_speed)

def stop():
    GPIO.output(AIN1, GPIO.LOW)
    GPIO.output(AIN2, GPIO.LOW)
    GPIO.output(BIN1, GPIO.LOW)
    GPIO.output(BIN2, GPIO.LOW)

# MJPG-Streamer URL
stream_url = "http://192.168.245.186:8080/?action=stream"

cap = cv2.VideoCapture(stream_url)

if not cap.isOpened():
    print("Error: Unable to open camera stream.")
    exit()

try:
    frame_center = 160  # Assuming the frame width is 320

    while True:
        # Capture a frame
        ret, frame = cap.read()
        if not ret:
            print("Error: Unable to capture frame.")
            break

        # Resize the frame (optional for faster processing)
        frame = cv2.resize(frame, (320, 240))

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Thresholding to detect black line
        _, binary = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)

        # Focus only on the bottom region of the frame
        roi = binary[200:240, :]
        contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Find the largest contour (assuming it's the line)
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)

            # Calculate the center of the black line
            line_center = x + w // 2

            # Calculate error
            error = frame_center - line_center

            k_p = 0.8  # Reduced proportional constant for smoother turns
            turn_rate = int(k_p * error)

            # Adjust motor speeds based on error
            base_speed = 20  # Lower base speed for slower movement
            left_speed = base_speed + turn_rate
            right_speed = base_speed - turn_rate

            # Ensure minimum speed to prevent stalling
            left_speed = max(15, min(30, left_speed))
            right_speed = max(15, min(30, right_speed))

            control_motors(left_speed, right_speed)
            print(f"Moving - Left: {left_speed}, Right: {right_speed}, Error: {error}")
        else:
            # If no line is detected, stop the robot
            print("Line not detected. Stopping.")
            stop()

        # Optional: Save frames for debugging
        cv2.imwrite("frame_debug.jpg", frame)
        cv2.imwrite("binary_debug.jpg", binary)

finally:
    # Cleanup
    cap.release()
    stop()
    GPIO.cleanup()
