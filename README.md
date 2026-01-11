# 3D-printable brain model from a T1w MR image using Docker

You want to 3D print your or another ones brain? Here's a step by step guide on how to end up with a 3D-printable brain model. It's as easy as running two command lines. This is an adaptation and extension of [skjerns/3dprintedbrain_docker](https://github.com/skjerns/3dprintedbrain_docker) and [miykael/3dprintyourbrain](https://github.com/miykael/3dprintyourbrain) with more options, ease of use and enhanced anatomical accuracy.

**What you need**
- Structural brain image (T1-weighted) in NIfTI-format
- FreeSurfer license (it's free; see [Installation](#installation))
- Installation of 'Docker Desktop' (see [Installation](#installation))
- 21 GB of free disk space

## Features
- Simple installation and usage - just two commands to get started.
- Compatible with pre-existing FreeSurfer [7.3+] output.
- Enhanced anatomical accuracy by leveraging both FreeSurfer's 'recon-all' and 'segment_subregions' pipelines, as well as by integrating ventricles.
- Generates print-ready STL files for subcortical structures, cortical regions, and the whole brain.
- Option to create a separate STL file for each hemisphere.
- [BETA] Option to generate STL files for parcels of the Desikan-Killiany Atlas and brain lobes.
- [BETA] Option to generate STL file for cerebral white matter.
- Smaller Docker image (20.46 GB)
- Technical feature: No longer requires FSL as a dependency (saving 10 GB of space).
- Technical feature: Runs entirely from a single Python file.

## Installation

### 1. Get a Freesurfer license (it's free)

Register on the [Harvard FreeSurferWiki](https://surfer.nmr.mgh.harvard.edu/fswiki/License) with your email and get a free Freesurfer 'license.txt' file.

### 2. Install 'Docker Desktop'

Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/). It is free of charge and availabe for Mac, Windows and Linux.

### 3. Pull the Docker image

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

## Usage

### Set up home directory

1) Create a new folder (e.g. named 'home')
2) Copy your FreeSurfer 'license.txt' file and your brain T1w image (.nii or .nii.gz) into the folder.

> [!NOTE]
> The following instructions assume that your brain T1w image is named 'brain.nii.gz'. If your file has a different name, please adjust the commands accordingly.

### Run the Docker container
3) Navigate inside the terminal to the folder: `cd /path/to/folder`
4) Run the command below:

**Usage** `docker run -t -v ./:/app/share <image name> <options>`

**Example for default use**
- Mac/Linux: `docker run -t -v ./:/app/share lbutry/nii2stl -t1w brain.nii.gz`
- Windows: `docker run -t -v .\/:/app/share lbutry/nii2stl -t1w brain.nii.gz`

> [!TIP]
> The default run will take several hours to complete due to FreeSurfer's 'recon-all' processing time. If you already have FreeSurfer output, consider using the `-fs_skip` option to skip this step.

**Example using additional options**

All options are listed at section [Arguments and options](#arguments-and-options). If you want to skip FreeSurfer (`-fs_skip`), use custom brainstem smoothing (`-smoothing`) and obtain an STL file for each hemisphere (`-hemi`), use the following command:
- Mac/Linux: `docker run -t -v ./:/app/share lbutry/nii2stl -fs_skip -smoothing 0 -hemi`
- Windows: `docker run -t -v .\/:/app/share lbutry/nii2stl -fs_skip -smoothing 0 -hemi`

# Arguments and options

**General options**

- `-work` Keep work directory. 
- `-tag <tag>` If set, `_<tag>` is appended to the output and FreeSurfer folder. When `-fs_skip` is additionally set, the FreeSurfer output directory with the according tag is used. [Defaut: None]

> [!TIP]
> Use the `-tag` option to keep multiple outputs organised. For example, if you want to use _nii2stl_ on different T1w images, you can run the script multiple times with different `-tag` values. Each output will be saved in a separate folder. Also handels pre-existing FreeSurfer output.

**Mandatory for default use**

- `-t1w <file name>` Name of the T1w-image (.nii or .nii.gz) inside the home directory.

**Freesurfer options**

- `-fs_skip` Skip FreeSurfer's 'recon-all' pipeline. Checks if 'segment_subregion brainstem' needs to be run. Requires FreeSurfer output to be located in home directory.
- `-fs_dir <folder name>` Name of FreeSurfer output directory. [Default = freesurfer]"
- `-fs_flags <flags>` Parse more flags to [recon-all](https://surfer.nmr.mgh.harvard.edu/fswiki/recon-all).

**Optional modules**

- `-hemi` Create STL-file for each hemisphere. Including brainstem, cerebellum and corpus callosum.
- `-parcels` [BETA] Create STL-file for each parcel of the Desikan-Killiany Atlas and for each brain lobe.
- `-wm` [BETA] Create STL-file for cerebral white matter.

**Mesh processing options**

- `-smooth <int>` Number of smoothing steps for subcortical model. Use '0' to disable. [Default = 150]
- `-decimate <float>` Target number of faces. Use '0' to disable. [Default = 200000]
- `-planeoffset` Indicate where the subcotical model is cut in half on the x-axis. Only applicable when -hemi is set.
- `-rev_overlap_correction` Swap subtraction terms in hemi overlap correction. Only applicable when -hemi is set.

## Output

All outputs are saved in the home directory.

- `home/freesurfer/...` Segmentation output of FreeSurfer.
- `home/output/brain_final.stl` 3D-printable STL model of the whole brain.
- `home/output/cortical_final.stl` 3D-printable STL model of the cerebrum.
- `home/output/subcortical_final.stl` 3D-printable model of the brainstem and cerebellum.
- `home/output/hemi/...` 3D-printable STL model for both hemispheres.
- `home/output/lobes/...` 3D-printable STL model for each brain lobe.
- `home/output/parcels/...` 3D-printable STL model for each parcel of the Desikan-Killiany Atlas.

# Q & A

**Q1: My MR images are in DICOM format and not in .nii or nii.gz.**
- You can convert DICOM to NIfTI using [dcm2niix](https://github.com/rordenlab/dcm2niix).

**Q2: I already have the output of FreeSurfer's 'recon-all'. How can I use it?**
1) Copy the FreeSurfer output folder to the home directory.
2) Now you have two options: 
    - (a) Rename the folder to 'freesurfer' (or 'freesurfer_>tag<' when using the `-tag` flag).
    - (b) Use the `-fs_dir` flag to specify the name of your FreeSurfer output directory.
3) Use the `-fs_skip` option to skip the 'recon-all' pipeline.

**Q3: I already have the output of FreeSurfer 'recon-all' but not of 'segment_subregion brainstem'.**
- Just follow the instructions of Q2 and use the `-fs_skip` option. The script will check if 'segment_subregion brainstem' needs to be run and do it if necessary.
