import pymeshlab
import os

print('Starting stand.py')

n = 40

# Set directories paths (inside share folder between docker & host)
share_dir  = os.path.join(os.getcwd(), 'share')
output_dir = os.path.join(share_dir, 'output')

brain = os.path.join(output_dir, 'brain_final.stl')
stand = os.path.join(share_dir, 'stand_template.stl')

ms = pymeshlab.MeshSet()
ms.load_new_mesh(brain)

## Set new origin at brains center of mass x-y-axis
geo = ms.compute_geometric_measures()
new_origin = geo['center_of_mass']
new_origin[-1] = 0 # set z-axis to 0
ms.transform_translate_center_set_origin(traslmethod='Set new Origin', neworigin=new_origin)
brain_centered = os.path.join(output_dir, 'brain_final_centered.stl')
ms.save_current_mesh(brain_centered)

# Load stand & move it to the bottom of the brain
ms.load_new_mesh(stand)
z_bbox_min = geo['bbox'].min()[-1] # get minimum of the bounding box (z-axis)
ms.transform_translate_center_set_origin(traslmethod='XYZ translation', axisz=z_bbox_min -1)
stand_centered = os.path.join(output_dir, 'stand_centered.stl')
ms.save_current_mesh(stand_centered)

for i in range(n):
    ms.set_current_mesh(0)
    if i != 0:
        ms.transform_translate_center_set_origin(traslmethod='XYZ translation', axisz=0.1)
    ms.mesh_boolean_difference(first_mesh=1 + i, second_mesh=0)
    print(f'Computed cradle: {i+1}/{n}')
    ms.set_current_mesh(1 + i + 1)

stand_final = os.path.join(output_dir, 'stand_final.stl')
ms.save_current_mesh(stand_final)