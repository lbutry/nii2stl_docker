import os
import shutil
import sys 
import argparse
import logging
import pymeshlab
import numpy as np
import nibabel.freesurfer as fsio

#===========================================================#
# SETUP ARGUMENTS PARSER & LOGGING
#===========================================================#

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Set parser
parser = argparse.ArgumentParser()

parser.add_argument('-t1w', type=str, help='Name of the T1w-image (.nii or .nii.gz) inside the home directory.')
parser.add_argument('-fs_skip', action='store_true', help="Skip FreeSurfer's 'recon-all' pipeline. Checks if 'segment_subregion brainstem' needs to be run. Requires FreeSurfer output to be located in home directory.")
parser.add_argument('-fs_flags', type=str, default = '', help="Parse more flags to 'recon-all'")
parser.add_argument('-fs_dir', type=str, default = None, help="Name of FreeSurfer output directory. [Default: 'freesurfer']")
parser.add_argument('-smooth', type=int, default = 150, help="Number of smoothing steps for subcortical model. Use '0' to disable. [Default: 150]")
parser.add_argument('-decimate', type=float, default = 200000, help="Target number of faces. Use '0' to disable. [Default: 200000]")
parser.add_argument('-hemi', action='store_true', help='Create STL files for each hemisphere.')
parser.add_argument('-planeoffset', type=float, default=None, help='Indicate where the subcotical model is cut in half on the x-axis. Only applicable when -hemi is set.')
parser.add_argument('-rev_overlap_correction', action='store_true', help='Indicate if hemi overlap correction should swap the subtraction terms.')
parser.add_argument('-work', action='store_true', help='Keep work directory.')
parser.add_argument('-tag', type=str, default = None, help='Tag for the output folders. [Defaut: None]')

## BETA arguments
parser.add_argument('-wm', action='store_true', help='Create STL file for cerebral white matter.')
parser.add_argument('-parcels', action='store_true', help='Create STL files for each parcel of the Desikan-Killiany Atlas and for each brain lobe.')

args = parser.parse_args()

#===========================================================#
# CREATE WORK & OUTPUT DIRECTORY, SET ENV VARIABLES
#===========================================================#

# Set directories paths (inside share folder between docker & host)
share_dir  = os.path.join(os.getcwd(), 'share')
work_dir   = os.path.join(share_dir, 'work')
output_dir = os.path.join(share_dir, 'output')

# Handle tag argument
if args.tag:
    work_dir = work_dir + '_' + args.tag
    output_dir = output_dir + '_' + args.tag

if not args.fs_dir:
    args.fs_dir = 'freesurfer'
    if args.tag:
        args.fs_dir = args.fs_dir + '_' + args.tag

