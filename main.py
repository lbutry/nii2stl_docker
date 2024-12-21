import os
import shutil
import argparse
import pymeshlab
import numpy as np
import nibabel.freesurfer as fsio

#===========================================================#
# SETUP ARGUMENTS PARSER
#===========================================================#

parser = argparse.ArgumentParser()

parser.add_argument('-t1w', type=str, help='Name of the T1w-image (.nii or .nii.gz) inside the home directory.')
parser.add_argument('-fs_skip', action='store_true', help="Skip FreeSurfer's 'recon-all' and 'segment_subregion brainstem' pipeline. Requires FreeSurfer output to be located in home directory.")
parser.add_argument('-fs_only_brainstem', action='store_true', help="Perform 'segment_subregion brainstem' and skip 'recon-all'. Requires FreeSurfer output to be located in home directory.")
parser.add_argument('-fs_flags', type=str, default = '', help="Parse more flags to 'recon-all'")
parser.add_argument('-smooth', type=int, default = 150, help="Number of smoothing steps. Use '0' to disable")
parser.add_argument('-decimate', type=float, default = 290000, help="Target number or percentage of faces. Use '0' to disable")
parser.add_argument('-parcels', action='store_true', help='Create STL files for each parcel of the Desikan-Killiany Atlas and for each brain lobe.')

args = parser.parse_args()

# Validate arguments & files
if not args.fs_skip and not args.t1w:
    parser.error('The following arguments are required: -t1w (unless -fs_skip is set)')

if not os.path.exists('/app/share/license.txt'):
    parser.error("The FreeSurfer's 'license.txt' file is missing in the home directory")

if args.fs_skip:
    if not os.path.exists('/app/share/freesurfer/mri/brainstemSsLabels.FSvoxelSpace.mgz'):
        parser.error("The folder 'freesurfer' is missing in the home directory or does not contain segmentation data from 'recon-all' & 'segment_subregions brainstem'")

if args.fs_only_brainstem:
    if not os.path.exists('/app/share/freesurfer/surf/lh.pial'):
        parser.error("The folder 'freesurfer' is missing in the home directory or does not contain segmentation data from 'recon-all'")
        
#===========================================================#
# CREATE WORK & OUTPUT DIRECTORY, SET ENV VARIABLES
#===========================================================#

# set directories inside share folder between docker & host
share_dir  = os.path.join(os.getcwd(), 'share')
work_dir   = os.path.join(share_dir, 'work')
output_dir = os.path.join(share_dir, 'output')

os.makedirs(work_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

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

lh_pial = os.path.join(share_dir, 'freesurfer/surf/lh.pial')
rh_pial = os.path.join(share_dir, 'freesurfer/surf/rh.pial')
cortical_stl = os.path.join(output_dir, 'cortical_final.stl')
os.system(f'mris_convert --combinesurfs {lh_pial} {rh_pial} {cortical_stl}')

#===========================================================#
# CREATE SUBCORTICAL MODEL
#===========================================================#

print('## CREATE CORTICAL AND SUBCORTICAL MODEL ##')

# Cerebellum
cerebellum_mgz = os.path.join(share_dir, 'freesurfer/mri/aseg.mgz')
cerebellum_bin = os.path.join(work_dir, 'cerebellum_bin.nii.gz')
cerebellum_surf = os.path.join(work_dir, 'cerebellum.pial')
cerebellum_stl = os.path.join(work_dir, 'cerebellum.stl')
os.system(f'mri_binarize --i {cerebellum_mgz} --match 6 7 8 45 46 47 --o {cerebellum_bin}')
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
# SMOOTH & COMBINE MODELS & DECIMATE VIA PYMESHLAB
#===========================================================#

print('## APPLY FURTHER PROCESSING AS REQUESTED ##')

ms = pymeshlab.MeshSet()

# Combine cerebellum & brainstem
ms.load_new_mesh(cerebellum_stl)
ms.load_new_mesh(brainstem_stl)
ms.apply_filter('flatten_visible_layers', mergevisible=True)

# Smoothing
if args.smooth:
    print(f'## Smoothing cerebellum & brainstem with {args.smooth} steps ##')
    ms.apply_filter('scaledependent_laplacian_smooth', stepsmoothnum=args.smooth, 
    delta=pymeshlab.Percentage(0.1))
else:
    print('## No smoothing requested ##')

ms.save_current_mesh(os.path.join(output_dir, 'subcortical_final.stl'))

# Combine subcortical & cortical
ms.load_new_mesh(cortical_stl)
ms.apply_filter('flatten_visible_layers', mergevisible=True)
ms.apply_filter('merge_close_vertices', )  # closing holes

# Decimate    
if args.decimate:
    if args.decimate < 1:  # Treat as percentage
        print(f'## Decimating mesh to {args.decimate * 100} % of original ##')
        ms.apply_filter('simplification_quadric_edge_collapse_decimation', targetperc=args.decimate, preserveboundary=True, boundaryweight=2)
    else:  # Treat as target face number
        print(f'## Decimating mesh to {args.decimate} faces ##')
        ms.apply_filter('simplification_quadric_edge_collapse_decimation', targetfacenum=int(args.decimate), preserveboundary=True, boundaryweight=2)
else:
    print('## No decimation requested ##')

ms.save_current_mesh(os.path.join(output_dir, 'brain_final.stl'))

#===========================================================#
# CREATE MODEL FOR EACH CORTICAL PARCEL & LOBE
#===========================================================#

print('## PARCELLATE BRAIN INTO REGIONS AND LOBES ##')

if args.parcels:

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

            ms.apply_filter('flatten_visible_layers', mergevisible=True)
            ms.save_current_mesh(os.path.join(lobes_dir, f'{hemi}_lobe-{lobe_name}.stl'))

#===========================================================#
# TIDY UP
#===========================================================#

# Remove work directory
shutil.rmtree(work_dir)

# End text
print('''
    #================================================#
    #                SCRIPT FINISHED                 #
    #================================================#
''')