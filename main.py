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
parser.add_argument('-fs_skip', action='store_true', help="Skip FreeSurfer's 'recon-all' and 'segment_subregion brainstem' pipeline. Requires FreeSurfer output to be located in home directory.")
parser.add_argument('-fs_only_brainstem', action='store_true', help="Perform 'segment_subregion brainstem' and skip 'recon-all'. Requires FreeSurfer output to be located in home directory.")
parser.add_argument('-fs_flags', type=str, default = '', help="Parse more flags to 'recon-all'")
parser.add_argument('-smooth', type=int, default = 150, help="Number of smoothing steps for subcortical model. Use '0' to disable")
parser.add_argument('-decimate', type=float, default = 150000, help="Target number of faces. Use '0' to disable")
parser.add_argument('-parcels', action='store_true', help='Create STL files for each parcel of the Desikan-Killiany Atlas and for each brain lobe.')
parser.add_argument('-hemi', action='store_true', help='Create STL files for each hemissphere.')
parser.add_argument('-planeoffset', type=float, default=None, help='Indicates where the subcotical model is cut in half on the x-axis. Only applicable when -hemi is set.')
parser.add_argument('-work', action='store_true', help='Keep work directory.')

args = parser.parse_args()

# Validate arguments & files
if not (args.fs_skip or args.fs_only_brainstem) and not args.t1w:
    logging.error('The following arguments are required: -t1w (unless -fs_skip is set)')
    sys.exit(1)

if not os.path.exists('/app/share/license.txt'):
    logging.error("The FreeSurfer's 'license.txt' file is missing in the home directory")
    sys.exit(1)

if args.fs_skip:
    if not os.path.exists('/app/share/freesurfer/mri/brainstemSsLabels.FSvoxelSpace.mgz'):
        logging.error("The folder 'freesurfer' is missing in the home directory or does not contain segmentation data from 'recon-all' & 'segment_subregions brainstem'")
        sys.exit(1)

if args.fs_only_brainstem:
    if not os.path.exists('/app/share/freesurfer/surf/lh.pial'):
        logging.error("The folder 'freesurfer' is missing in the home directory or does not contain segmentation data from 'recon-all'")
        sys.exit(1)
        
#===========================================================#
# CREATE WORK & OUTPUT DIRECTORY, SET ENV VARIABLES
#===========================================================#

# Set directories paths (inside share folder between docker & host)
share_dir  = os.path.join(os.getcwd(), 'share')
work_dir   = os.path.join(share_dir, 'work')
output_dir = os.path.join(share_dir, 'output')

