from flask import Flask, Response
import cv2
import RPi.GPIO as GPIO
import time

# Flask app initialization
app = Flask(__name__)

# GPIO setup for servo and solenoid valve
SERVO_PIN = 17  # Servo motor GPIO pin
VALVE_PIN = 23  # Solenoid valve (Relay) GPIO pin
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
GPIO.setup(VALVE_PIN, GPIO.OUT)
servo = GPIO.PWM(SERVO_PIN, 50)  # 50 Hz PWM frequency
servo.start(0)  # Start with duty cycle 0
GPIO.output(VALVE_PIN, GPIO.LOW)  # Ensure valve is initially closed

# Fire detection setup
fire_cascade = cv2.CascadeClassifier('fire_detection_cascade_model.xml')  # Adjust filename as needed
cap = cv2.VideoCapture(0)  # Use 0 for built-in camera, 1 for USB camera

# Variable to track fire detection state
fire_detected_previously = False


# Function to set servo angle (converts angle to duty cycle)
def set_servo_angle(angle):
    duty_cycle = 2.5 + (angle / 18)  # Map 0-180 degrees to 2.5-12.5% duty cycle
    servo.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5)  # Allow time for servo to move
    servo.ChangeDutyCycle(0)  # Stop PWM signal


# Function to control solenoid valve
def control_solenoid(valve_state):
    if valve_state == "open":
        GPIO.output(VALVE_PIN, GPIO.HIGH)
        print("Solenoid Valve Opened")
    else:
        GPIO.output(VALVE_PIN, GPIO.LOW)
        print("Solenoid Valve Closed")


# Function to generate video frames for streaming
def generate_frames():
    global fire_detected_previously
    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to capture frame")
            break

        # Convert frame to grayscale for fire detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fires = fire_cascade.detectMultiScale(gray, 1.2, 5)  # Detect fire

        # Check if fire is detected
        fire_detected = len(fires) > 0

        # Draw rectangles around detected fire
        for (x, y, w, h) in fires:
            cv2.rectangle(frame, (x - 20, y - 20), (x + w + 20, y + h + 20), (255, 0, 0), 2)
            print("Fire detected")

            # Determine servo angle based on fire position (assuming 640x480 resolution)
            if x < 320:  # Fire on left, rotate to 30 degrees
                set_servo_angle(30)
            elif x > 320:  # Fire on right, rotate to 150 degrees
                set_servo_angle(150)
            else:  # Fire near center, rotate to 90 degrees
                set_servo_angle(90)

            # Open solenoid valve to spray water
            control_solenoid("open")

        # If no fire detected, reset servo and close valve
        if not fire_detected and fire_detected_previously:
            set_servo_angle(90)  # Return to center position
            control_solenoid("close")

        # Update the previous fire detection state
        fire_detected_previously = fire_detected

        # Encode frame as JPEG for streaming
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            print("Failed to encode frame")
            continue
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# Flask route for video streaming
@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


# Main execution
if __name__ == '__main__':
    try:
        print("Starting Flask server...")
        app.run(host='0.0.0.0', port=5000)  # Run Flask server
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cap.release()
        set_servo_angle(90)  # Return servo to center on shutdown
        control_solenoid("close")  # Ensure valve is closed on shutdown
        servo.stop()
        GPIO.cleanup()
        print("System shutdown")