# Create directories if they don't exist
os.makedirs(work_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# Set environmental varibales
os.environ['FS_LICENSE'] = '/app/share/license.txt'
os.environ['SUBJECTS_DIR'] = share_dir

#===========================================================#
# VALIDATE ARGUMENTS & FILES
#===========================================================#

if not args.fs_skip and not args.t1w:
    logging.error('The following arguments are required: -t1w (unless -fs_skip is set)')
    sys.exit(1)

if not os.path.exists('/app/share/license.txt'):
    logging.error("The FreeSurfer's 'license.txt' file is missing in the home directory")
    sys.exit(1)

if args.fs_skip:
    required_files = [f'/app/share/{args.fs_dir}/surf/lh.pial', f'/app/share/{args.fs_dir}/surf/rh.pial', f'/app/share/{args.fs_dir}/mri/aseg.mgz']
    if any(not os.path.exists(file) for file in required_files):
        logging.error("The FreeSurfer output folder is missing in the home directory or does not contain segmentation data from 'recon-all'.")
        sys.exit(1)
        
#===========================================================#
# RUN FREESURFER RECON-ALL & SEGMENT_SUBREGIONS
#===========================================================#

if not args.fs_skip:

    print('## RUN RECON-ALL & SEGMENT_SUBREGIONS ##')
    print(f'## INPUT FILE: {args.t1w} ##')    

    os.system(f'recon-all -i share/{args.t1w} -subjid {args.fs_dir} -nuintensitycor -all {args.fs_flags} -parallel')
    os.system(f'segment_subregions brainstem --cross {args.fs_dir}')

if args.fs_skip:
    print('## SKIP RECON-ALL ##')

    if not os.path.exists(f'/app/share/{args.fs_dir}/mri/brainstemSsLabels.FSvoxelSpace.mgz'):
        print('## BRAINSTEM SEGMENTATION MISSING IN FREESURFER OUTPUT. RUNNING SEGMENT_SUBREGIONS: ##')
        os.system(f'segment_subregions brainstem --cross {args.fs_dir}')

#===========================================================#
# CREATE CORTICAL MODEL
#===========================================================#

print('## CREATE CORTICAL AND SUBCORTICAL MODEL ##')

lh_pial = os.path.join(share_dir, f'{args.fs_dir}/surf/lh.pial')
rh_pial = os.path.join(share_dir, f'{args.fs_dir}/surf/rh.pial')
cortical_stl = os.path.join(output_dir, 'cortical_final.stl')
os.system(f'mris_convert --combinesurfs {lh_pial} {rh_pial} {cortical_stl}')

#===========================================================#
# CREATE SUBCORTICAL MODEL
#===========================================================#

def mgz2stl(input_mgz, output_prefix, match_values):
    mgz = os.path.join(share_dir, input_mgz)
    bin = os.path.join(work_dir, f'{output_prefix}_bin.nii.gz')
    surf = os.path.join(work_dir, f'{output_prefix}.pial')
    stl = os.path.join(work_dir, f'{output_prefix}.stl')
    os.system(f'mri_binarize --i {mgz} --match {match_values} --o {bin}')
    os.system(f'mri_tessellate {bin} 1 {surf}')
    os.system(f'mris_convert {surf} {stl}')

# Cerebellum, Thalamus, VentralDC, Fornix, Corpus callosum
sub_stl = os.path.join(work_dir, 'sub.stl')
mgz2stl(f'{args.fs_dir}/mri/aseg.mgz', 'sub', '6 7 8 10 28 45 46 47 49 60 250 251 252 253 254 255')

# Brainstem
brainstem_stl = os.path.join(work_dir, 'brainstem.stl')
mgz2stl(f'{args.fs_dir}/mri/brainstemSsLabels.FSvoxelSpace.mgz', 'brainstem', '170 171 172 173 174 175 177 178 179')

## Ventricels (for subtraction)
ventricle_stl = os.path.join(work_dir, 'ventricles.stl')
mgz2stl(f'{args.fs_dir}/mri/aseg.mgz', 'ventricles', '4 14 15 43 72')

#===========================================================#
# MESH PROCESSING VIA PYMESHLAB
#===========================================================#

print('## APPLY MESH PROCESSING VIA PYMESHLAB ##')

# Combine subcortical & brainstem
ms = pymeshlab.MeshSet()
ms.load_new_mesh(brainstem_stl)
ms.load_new_mesh(sub_stl)
ms.mesh_boolean_union()

# Subtract ventricle from subcortical
ms.load_new_mesh(ventricle_stl)
ms.mesh_boolean_difference(first_mesh=2, second_mesh=3)
subcortical_stl = os.path.join(output_dir, 'subcortical_final.stl')
ms.save_current_mesh(subcortical_stl)

def process_mesh(mesh_stl):
    ## Resolve non-manifold mesh
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(mesh_stl)
    ms.uniform_mesh_resampling(cellsize=pymeshlab.Percentage(1))
    ms.remove_isolated_pieces_wrt_diameter()
    ms.save_current_mesh(mesh_stl)

    # Smooth
    if args.smooth and mesh_stl == subcortical_stl:
        ms.scaledependent_laplacian_smooth(stepsmoothnum=args.smooth, delta=pymeshlab.Percentage(0.1))
        ms.save_current_mesh(mesh_stl)

process_mesh(subcortical_stl)
process_mesh(ventricle_stl)

# Subtract ventricles from cortical & smooth
ms = pymeshlab.MeshSet()
ms.load_new_mesh(cortical_stl)
ms.load_new_mesh(ventricle_stl)
ms.mesh_boolean_difference(first_mesh=0, second_mesh=1)
ms.laplacian_smooth(stepsmoothnum=2)
ms.save_current_mesh(cortical_stl)

# Combine subcortical & cortical model
ms = pymeshlab.MeshSet()
ms.load_new_mesh(cortical_stl)
ms.load_new_mesh(subcortical_stl)
ms.flatten_visible_layers()

# Decimate combined model
if args.decimate:
    ms.simplification_quadric_edge_collapse_decimation(targetfacenum=int(args.decimate), preserveboundary=True, preservetopology=True, boundaryweight=2)

# Clean model
ms.close_holes()
ms.remove_isolated_pieces_wrt_diameter()

# Save final model
final_stl = os.path.join(output_dir, 'brain_final.stl')
ms.save_current_mesh(final_stl)

#===========================================================#
# CREATE MODEL FOR WHITE MATTER
#===========================================================#

if args.wm:

    # Create output folder
    wm_dir = os.path.join(output_dir, 'wm')
    os.makedirs(wm_dir, exist_ok=True)
    
    # Create WM model
    wm_stl = os.path.join(work_dir, 'wm.stl')
    mgz2stl(f'{args.fs_dir}/mri/aseg.mgz', 'wm', '2 41 250 251 252 253 254 255')

    # Process mesh
    process_mesh(wm_stl)
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(wm_stl)
    ms.scaledependent_laplacian_smooth(stepsmoothnum=120, delta=pymeshlab.Percentage(0.))
    wm_final = os.path.join(wm_dir, 'wm.stl')
    ms.save_current_mesh(wm_final)

#===========================================================#
# CREATE MODEL FOR EACH HEMISPHERE
#===========================================================#

if args.hemi:

    print('## CREATE MODEL FOR EACH HEMISPHERE ##')

    # Create output folder
    hemi_dir = os.path.join(output_dir, 'hemi')
    os.makedirs(hemi_dir, exist_ok=True)

    # Cortical model
    lh_stl = os.path.join(hemi_dir, 'left_hemi.stl')
    rh_stl = os.path.join(hemi_dir, 'right_hemi.stl')
    os.system(f'mris_convert {lh_pial}  {lh_stl}')
    os.system(f'mris_convert {rh_pial}  {rh_stl}')

    # Get value for 'planeoffset' argument (middle of whole brain model)
    offset_x = args.planeoffset if args.planeoffset is not None else ms.compute_geometric_measures()['center_of_mass'][0]

    # Split subcortical model in half
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(subcortical_stl)
    ms.compute_planar_section(planeoffset=offset_x, splitsurfacewithsection=True, createsectionsurface=True)

    ms.set_current_mesh(2)
    section = os.path.join(work_dir, 'section.stl')
    ms.save_current_mesh(section)
    ms.set_current_mesh(3)
    right_subc = os.path.join(work_dir, 'right_subc.stl')
    ms.save_current_mesh(right_subc)
    ms.set_current_mesh(4)
    left_subc = os.path.join(work_dir, 'left_subc.stl')
    ms.save_current_mesh(left_subc)

    ## Close the cut
    def process_splitted_subcortical(subc_stl):
        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(section)

        # Check face orientation of section & invert face orientation if necessary
        normals = ms.current_mesh().face_normal_matrix()[:, 0]
        normals_negative = np.all(normals < 0)
        if (normals_negative and subc_stl == left_subc) or (not normals_negative and subc_stl == right_subc):
            ms.invert_faces_orientation()

        # Combine section & subcortical half
        ms.load_new_mesh(subc_stl)
        ms.flatten_visible_layers()
        ms.save_current_mesh(subc_stl)

    process_splitted_subcortical(left_subc)
    process_splitted_subcortical(right_subc)

    # Smooth cortical model; Combine subcortical & cortical model of each hemisphere; clean edge between hemispheres
    def process_hemi(hemi_stl, subc_stl, colat_subc):
        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(hemi_stl)
        ms.load_new_mesh(ventricle_stl)
        ms.mesh_boolean_difference(first_mesh=0, second_mesh=1)
        ms.laplacian_smooth(stepsmoothnum=2)
        ms.load_new_mesh(subc_stl)
        ms.mesh_boolean_union(first_mesh=2, second_mesh=3)
        ms.load_new_mesh(colat_subc)
        ms.mesh_boolean_difference(first_mesh=4, second_mesh=5)
        ms.save_current_mesh(hemi_stl)

    process_hemi(lh_stl, left_subc, right_subc)
    process_hemi(rh_stl, right_subc, left_subc)

    # Clean hemisphere models
    def clean_hemi(hemi_stl):
        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(hemi_stl)
        ms.remove_isolated_pieces_wrt_diameter()
        ms.save_current_mesh(hemi_stl)

    clean_hemi(lh_stl)
    clean_hemi(rh_stl)

    # Stop hemis from overlapping (by computing difference)
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(lh_stl)
    ms.load_new_mesh(rh_stl)
    if args.rev_overlap_correction:
        ms.mesh_boolean_difference(first_mesh=0, second_mesh=1)
        ms.save_current_mesh(lh_stl)
    else:
        ms.mesh_boolean_difference(first_mesh=1, second_mesh=0)
        ms.save_current_mesh(rh_stl)

#===========================================================#
# CREATE MODEL FOR EACH CORTICAL PARCEL & LOBE
#===========================================================#

if args.parcels:

    print('## CREATE MODEL FOR EACH CORTICAL PARCEL & LOBE ##')

    # Create folders
    pial_dir    = os.path.join(work_dir, 'pial')
    parcels_dir = os.path.join(output_dir, 'parcels')
    lobes_dir = os.path.join(output_dir, 'lobes')
    os.makedirs(pial_dir, exist_ok=True) 
    os.makedirs(parcels_dir, exist_ok=True) 
    os.makedirs(lobes_dir, exist_ok=True) 

    # Function to parcellate .pial & convert to .stl
    def pial2stl(pial_file, hemi):
        vertices, faces = fsio.read_geometry(pial_file)
        annot = os.path.join(share_dir, f"{args.fs_dir}/label/{hemi}.aparc.annot")
        labels, ctab, names = fsio.read_annot(annot)

        # Loop over all parcels in names
        for parcel_name in names:
            parcel_idx = names.index(parcel_name)  # No need to encode since names are already in bytes
            parcel_vertices = np.where(labels == parcel_idx)[0]
            parcel_faces = faces[np.all(np.isin(faces, parcel_vertices), axis=1)]
            remapped_faces = np.searchsorted(parcel_vertices, parcel_faces)
            parcel_surf = os.path.join(pial_dir, parcel_name.decode() + '.pial')
            fsio.write_geometry(parcel_surf, vertices[parcel_vertices], remapped_faces)
            parcel_mesh = os.path.join(output_dir, 'parcels', f"{hemi}_{parcel_name.decode()}.stl")
            os.system(f"mris_convert {parcel_surf} {parcel_mesh}")
            print(f"created STL file for {parcel_name.decode()}")

    # Run pial2stl for each hemisphere
    pial2stl(lh_pial, 'lh')
    pial2stl(rh_pial, 'rh')

    # Define lobes
    lobe_dict = {
    'frontal': ['superiorfrontal', 'rostralmiddlefrontal', 'caudalmiddlefrontal', 'parsopercularis', 'parstriangularis', 'parsorbitalis', 'lateralorbitofrontal', 'medialorbitofrontal', 'precentral', 'paracentral', 'frontalpole'],
    'parietal': ['superiorparietal', 'inferiorparietal', 'supramarginal', 'postcentral', 'precuneus'],
    'temporal': ['parahippocampal', 'temporalpole', 'entorhinal', 'transversetemporal', 'fusiform', 'bankssts', 'inferiortemporal', 'middletemporal', 'superiortemporal'],
    'occipital': ['lateraloccipital', 'lingual', 'cuneus', 'pericalcarine'],
    'cingulate': ['caudalanteriorcingulate', 'isthmuscingulate', 'posteriorcingulate', 'rostralanteriorcingulate']
    }
   
    # Combine parcels to lobes
    for lobe_name, lobe in lobe_dict.items():

        for hemi in ['lh', 'rh']:
            ms = pymeshlab.MeshSet()

            for region in lobe:
                path_stl = os.path.join(parcels_dir, f'{hemi}_{region}.stl')
                ms.load_new_mesh(path_stl)

            ms.flatten_visible_layers()
            ms.save_current_mesh(os.path.join(lobes_dir, f'{hemi}_lobe-{lobe_name}.stl'))

#===========================================================#
# TIDY UP
#===========================================================#

# Remove work directory
if args.work:
    print(f'## Keeping work directory ##')
else:
    shutil.rmtree(work_dir)

# End text
print('''
    #================================================#
    #                SCRIPT FINISHED                 #
    #================================================#
''')

if args.smooth:
    print(f'## Smoothed subcortical model with {args.smooth} steps')

if args.decimate:
    print(f"## Decimated 'brain_final.stl' to {args.decimate} faces")

if args.hemi:
    print(f'## The subcortical model was split at x-planeoffset: {offset_x}')

    if args.rev_overlap_correction:
        print('## The right hemisphere is subtracted from the left hemisphere.')
    else:
        print('## The left hemisphere is subtracted from the right hemisphere.')