# Create directories if they don't exist
os.makedirs(work_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# Set environmental varibales
os.environ['FS_LICENSE'] = '/app/share/license.txt'
os.environ['SUBJECTS_DIR'] = share_dir

#===========================================================#
# RUN FREESURFER RECON-ALL & SEGMENT_SUBREGIONS
#===========================================================#

if not args.fs_skip:

    print('## RUN RECON-ALL & SEGMENT_SUBREGIONS ##')
    print(f'## INPUT FILE: {args.t1w} ##')    

    os.system(f'recon-all -i share/{args.t1w} -subjid freesurfer -nuintensitycor -all {args.fs_flags} -parallel')
    os.system('segment_subregions brainstem --cross freesurfer')

if args.fs_only_brainstem:
    os.system('segment_subregions brainstem --cross freesurfer')

#===========================================================#
# CREATE CORTICAL MODEL
#===========================================================#

print('## CREATE CORTICAL AND SUBCORTICAL MODEL ##')

lh_pial = os.path.join(share_dir, 'freesurfer/surf/lh.pial')
rh_pial = os.path.join(share_dir, 'freesurfer/surf/rh.pial')
cortical_stl = os.path.join(output_dir, 'cortical_final.stl')
os.system(f'mris_convert --combinesurfs {lh_pial} {rh_pial} {cortical_stl}')

#===========================================================#
# CREATE SUBCORTICAL MODEL
#===========================================================#

# Cerebellum, corpus callosum, thalamus
cerebellum_mgz = os.path.join(share_dir, 'freesurfer/mri/aseg.mgz')
cerebellum_bin = os.path.join(work_dir, 'cerebellum_bin.nii.gz')
cerebellum_surf = os.path.join(work_dir, 'cerebellum.pial')
cerebellum_stl = os.path.join(work_dir, 'cerebellum.stl')
os.system(f'mri_binarize --i {cerebellum_mgz} --match 6 7 8 10 45 46 47 49 250 251 252 253 254 255 --o {cerebellum_bin}')
os.system(f'mri_tessellate {cerebellum_bin} 1 {cerebellum_surf}')
os.system(f'mris_convert {cerebellum_surf} {cerebellum_stl}')

# Brainstem
brainstem_mgz = os.path.join(share_dir, 'freesurfer/mri/brainstemSsLabels.FSvoxelSpace.mgz')
brainstem_bin = os.path.join(work_dir, 'brainstem_bin.mgz')
brainstem_surf = os.path.join(work_dir, 'brainstem.pial')
brainstem_stl = os.path.join(work_dir, 'brainstem.stl')
os.system(f'mri_binarize --i {brainstem_mgz} --match 170 171 172 173 174 175 177 178 179 --o {brainstem_bin}')
os.system(f'mri_tessellate {brainstem_bin} 1 {brainstem_surf}')
os.system(f'mris_convert {brainstem_surf} {brainstem_stl}')

#===========================================================#
# MESH PROCESSING VIA PYMESHLAB
#===========================================================#

print('## APPLY MESH PROCESSING VIA PYMESHLAB ##')

# Combine cerebellum & brainstem
ms = pymeshlab.MeshSet()
ms.load_new_mesh(brainstem_stl)
ms.load_new_mesh(cerebellum_stl)
ms.mesh_boolean_union()
subcortical_stl = os.path.join(output_dir, 'subcortical_final.stl')
ms.save_current_mesh(subcortical_stl)

## Resolve non-manifold mesh
ms = pymeshlab.MeshSet()
ms.load_new_mesh(subcortical_stl)
ms.uniform_mesh_resampling(cellsize=pymeshlab.Percentage(1))
ms.remove_isolated_pieces_wrt_diameter()
ms.save_current_mesh(subcortical_stl)

# Smoothing subcortical model
if args.smooth:
    ms.scaledependent_laplacian_smooth(stepsmoothnum=args.smooth, delta=pymeshlab.Percentage(0.1))
    ms.save_current_mesh(subcortical_stl)
    print(f'## Smoothed cerebellum & brainstem with {args.smooth} steps ##')
else:
    print('## No smoothing requested ##')

# Smooth cortical model
ms = pymeshlab.MeshSet()
ms.load_new_mesh(cortical_stl)
ms.laplacian_smooth(stepsmoothnum=1)
ms.save_current_mesh(cortical_stl)

# Combine subcortical & cortical model
ms.load_new_mesh(subcortical_stl)
ms.mesh_boolean_union()

# Decimate combined model
if args.decimate:
    ms.simplification_quadric_edge_collapse_decimation(targetfacenum=int(args.decimate), preserveboundary=True, preservetopology=True, boundaryweight=2)
    print(f'## Decimated mesh to {args.decimate} faces ##')
else:
    print('## No decimation requested ##')

# Save final model
final_stl = os.path.join(output_dir, 'brain_final.stl')
ms.save_current_mesh(final_stl)

#===========================================================#
# CREATE MODEL FOR EACH HEMISSPHERE
#===========================================================#

if args.hemi:

    print('## CREATE MODEL FOR EACH HEMISSPHERE ##')

    # Create output folder
    hemi_dir = os.path.join(output_dir, 'hemi')
    os.makedirs(hemi_dir, exist_ok=True)

    # Cortical model
    lh_stl = os.path.join(hemi_dir, 'left_hemi.stl')
    rh_stl = os.path.join(hemi_dir, 'right_hemi.stl')
    os.system(f'mris_convert {lh_pial}  {lh_stl}')
    os.system(f'mris_convert {rh_pial}  {rh_stl}')

    # Get value for 'planeoffset' argument    
    offset_x = args.planeoffset if args.planeoffset is not None else ms.compute_geometric_measures()['center_of_mass'][0]

    # Split subcortical model in half
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(subcortical_stl)
    ms.compute_planar_section(planeoffset=offset_x, splitsurfacewithsection=True, createsectionsurface=True)
    print(f'## The subcortical model was splitted at x-planeoffset: {offset_x} ##')

    ms.set_current_mesh(2)
    section = os.path.join(work_dir, 'section.stl')
    ms.save_current_mesh(section)
    ms.set_current_mesh(3)
    right_subc = os.path.join(work_dir, 'right_subc.stl')
    ms.save_current_mesh(right_subc)
    ms.set_current_mesh(4)
    left_subc = os.path.join(work_dir, 'left_subc.stl')
    ms.save_current_mesh(left_subc)

    ## Close hole
    def process_subc(subc_stl):
        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(section)

        if (offset_x > 0 and subc_stl == right_subc) or (offset_x < 0 and subc_stl == left_subc):
            ms.invert_faces_orientation()

        ms.load_new_mesh(subc_stl)
        ms.flatten_visible_layers()
        ms.save_current_mesh(subc_stl)

    process_subc(left_subc)
    process_subc(right_subc)

    # Smooth cortical model; Combine subcortical & cortical model of each hemisphere; clean edge between hemisspheres
    def process_hemi(hemi_stl, subc_stl, opposing_subc):
        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(hemi_stl)
        ms.laplacian_smooth(stepsmoothnum=1)
        ms.load_new_mesh(subc_stl)
        ms.mesh_boolean_union()
        ms.load_new_mesh(opposing_subc)
        ms.mesh_boolean_difference(first_mesh=2, second_mesh=3)
        ms.save_current_mesh(hemi_stl)

    process_hemi(lh_stl, left_subc, right_subc)
    process_hemi(rh_stl, right_subc, left_subc)

    # Clean hemissphere models
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
    ms.mesh_boolean_difference()
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
        annot = os.path.join(share_dir, f"freesurfer/label/{hemi}.aparc.annot")
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

    # Run pial2stl for each hemissphere
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