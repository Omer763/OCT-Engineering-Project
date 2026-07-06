# Tomographic Refractive Index Profiling of FLDW Waveguides

This repository contains the software ecosystem for automating data acquisition and performing refractive index reconstruction of femtosecond laser direct written (FLDW) waveguides. The system is split into a Python-based hardware control and preprocessing pipeline, and a Julia-based mathematical reconstruction backend.

The reconstruction methodology implemented in this project is based on the work described by Nicolas Barré et al. in *"Tomographic refractive index profiling of direct laser written waveguides."* (Optics Express 29, no. 22 (2021): 35414-35425).

## 📁 Repository Structure
```text
OCT Project/
├── tests/
│   ├── test i/
│   │   ├── backgrounds/          # Illumination profiles without the sample
│   │   ├── debug/                # Intermediate preprocessing outputs
│   │   ├── samples/              # Raw waveguide images
│   │   ├── dark/                 # Raw dark images, without lightsource
│   │   ├── angles (rad).npy      # Recorded mirror angles
│   │   ├── reconstructing.ipynb  # Test-specific Julia reconstruction notebook
│   │   └── tomogram_guide.jld    # Extracted 1D intensity profiles (HDF5)
├── utils/
│   ├── julia/
│   │   ├── model.jl              # Physical modeling for reconstruction
│   │   ├── proximal_optim.jl     # Optimization routines
│   │   └── TV_prox.jl            # Total Variation (TV) proximal operators
│   └── thorlabs/
│       ├── dlls/                 # Thorlabs SDK dynamic libraries
│       ├── kinesis.py            # Custom wrapper for Kinesis TDC001 servo control
│       └── thorcam.py            # Thorlabs scientific camera interface
├── preprocessing.py              # Parallelized tomogram generation script
└── shooting.py                   # Automated optical scanning script
```

## ⚙️ Core Components

### 1. Automated Data Acquisition (`shooting.py`)
This script automates the tomographic scanning process. It interfaces directly with the physical setup, rotating a mirror to specific angular steps and capturing frames via software triggers.
*   **Hardware Interfacing:** Utilizes the Thorlabs SDK for camera operation (`thorcam.py`) and a custom-written Python wrapper (`kinesis.py`) to manage the Kinesis TDC001 motor controller.
*   **Modes of Operation:** Supports capturing Waveguide (sample), Background, and Dark (sensor noise) image sets.

### 2. Data Preprocessing (`preprocessing.py`)
This script cleans the raw 2D images and extracts the intensity map required for the Julia reconstruction.
*   **Noise Reduction:** Performs dark frame subtraction, averages multiple frames per angle, and applies median filtering (size 3).
*   **Parallel Processing:** Uses `concurrent.futures.ProcessPoolExecutor` to drastically reduce processing time by chunking image operations across available CPU cores.
*   **Data Export:** Averages the 2D images along a specified y-axis band to generate a 1D intensity profile (I_k) per angle, exporting the final aggregated 2D `I_map`, pixel pitch (`dx`), and angles (`θ_l`) into a `tomogram_guide.jld` file.

### 3. Refractive Index Reconstruction (`reconstructing.ipynb`)
Each `test` directory contains a dedicated Jupyter notebook running a Julia kernel to process the `.jld` file outputted by the preprocessing stage. 
*   **Optimization Algorithm:** Utilizes the Fast Iterative Shrinkage-Thresholding Algorithm (FISTA) combined with Total Variation (TV) proximal operators to iteratively solve for the refractive index and correct optical aberrations.
*   **Test-Specific Tuning:** Parameters such as the angular sample range (`l_i`), angular offset correction (`θ_l_i`), and spatial cropping constraints (`ncut`) are exposed in the notebook to allow for manual adjustments based on the physical alignment of that specific scan.

## 🚀 Setup and Usage

### Prerequisites
*   **Python 3.x:** `numpy`, `scipy`, `imageio`, `h5py`, `matplotlib`.
*   **Julia 1.12+:** `FFTW`, `JLD`, `PyPlot`, `ProgressMeter`.
*   **Hardware:** Thorlabs Scientific Camera, Kinesis TDC001 Controller.

### Execution Workflow
1.  **Acquisition:** Configure the target test directory and angular range in `shooting.py`. Run the script three separate times, changing the `MODE` constant to capture Waveguide, Background, and Dark images.
2.  **Preprocessing:** Ensure `TEST_NUMBER` in `preprocessing.py` matches your target directory. Run the script to generate the `tomogram_guide.jld` file.
3.  **Reconstruction:** Open the `reconstructing.ipynb` file inside the specific test directory. Adjust the angular offset (`θ_l_i`) and crop values (`ncut`) as needed, then execute the cells to generate the final cross-section visualization.

## 📚 References
*   Barré, N., Shivaraman, R., Ackermann, L., Moser, S., Schmidt, M., Salter, P., Booth, M., & Jesacher, A. (2021). *Tomographic refractive index profiling of direct laser written waveguides.* Optics Express, 29(22), 35414-35425.
=======
# Tomographic Refractive Index Profiling of FLDW Waveguides

