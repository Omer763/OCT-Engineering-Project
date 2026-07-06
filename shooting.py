import os
import sys
import time

# Add the parent directory to the system path to allow importing modules from it
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import numpy as np
from utils.thorlabs.thorcam import TL_SDK, TL_Camera
from utils.thorlabs.kinesis import *
from imageio.v2 import imwrite

def take_tomographic_images(camera: TL_Camera,
                            mirror_servo: KinesisDevice, 
                            angles,
                            images_path,
                            samples_per_angle,
                            angles_path=None):

    real_angles = []

    for n, angle in enumerate(angles):
        i = n + 1 # Angle number
        
        # Rotate mirror
        mirror_servo.move_to(angle if angle >= 0 else 360 + angle)
        time.sleep(1)  # Wait for the mirror to stabilize

        real_angle = mirror_servo.get_position()
        real_angle = real_angle if real_angle <= 180 else -(360 - real_angle)
        real_angles.append(real_angle)

        print(f"Taking {samples_per_angle} images for angle {i} of {len(angles)}")

        # Loop to capture multiple samples for the current angle
        for j in range(1, samples_per_angle + 1):
            image_name = f"{i}{j}"
            
            # Take a shot
            camera.issue_software_trigger()

            frame = None
            while frame is None:
                frame = camera.get_pending_frame_or_null()
                if frame is None:
                    time.sleep(0.01)
            image_array = camera.frame_to_array(frame) # Copies image data from frame into a numpy array

            imwrite(os.path.join(images_path, f"{image_name}.png"), (image_array).astype(np.uint16))

    if angles_path is not None:
        np.save(angles_path, np.deg2rad(real_angles))

    print("\nFinishing...")
    mirror_servo.move_to(0)

def take_dark_images(camera: TL_Camera, images_path, samples):
    print(f"Taking {samples} dark images...")
    for j in range(1, samples + 1):
        image_name = f"{j}"
        
        # Take a shot
        camera.issue_software_trigger()

        frame = None
        while frame is None:
            frame = camera.get_pending_frame_or_null()
            if frame is None:
                time.sleep(0.01)
        image_array = camera.frame_to_array(frame)
        
        imwrite(os.path.join(images_path, f"{image_name}.png"), (image_array).astype(np.uint16))

class Mode:
    WAVEGUIDE = 0
    BACKGROUND = 1
    DARK = 2

# ===== Constants ===== #

TEST_NUMBER = 6
SAMPLES_PER_ANGLE = 0
MODE = Mode.WAVEGUIDE

START_ANGLE = -0.8
END_ANGLE = 1.2
ANGLES = 50

# ===================== #

root_dir = os.path.dirname(os.path.abspath(__file__))

test_dir = f"{root_dir}/tests/test {TEST_NUMBER}"
samples_dir = f"{test_dir}/samples"
backgrounds_dir = f"{test_dir}/backgrounds"
dark_dir = f"{test_dir}/dark"
angles_path = f"{test_dir}/angles (rad).npy"

# Create directories if they don't exist
os.makedirs(samples_dir, exist_ok=True)
os.makedirs(backgrounds_dir, exist_ok=True)
os.makedirs(dark_dir, exist_ok=True)

mirror_servo = None
sdk = None
camera = None

try:
    # Servo setup
    mirror_servo = TDC001Controller(83858557)
    mirror_servo.connect()
    mirror_servo.set_velocity(0.5)
    mirror_servo.set_acceleration(0.5)

    # Camera setup
    sdk = TL_SDK()
    cameras = sdk.get_camera_list()
    first_camera_id = cameras[0]
    camera = sdk.open_camera(first_camera_id)
    camera.set_exposure_time_us(2000)  # 2 ms exposure
    camera.set_frames_per_trigger_zero_for_unlimited(0)  # continuous mode
    camera.arm()

    # Angles setup
    d = (END_ANGLE - START_ANGLE) / (ANGLES - 1)
    angles = [START_ANGLE + i * d for i in range(ANGLES)]

    print("Setup complete.")

    if MODE ==  Mode.WAVEGUIDE:
        # Shooting Samples
        print("Press Enter to start taking WAVEGUIDE images...")
        take_tomographic_images(camera,
                                mirror_servo, 
                                angles,
                                samples_dir,
                                SAMPLES_PER_ANGLE,
                                angles_path)
        print("Sample images taken successfully.")

    elif MODE == Mode.BACKGROUND:
        # Shooting background
        print("Press Enter to start taking BACKGROUND images...")
        take_tomographic_images(camera,
                                mirror_servo, 
                                angles,
                                backgrounds_dir,
                                SAMPLES_PER_ANGLE)
        print("Background images taken successfully.")

    else:
        # Shooting Dark Images
        print("Press Enter to start taking DARK image...")
        take_dark_images(camera, dark_dir, SAMPLES_PER_ANGLE)
        print("Dark images taken successfully.")

        
except Exception as e:
    raise e
finally:
    if mirror_servo is not None:
        mirror_servo.disconnect()

    if camera is not None:
        camera.disarm()
        camera.close()

    if sdk is not None:
        sdk.close()