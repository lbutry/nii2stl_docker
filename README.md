# 3D-printable brain model from a T1w MR image using Docker

You want to 3D print your or another ones brain? Here's a step by step guide on how to end up with a 3D-printable brain model. It's as easy as running two command lines. This is an adaptation and extension of [skjerns/3dprintedbrain_docker](https://github.com/skjerns/3dprintedbrain_docker) and [miykael/3dprintyourbrain](https://github.com/miykael/3dprintyourbrain) with more options and ease of use.

**What you need**
- Structural brain image (T1-weighted) in NIfTI-format
- FreeSurfer license (it's free; see Instructions)
- Installation of 'Docker Desktop' (see Instructions)

# Features
- Easy installation & command usage (just two commands)
- Also works with previously generated FreeSurfer output.
- More accurate subcortical segmentation by not only utilizing FreeSurfer's 'recon-all' but also 'segment_subregions'.
- Option to obtain an STL-file for each parcel of the Desikan-Killiany Atlas and for each brain lobe. [BETA]
- Outputs a subcortical, cortical and whole brain STL-file.
- Smaller Docker image (20.46 GB)
- Options to control subcortical smoothing and overall number of faces.
- Technical feature: Does not require FSL anymore
- Technical feature: Program is run from one python file.

# Instructions

## 1. Get a Freesurfer license (it's free)

Register on the [Harvard FreeSurferWiki](https://surfer.nmr.mgh.harvard.edu/fswiki/License) with your email and get a free Freesurfer 'license.txt' file.

## 2. Install 'Docker Desktop'

Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/). It is free of charge and availabe for Mac, Windows and Linux.

## 3. Pull the Docker image

**Option A: via Terminal**

Open the terminal and run: `docker image pull lbutry/nii2stl:latest`

**Option B: via Docker Desktop app**
1) Open 'Docker Desktop'
2) Navigate to the search bar at the top and type 'lbutry/nii2stl'.
3) Click on 'Pull' to download the image.

**Option C: Build manually from this repository**
1) Clone this repository
2) Open the repository folder with the terminal
3) Run `docker build -t nii2stl .`

## 4. Run the Docker image

1) Create a new folder (e.g.: home)
2) Copy your FreeSurfer 'license.txt' file and your brain T1w image (.nii or .nii.gz) into the folder
3) Navigate inside the terminal to the folder: `cd /path/to/folder`

**Usage:** `docker run -t -v ./:/app/share <image> <options>`

**Example for default use**
- Mac/Linux: `docker run -t -v ./:/app/share lbutry/nii2stl -t1w brain.nii.gz`
- Windows: `docker run -t -v .\/:/app/share lbutry/nii2stl -t1w brain.nii.gz`

**Example for advanced use**

This code is required if you want to skip FreeSurfer, use custom brainstem smoothing and obtain an STL file for each brain lobe:
- Mac/Linux: `docker run -t -v ./:/app/share lbutry/nii2stl -fs_skip -smoothing 0 -parcels`
- Windows: `docker run -t -v .\/:/app/share lbutry/nii2stl -fs_skip -smoothing 0 -parcels`

### Arguments and options

- `-t1w` Name of the T1w-image (.nii or .nii.gz) inside the home directory.
- `-fs_skip` Skip FreeSurfer's 'recon-all' and 'segment_subregion brainstem' pipeline. Requires FreeSurfer output to be located in home directory.
- `-fs_only_brainstem` Perform 'segment_subregion brainstem' and skip 'recon-all'. Requires FreeSurfer output to be located in home directory.
- `-fs_flags` Parse more flags to 'recon-all'.
- `-smooth` Number of smoothing steps. Use '0' to disable. [Default = 150]
- `-decimate` Target number or percentage of faces. Use '0' to disable. [Default = 290000]
- `-parcels` Create STL-files for each parcel of the Desikan-Killiany Atlas and for each brain lobe.

### Output

All outputs are saved in the home directory.

- `home/freesurfer` Segmentation output of FreeSurfer.
- `home/output/brain_final.stl` 3D-printable model of the whole brain.
- `home/output/cortical_final.stl` 3D-printable model of the cerebrum.
- `home/output/subcortical_final.stl` 3D-printable model of the brainstem and cerebellum.
- `home/output/lobes` STL-files for each brain lobe.
- `home/output/parcels` STL-files for each parcel of the Desikan-Killiany Atlas.

# Q & A

1) My MR images are in DICOM format and not in .nii or nii.gz.
- You can convert DICOM to NIfTI using [dcm2niix](https://github.com/rordenlab/dcm2niix).

2) I already have the output of FreeSurfer 'recon-all' and 'segment_subregion brainstem'. How can I use it?
- Copy the output to the home directory and rename it to 'freesurfer'. You should now use the '-fs_skip' flag.

3) I already have the output of FreeSurfer 'recon-all' but not of 'segment_subregion brainstem'. 
- Copy the output to the home directory and rename it to 'freesurfer'. You should now use the '-fs_only_brainstem' flag.
