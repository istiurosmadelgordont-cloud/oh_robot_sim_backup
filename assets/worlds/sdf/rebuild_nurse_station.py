import xml.etree.ElementTree as ET

world_file = r'd:\飞腾派\plan\2\oh_robot_sim\assets\worlds\sdf\hospital_ward.classic.world'
tree = ET.parse(world_file)
ward = [m for m in tree.getroot().findall('.//model') if m.attrib.get('name') == 'hospital_ward'][0]

def add_box(link, name, pose, size, color, is_glass=False):
    vis = ET.SubElement(link, 'visual', {'name': name + '_vis'})
    ET.SubElement(vis, 'pose').text = pose
    geom = ET.SubElement(vis, 'geometry')
    ET.SubElement(geom, 'box').append(ET.fromstring(f'<size>{size}</size>'))
    mat = ET.SubElement(vis, 'material')
    if is_glass:
        ET.SubElement(mat, 'ambient').text = color
        ET.SubElement(mat, 'diffuse').text = color
        # Transparency is not always perfect in SDF without proper tags, but ambient alpha helps
    elif color.startswith('Gazebo/'):
        ET.SubElement(mat, 'script').append(ET.fromstring(f'<name>{color}</name>'))
    else:
        ET.SubElement(mat, 'ambient').text = color
        ET.SubElement(mat, 'diffuse').text = color
        
    col = ET.SubElement(link, 'collision', {'name': name + '_col'})
    ET.SubElement(col, 'pose').text = pose
    geom_c = ET.SubElement(col, 'geometry')
    ET.SubElement(geom_c, 'box').append(ET.fromstring(f'<size>{size}</size>'))

def add_mesh(link, name, pose, uri, scale):
    vis = ET.SubElement(link, 'visual', {'name': name + '_vis'})
    ET.SubElement(vis, 'pose').text = pose
    geom = ET.SubElement(vis, 'geometry')
    mesh = ET.SubElement(geom, 'mesh')
    ET.SubElement(mesh, 'uri').text = uri
    ET.SubElement(mesh, 'scale').text = scale

# Find target links
desk_link = None
cabinet_link = None
pda_link = None

for l in ward.findall('.//link'):
    name = l.attrib.get('name', '')
    if name == 'nurse_desk': desk_link = l
    elif name == 'nurse_cabinet': cabinet_link = l
    elif name == 'virtual_pda': pda_link = l

# 1. Rebuild Nurse Desk
if desk_link is not None:
    # Clear old
    for t in ['visual', 'collision']:
        for e in desk_link.findall(t): desk_link.remove(e)
        
    desk_link.find('pose').text = '4.0 -4.0 0 0 0 0'
    
    # Solid desk
    add_box(desk_link, 'desk_top', '0 0 0.75 0 0 0', '1.6 0.7 0.02', 'Gazebo/White')
    add_box(desk_link, 'desk_front', '0 0.34 0.375 0 0 0', '1.6 0.02 0.75', 'Gazebo/White')
    add_box(desk_link, 'desk_side_l', '-0.79 0 0.375 0 0 0', '0.02 0.7 0.75', 'Gazebo/White')
    add_box(desk_link, 'desk_side_r', '0.79 0 0.375 0 0 0', '0.02 0.7 0.75', 'Gazebo/White')
    
    # Monitor (using TV mesh)
    add_mesh(desk_link, 'desk_monitor', '0 -0.15 0.76 0 0 0', 'file:///root/workspace/assets/models/sdf/extracted/aws_robomaker_residential_TV_01/meshes/aws_robomaker_residential_TV_01_visual.DAE', '0.4 0.4 0.4')
    # Blue Screen
    add_box(desk_link, 'desk_screen', '0 -0.16 0.95 0 0 0', '0.38 0.005 0.23', '0.2 0.6 1.0 1')
    # Keyboard
    add_box(desk_link, 'desk_keyboard', '0 -0.3 0.765 0 0 0', '0.4 0.15 0.01', 'Gazebo/DarkGrey')

