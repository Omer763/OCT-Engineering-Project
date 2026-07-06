import os
import h5py
import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from scipy.ndimage import median_filter, rotate
import concurrent.futures

# ===== Constants ===== #

TEST_NUMBER = 2
SAMPLES_PER_ANGLE = 1
USE_DARK_IMAGES = True

# Filter samples
START_INDEX = 0
END_INDEX = -1 # Use -1 for last index

# Samples cropping and rotation
TOP_CROP = 0
BOTTOM_CROP = 0
LEFT_CROP = 0
RIGHT_CROP = 0
ROTATION_ANGLE = 2

AVARAGE_WIDTH = 100     # number of pixels to avarage over
DX = 0.03108  # μm per pixel
ANGLE_SCALE_FACTOR = 18.75
ANGLE_OFFSET = -4

DEBUG_SCALE_FACTOR = 15000
DEBUG_SAMPLE = -1

NOISE_FLOOR = 1.0       # Threshold to prevent near-zero division blowups
MEDIAN_FILTER_SIZE = 3

# ===================== #

# ===== Functions ===== #

def sort_by_sample(lst):
    return sorted(lst, key=lambda x: int(os.path.basename(x).split(".")[0]))

def load_files(samples_dir, backgrounds_dir, dark_dir, angles_path):
    sample_files = sort_by_sample([os.path.join(samples_dir, f) for f in os.listdir(samples_dir) if f.lower().endswith((".png"))])
    background_files = sort_by_sample([os.path.join(backgrounds_dir, f) for f in os.listdir(backgrounds_dir) if f.lower().endswith((".png"))])
    dark_files = sort_by_sample([os.path.join(dark_dir, f) for f in os.listdir(dark_dir) if f.lower().endswith((".png"))]) if dark_dir else None
    angles = np.load(angles_path)
    return sample_files, background_files, dark_files, angles

# Worker function for multiprocessing
def preprocess_image(i, sample_files, background_files, dark_image, image_name, debug_dir, start_avg, end_avg, Ny, Nx, Ny_cropped, Nx_cropped, samples_per_angle, rotate_angle, top_crop, left_crop, debug_scale, noise_floor):
    print(f"Processing {image_name}...")

    # Load and process images for the current sample
    image_sample = np.zeros((Ny, Nx), dtype=np.float64)
    image_background = np.zeros((Ny, Nx), dtype=np.float64)
    for j in range(samples_per_angle):
        image_sample += imageio.imread(sample_files[j]).astype(np.float64)
        image_background += imageio.imread(background_files[j]).astype(np.float64)

    # Average the images
    image_sample /= samples_per_angle
    image_background /= samples_per_angle

    # DEBUG
    if i == DEBUG_SAMPLE: debug_image(np.clip(image_sample * 500, 0, 65535).astype(np.uint16), f"1. original_{image_name}", debug_dir)

    # Subtract the dark frame and clip negative noise to 0
    if dark_image is not None:
        image_sample = np.clip(image_sample - dark_image, 0, None)
        image_background = np.clip(image_background - dark_image, 0, None)
    
    # Avoid division by zero and microscopic noise
    image = np.divide(image_sample, image_background, 
                    out=np.ones_like(image_sample), 
                    where=image_background > noise_floor)
    
    # DEBUG
    if i == DEBUG_SAMPLE: debug_image(np.clip(image * 14000, 0, 65535).astype(np.uint16), f"2. background_corrected_{image_name}", debug_dir)

    # Filter noise
    image = median_filter(image, size=MEDIAN_FILTER_SIZE)

    # DEBUG
    if i == DEBUG_SAMPLE: debug_image(np.clip(image * 14000, 0, 65535).astype(np.uint16), f"3. filtered_{image_name}", debug_dir)

    # Rotate images
    if rotate_angle != 0:
        image_sample = rotate(image_sample, rotate_angle, reshape=False)
        image_background = rotate(image_background, rotate_angle, reshape=False)  

    # Crop images
    image_sample = image_sample[top_crop:top_crop+Ny_cropped, left_crop:left_crop+Nx_cropped]
    image_background = image_background[top_crop:top_crop+Ny_cropped, left_crop:left_crop+Nx_cropped]

    # Take average along the x axis
    I_k = image[start_avg:end_avg, :].mean(axis=0)

    # DEBUG: Save the processed image and the averaged intensity map
    debug_image(np.clip(image * debug_scale, 0, 65535).astype(np.uint16), f"{image_name}", debug_dir)
    debug_image(np.clip(np.array([I_k]) * debug_scale, 0, 65535).astype(np.uint16), f"{image_name}_y_avg", debug_dir)
    
    return i, I_k

def debug_image(image, image_name, dir):
    imageio.imwrite(f"{dir}/{image_name}.png", image)

