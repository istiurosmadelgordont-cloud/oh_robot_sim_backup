import xml.etree.ElementTree as ET

world_file = r'd:\飞腾派\plan\2\oh_robot_sim\assets\worlds\sdf\hospital_ward.classic.world'
tree = ET.parse(world_file)
root = tree.getroot()

ward = None
for m in root.findall('.//model'):
    if m.attrib.get('name') == 'hospital_ward':
        ward = m
        break

def get_link(name):
    for l in ward.findall('.//link'):
        if l.attrib.get('name') == name:
            return l
    return None

# Fix Nurse Cabinet
nurse_cabinet = get_link('nurse_cabinet')
if nurse_cabinet is not None:
    uri_vis = nurse_cabinet.find('.//visual/geometry/mesh/uri')
    if uri_vis is not None:
        uri_vis.text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_residential_Wardrobe_01/meshes/aws_Wardrobe_01_visual.DAE'
    uri_col = nurse_cabinet.find('.//collision/geometry/mesh/uri')
    if uri_col is not None:
        uri_col.text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_residential_Wardrobe_01/meshes/aws_Wardrobe_01_collision.DAE'
    # Adjust pose so it faces inward and doesn't clip the wall. Wall is at X=7.
    nurse_cabinet.find('pose').text = '6.4 -3 0 0 0 -1.5708' 

# Fix Beds
for i in range(1, 3):
    for j in range(1, 5):
        bed_name = f'bed_w{i}_{j}'
        bed = get_link(bed_name)
        if bed is not None:
            uri_vis = bed.find('.//visual/geometry/mesh/uri')
            if uri_vis is not None:
                uri_vis.text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_residential_Bed_01/meshes/aws_Bed_01_visual.DAE'
            uri_col = bed.find('.//collision/geometry/mesh/uri')
            if uri_col is not None:
                uri_col.text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_residential_Bed_01/meshes/aws_Bed_01_collision.DAE'
            # The bed DAE might have a different orientation. Let's add a 90 degree yaw if needed? 
            # We'll rotate the bed 90 degrees just in case it was modeled horizontally.
            # Usually Bed_01 has head at +X. If so, yaw=1.5708 makes it point head towards +Y (the top wall).
            pose_text = bed.find('pose').text
            parts = pose_text.split()
            # Set yaw to 1.5708
            bed.find('pose').text = f'{parts[0]} {parts[1]} {parts[2]} 0 0 1.5708'

# Fix Sign Zones (Delivery Zones)
# We want them to attach exactly to the bed edge.
for i in range(1, 3):
    for j in range(1, 5):
        sz_name = f'sign_zone_w{i}_{j}'
        sz = get_link(sz_name)
        bed = get_link(f'bed_w{i}_{j}')
        if sz is not None and bed is not None:
            bed_x = float(bed.find('pose').text.split()[0])
            bed_y = float(bed.find('pose').text.split()[1])
            # The yellow zone width is 0.5. 
            # If the bed is X=bed_x, and bed width is ~1.0m, edge is bed_x + 0.5
            # So the center of the yellow zone should be bed_x + 0.5 + 0.25 = bed_x + 0.75
            new_x = bed_x + 0.75
            sz.find('pose').text = f'{new_x} {bed_y} 0.005 0 0 0'

# Extract a new desk and use it!
import os, tarfile
base_dir = r"d:\飞腾派\plan\2\oh_robot_sim\assets\models\sdf"
extract_dir = os.path.join(base_dir, "extracted")
new_desk = "assets_models_aws_robomaker_residential_ReadingDesk_01.tar.xz"
tar_path = os.path.join(base_dir, new_desk)
if os.path.exists(tar_path):
    with tarfile.open(tar_path, "r:xz") as t:
        t.extractall(path=extract_dir)

# Update Desk
nurse_desk = get_link('nurse_desk')
if nurse_desk is not None:
    uri_vis = nurse_desk.find('.//visual/geometry/mesh/uri')
    if uri_vis is not None:
        uri_vis.text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_residential_ReadingDesk_01/meshes/aws_ReadingDesk_01_visual.DAE'
    uri_col = nurse_desk.find('.//collision/geometry/mesh/uri')
    if uri_col is not None:
        uri_col.text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_residential_ReadingDesk_01/meshes/aws_ReadingDesk_01_collision.DAE'

tree.write(world_file, xml_declaration=True, encoding='utf-8')
print("Fix applied successfully.")