# 2. Virtual PDA
if pda_link is not None:
    pda_link.find('pose').text = '4.4 -4.2 0.76 0 0 0'

# 3. Rebuild Medical Cabinet
if cabinet_link is not None:
    for t in ['visual', 'collision']:
        for e in cabinet_link.findall(t): cabinet_link.remove(e)
        
    cabinet_link.find('pose').text = '6.0 -4.8 0 0 0 0'
    
    # Cabinet Frame
    add_box(cabinet_link, 'cab_back', '0 0.19 1.0 0 0 0', '1.4 0.02 2.0', 'Gazebo/White')
    add_box(cabinet_link, 'cab_side_l', '-0.69 0 1.0 0 0 0', '0.02 0.4 2.0', 'Gazebo/White')
    add_box(cabinet_link, 'cab_side_r', '0.69 0 1.0 0 0 0', '0.02 0.4 2.0', 'Gazebo/White')
    add_box(cabinet_link, 'cab_top', '0 0 1.99 0 0 0', '1.4 0.4 0.02', 'Gazebo/White')
    add_box(cabinet_link, 'cab_bot', '0 0 0.01 0 0 0', '1.4 0.4 0.02', 'Gazebo/White')
    
    # Shelves
    for i, z in enumerate([0.4, 0.8, 1.2, 1.6]):
        add_box(cabinet_link, f'cab_shelf_{i}', f'0 0 {z} 0 0 0', '1.38 0.38 0.02', 'Gazebo/White')
        # Add some medical supplies on the shelves
        add_box(cabinet_link, f'med_supply_{i}_1', f'-0.4 0 {z+0.1} 0 0 0', '0.2 0.2 0.2', 'Gazebo/Red')
        add_box(cabinet_link, f'med_supply_{i}_2', f'0.0 0 {z+0.1} 0 0 0', '0.25 0.15 0.2', 'Gazebo/Blue')
        add_box(cabinet_link, f'med_supply_{i}_3', f'0.4 0 {z+0.1} 0 0 0', '0.15 0.25 0.2', 'Gazebo/Green')
        
    # Glass Doors
    add_box(cabinet_link, 'cab_glass_l', '-0.35 -0.19 1.0 0 0 0', '0.68 0.02 1.96', '0.8 0.9 1.0 0.4', is_glass=True)
    add_box(cabinet_link, 'cab_glass_r', '0.35 -0.19 1.0 0 0 0', '0.68 0.02 1.96', '0.8 0.9 1.0 0.4', is_glass=True)

# 4. Add Whiteboard on the back wall
# Remove old whiteboard if exists
for l in ward.findall('.//link'):
    if l.attrib.get('name') == 'nurse_whiteboard':
        ward.remove(l)

wb = ET.SubElement(ward, 'link', {'name': 'nurse_whiteboard'})
ET.SubElement(wb, 'pose').text = '4.0 -4.92 1.5 0 0 0'
add_box(wb, 'wb_frame', '0 0 0 0 0 0', '1.24 0.005 0.84', 'Gazebo/Grey')
add_box(wb, 'wb_board', '0 -0.005 0 0 0 0', '1.2 0.005 0.8', 'Gazebo/White')
# Add some "content"
add_box(wb, 'wb_line1', '0 -0.01 0.2 0 0 0', '0.8 0.001 0.02', 'Gazebo/Black')
add_box(wb, 'wb_line2', '-0.2 -0.01 0.1 0 0 0', '0.4 0.001 0.02', 'Gazebo/Black')
add_box(wb, 'wb_line3', '0.1 -0.01 -0.1 0 0 0', '0.6 0.001 0.02', 'Gazebo/Blue')

tree.write(world_file, xml_declaration=True, encoding='utf-8')
print("Nurse station perfectly rebuilt.")
