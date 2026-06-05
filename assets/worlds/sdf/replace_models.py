import xml.etree.ElementTree as ET
import copy

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

# 1. Replace Nurse Desk
nurse_desk = get_link('nurse_desk')
if nurse_desk is not None:
    # Set to ground level
    nurse_desk.find('pose').text = '5 -3 0 0 0 0'
    for vis in nurse_desk.findall('visual'):
        nurse_desk.remove(vis)
    for col in nurse_desk.findall('collision'):
        nurse_desk.remove(col)
    
    vis = ET.SubElement(nurse_desk, 'visual', {'name': 'nurse_desk_vis'})
    geom = ET.SubElement(vis, 'geometry')
    mesh = ET.SubElement(geom, 'mesh')
    uri = ET.SubElement(mesh, 'uri')
    uri.text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_warehouse_DeskC_01/meshes/aws_robomaker_warehouse_DeskC_01_visual.DAE'
    
    col = ET.SubElement(nurse_desk, 'collision', {'name': 'nurse_desk_col'})
    geom_col = ET.SubElement(col, 'geometry')
    mesh_col = ET.SubElement(geom_col, 'mesh')
    uri_col = ET.SubElement(mesh_col, 'uri')
    uri_col.text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_warehouse_DeskC_01/meshes/aws_robomaker_warehouse_DeskC_01_collision.DAE'

# 2. Replace Nurse Cabinet
nurse_cabinet = get_link('nurse_cabinet')
if nurse_cabinet is not None:
    # Cabinet needs to be placed on the East Wall (X=7). Let's put it at X=6.5, Y=-3
    nurse_cabinet.find('pose').text = '6.5 -3 0 0 0 1.5708'
    for vis in nurse_cabinet.findall('visual'):
        nurse_cabinet.remove(vis)
    for col in nurse_cabinet.findall('collision'):
        nurse_cabinet.remove(col)
    
    vis = ET.SubElement(nurse_cabinet, 'visual', {'name': 'nurse_cabinet_vis'})
    geom = ET.SubElement(vis, 'geometry')
    mesh = ET.SubElement(geom, 'mesh')
    uri = ET.SubElement(mesh, 'uri')
    uri.text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_residential_Wardrobe_01/meshes/aws_robomaker_residential_Wardrobe_01_visual.DAE'
    
    col = ET.SubElement(nurse_cabinet, 'collision', {'name': 'nurse_cabinet_col'})
    geom_col = ET.SubElement(col, 'geometry')
    mesh_col = ET.SubElement(geom_col, 'mesh')
    uri_col = ET.SubElement(mesh_col, 'uri')
    uri_col.text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_residential_Wardrobe_01/meshes/aws_robomaker_residential_Wardrobe_01_collision.DAE'

# 3. Add Virtual PDA and Server Node
# We will append them to the ward model
if get_link('virtual_pda') is None:
    pda_link = ET.SubElement(ward, 'link', {'name': 'virtual_pda'})
    ET.SubElement(pda_link, 'pose').text = '4.8 -3 0.8 0 0 0' # On the desk
    vis = ET.SubElement(pda_link, 'visual', {'name': 'pda_vis'})
    geom = ET.SubElement(vis, 'geometry')
    mesh = ET.SubElement(geom, 'mesh')
    ET.SubElement(mesh, 'uri').text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_residential_Tablet_01/meshes/aws_robomaker_residential_Tablet_01_visual.DAE'
    ET.SubElement(pda_link, 'kinematic').text = '0'

if get_link('server_node') is None:
    srv_link = ET.SubElement(ward, 'link', {'name': 'server_node'})
    ET.SubElement(srv_link, 'pose').text = '5.2 -3 0.8 0 0 0' # On the desk
    vis = ET.SubElement(srv_link, 'visual', {'name': 'srv_vis'})
    geom = ET.SubElement(vis, 'geometry')
    mesh = ET.SubElement(geom, 'mesh')
    ET.SubElement(mesh, 'uri').text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_residential_TV_01/meshes/aws_robomaker_residential_TV_01_visual.DAE'
    ET.SubElement(srv_link, 'kinematic').text = '0'

# 4. Replace Beds
for i in range(1, 3):
    for j in range(1, 5):
        bed_name = f'bed_w{i}_{j}'
        bed = get_link(bed_name)
        if bed is not None:
            # We must drop the bed to ground level Z=0 instead of Z=0.25 (which was the box center)
            pose_text = bed.find('pose').text
            parts = pose_text.split()
            x, y = parts[0], parts[1]
            bed.find('pose').text = f'{x} {y} 0 0 0 0'
            
            for vis in bed.findall('visual'):
                bed.remove(vis)
            for col in bed.findall('collision'):
                bed.remove(col)
            
            vis = ET.SubElement(bed, 'visual', {'name': f'{bed_name}_vis'})
            geom = ET.SubElement(vis, 'geometry')
            mesh = ET.SubElement(geom, 'mesh')
            uri = ET.SubElement(mesh, 'uri')
            uri.text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_residential_Bed_01/meshes/aws_robomaker_residential_Bed_01_visual.DAE'
            
            col = ET.SubElement(bed, 'collision', {'name': f'{bed_name}_col'})
            geom_col = ET.SubElement(col, 'geometry')
            mesh_col = ET.SubElement(geom_col, 'mesh')
            uri_col = ET.SubElement(mesh_col, 'uri')
            uri_col.text = 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_residential_Bed_01/meshes/aws_robomaker_residential_Bed_01_collision.DAE'

# 5. Modify Sign Zones (Delivery Zones) to be Yellow Rectangles
for i in range(1, 3):
    for j in range(1, 5):
        sz_name = f'sign_zone_w{i}_{j}'
        sz = get_link(sz_name)
        if sz is not None:
            # The bed is at x_bed. Sz is currently at x_bed + 1.0.
            # We want it to be a yellow rectangle.
            for vis in sz.findall('visual'):
                sz.remove(vis)
            
            # The box geometry
            vis = ET.SubElement(sz, 'visual', {'name': f'{sz_name}_vis'})
            geom = ET.SubElement(vis, 'geometry')
            # Use box instead of cylinder to make a rectangle on the floor
            box = ET.SubElement(geom, 'box')
            ET.SubElement(box, 'size').text = '0.5 2.0 0.01' # 50cm width, 2m length
            
            mat = ET.SubElement(vis, 'material')
            ET.SubElement(mat, 'ambient').text = '1.0 0.8 0.0 0.5' # Yellow semi-transparent
            ET.SubElement(mat, 'diffuse').text = '1.0 0.8 0.0 0.5'
            # Also adjust pose to Z=0.005 so it sits on the floor
            parts = sz.find('pose').text.split()
            sz.find('pose').text = f'{parts[0]} {parts[1]} 0.005 0 0 0'

# Save the world
tree.write(world_file, xml_declaration=True, encoding='utf-8')
print("World file updated successfully.")