This repository contains the software ecosystem for automating data acquisition and performing refractive index reconstruction of femtosecond laser direct written (FLDW) waveguides. The system is split into a Python-based hardware control and preprocessing pipeline, and a Julia-based mathematical reconstruction backend.

The reconstruction methodology implemented in this project is based on the work described by Nicolas Barré et al. in *"Tomographic refractive index profiling of direct laser written waveguides."* (Optics Express 29, no. 22 (2021): 35414-35425).

## 📁 Repository Structure

OCT Project/
├── tests/
│   ├── test i/
│   │   ├── backgrounds/          # Illumination profiles without the sample
│   │   ├── debug/                # Intermediate preprocessing outputs
│   │   ├── samples/              # Raw waveguide images
│   │   ├── dark/                 # Raw dark images, without lightsource
│   │   ├── angles (rad).npy      # Recorded mirror angles
│   │   ├── reconstructing.ipynb  # Test-specific Julia reconstruction notebook
│   │   └── tomogram_guide.jld    # Extracted 1D intensity profiles (HDF5)
├── utils/
│   ├── julia/
│   │   ├── model.jl              # Physical modeling for reconstruction
│   │   ├── proximal_optim.jl     # Optimization routines
│   │   └── TV_prox.jl            # Total Variation (TV) proximal operators
│   └── thorlabs/
│       ├── dlls/                 # Thorlabs SDK dynamic libraries
│       ├── kinesis.py            # Custom wrapper for Kinesis TDC001 servo control
│       └── thorcam.py            # Thorlabs scientific camera interface
├── preprocessing.py              # Parallelized tomogram generation script
└── shooting.py                   # Automated optical scanning script


## ⚙️ Core Components

### 1. Automated Data Acquisition (`shooting.py`)
This script automates the tomographic scanning process. It interfaces directly with the physical setup, rotating a mirror to specific angular steps and capturing frames via software triggers.
*   **Hardware Interfacing:** Utilizes the Thorlabs SDK for camera operation (`thorcam.py`) and a custom-written Python wrapper (`kinesis.py`) to manage the Kinesis TDC001 motor controller.
*   **Modes of Operation:** Supports capturing Waveguide (sample), Background, and Dark (sensor noise) image sets.

### 2. Data Preprocessing (`preprocessing.py`)
This script cleans the raw 2D images and extracts the intensity map required for the Julia reconstruction.
*   **Noise Reduction:** Performs dark frame subtraction, averages multiple frames per angle, and applies median filtering (size 3).
*   **Parallel Processing:** Uses `concurrent.futures.ProcessPoolExecutor` to drastically reduce processing time by chunking image operations across available CPU cores.
*   **Data Export:** Averages the 2D images along a specified y-axis band to generate a 1D intensity profile (I_k) per angle, exporting the final aggregated 2D `I_map`, pixel pitch (`dx`), and angles (`θ_l`) into a `tomogram_guide.jld` file.

### 3. Refractive Index Reconstruction (`reconstructing.ipynb`)
Each `test` directory contains a dedicated Jupyter notebook running a Julia kernel to process the `.jld` file outputted by the preprocessing stage. 
*   **Optimization Algorithm:** Utilizes the Fast Iterative Shrinkage-Thresholding Algorithm (FISTA) combined with Total Variation (TV) proximal operators to iteratively solve for the refractive index and correct optical aberrations.
*   **Test-Specific Tuning:** Parameters such as the angular sample range (`l_i`), angular offset correction (`θ_l_i`), and spatial cropping constraints (`ncut`) are exposed in the notebook to allow for manual adjustments based on the physical alignment of that specific scan.

## 🚀 Setup and Usage

### Prerequisites
*   **Python 3.x:** `numpy`, `scipy`, `imageio`, `h5py`, `matplotlib`.
*   **Julia 1.12+:** `FFTW`, `JLD`, `PyPlot`, `ProgressMeter`.
*   **Hardware:** Thorlabs Scientific Camera, Kinesis TDC001 Controller.

### Execution Workflow
1.  **Acquisition:** Configure the target test directory and angular range in `shooting.py`. Run the script three separate times, changing the `MODE` constant to capture Waveguide, Background, and Dark images.
2.  **Preprocessing:** Ensure `TEST_NUMBER` in `preprocessing.py` matches your target directory. Run the script to generate the `tomogram_guide.jld` file.
3.  **Reconstruction:** Open the `reconstructing.ipynb` file inside the specific test directory. Adjust the angular offset (`θ_l_i`) and crop values (`ncut`) as needed, then execute the cells to generate the final cross-section visualization.

## 📚 References
*   Barré, N., Shivaraman, R., Ackermann, L., Moser, S., Schmidt, M., Salter, P., Booth, M., & Jesacher, A. (2021). *Tomographic refractive index profiling of direct laser written waveguides.* Optics Express, 29(22), 35414-35425.