def plot(I_map, angles, Nx_cropped):
    plt.figure(figsize=(4,3))
    plt.imshow(
        I_map.T,
        extent=[np.rad2deg(angles[0]) + ANGLE_OFFSET, np.rad2deg(angles[-1]) + ANGLE_OFFSET, 0, DX * Nx_cropped],
        aspect='auto',
        origin='lower')
    plt.colorbar()
    plt.xlabel("angle θ (°)")
    plt.ylabel("x (μm)")
    plt.tight_layout()
    plt.show()

def save_to_jld(I_map, angles, tomogram_guide_path):
    with h5py.File(tomogram_guide_path, "w") as f:
        f.create_dataset("I", data=I_map)
        f.create_dataset("θ_l", data=angles)
        f.create_dataset("dx", data=np.array(DX))

# ===================== #

def main():
    # Create directories
    root_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = f"{root_dir}/tests/test {TEST_NUMBER}"
    samples_dir = f"{test_dir}/samples"
    backgrounds_dir = f"{test_dir}/backgrounds"
    dark_dir = f"{test_dir}/dark"
    debug_dir = f"{test_dir}/debug"
    angles_path = f"{test_dir}/angles (rad).npy"
    tomogram_guide_path = f"{test_dir}/tomogram_guide.jld"

    # Create debug directory if it doesn't exist
    os.makedirs(debug_dir, exist_ok=True)

    # Load files
    waveguide_files, background_files, dark_files, angles = load_files(samples_dir, backgrounds_dir, dark_dir if USE_DARK_IMAGES else None, angles_path)
    assert len(waveguide_files) == len(background_files) == len(angles) * SAMPLES_PER_ANGLE, f"Mismatch in number of files: {len(waveguide_files)} waveguide files, {len(background_files)} background files, {len(angles)} angles"

    # Calc samples count
    end_index = len(angles) if END_INDEX == -1 else (END_INDEX + 1)
    number_of_angles = end_index - START_INDEX

    # Calc cropped image dimensions
    Ny, Nx = imageio.imread(waveguide_files[0]).shape
    Ny_cropped = Ny - (TOP_CROP + BOTTOM_CROP)
    Nx_cropped = Nx - (LEFT_CROP + RIGHT_CROP)

    # Pre-calculate the master dark frame once
    dark_image = None
    if USE_DARK_IMAGES:
        dark_image = np.zeros((Ny, Nx), dtype=np.float64)
        for f in dark_files:
            dark_image += imageio.imread(f).astype(np.float64)
        if len(dark_files) > 0:
            dark_image /= len(dark_files)
        # dark_image = median_filter(dark_image, size=MEDIAN_FILTER_SIZE)

    # Calc avarage band indices
    center = Ny_cropped // 2
    half_width = AVARAGE_WIDTH // 2
    start_avg = max(center - half_width, 0)
    end_avg = min(center + half_width, Ny_cropped)

    # Define I_map dimensions
    I_map = np.zeros((number_of_angles, Nx_cropped), dtype=np.float64)

    # Preprocess the samples using multiprocessing
    max_workers = os.cpu_count() or 4
    print(f"Starting multiprocessing pool with {max_workers} workers...")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(number_of_angles):
            image_name = f"Sample {START_INDEX + i + 1}"
            w_files_chunk = waveguide_files[(START_INDEX + i) * SAMPLES_PER_ANGLE:(START_INDEX + i) * SAMPLES_PER_ANGLE + SAMPLES_PER_ANGLE]
            b_files_chunk = background_files[(START_INDEX + i) * SAMPLES_PER_ANGLE:(START_INDEX + i) * SAMPLES_PER_ANGLE + SAMPLES_PER_ANGLE]
            
            futures.append(executor.submit(
                preprocess_image,
                i, w_files_chunk, b_files_chunk, dark_image, image_name, debug_dir, start_avg, end_avg,
                Ny, Nx, Ny_cropped, Nx_cropped, SAMPLES_PER_ANGLE, ROTATION_ANGLE, 
                TOP_CROP, LEFT_CROP, DEBUG_SCALE_FACTOR, NOISE_FLOOR
            ))

        # Populate I_map as tasks complete
        for future in concurrent.futures.as_completed(futures):
            i, I_k = future.result()
            I_map[i, :] = I_k

    # Flip I_map and properly sliced angles horizontally
    I_map = np.flip(I_map, axis=0)
    angles = np.flip(angles[START_INDEX:end_index], axis=0) * ANGLE_SCALE_FACTOR

    # Save to JLD file
    save_to_jld(I_map, angles, tomogram_guide_path)

    # Plot the intensity map
    plot(I_map, angles, Nx_cropped)

# Required guard block for multiprocessing on Windows
if __name__ == '__main__':
    main()