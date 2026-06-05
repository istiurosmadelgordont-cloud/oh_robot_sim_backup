import xml.etree.ElementTree as ET

world_file = r'd:\飞腾派\plan\2\oh_robot_sim\assets\worlds\sdf\hospital_ward.classic.world'
tree = ET.parse(world_file)
ward = [m for m in tree.getroot().findall('.//model') if m.attrib.get('name') == 'hospital_ward'][0]

def add_box(link, name, pose, size, color):
    vis = ET.SubElement(link, 'visual', {'name': name + '_vis'})
    ET.SubElement(vis, 'pose').text = pose
    geom = ET.SubElement(vis, 'geometry')
    ET.SubElement(geom, 'box').append(ET.fromstring(f'<size>{size}</size>'))
    mat = ET.SubElement(vis, 'material')
    if color.startswith('Gazebo/'):
        ET.SubElement(mat, 'script').append(ET.fromstring(f'<name>{color}</name>'))
    else:
        ET.SubElement(mat, 'ambient').text = color
        ET.SubElement(mat, 'diffuse').text = color
        
    col = ET.SubElement(link, 'collision', {'name': name + '_col'})
    ET.SubElement(col, 'pose').text = pose
    geom_c = ET.SubElement(col, 'geometry')
    ET.SubElement(geom_c, 'box').append(ET.fromstring(f'<size>{size}</size>'))

# 1. Move and Reshape the Desk to an L-shape against the left wall
desk_link = None
cabinet_link = None
for l in ward.findall('.//link'):
    name = l.attrib.get('name', '')
    if name == 'nurse_desk': desk_link = l
    if name == 'nurse_cabinet': cabinet_link = l

if desk_link is not None:
    # Desk at X=4.4, Y=-3.6 (closer to center, facing North)
    desk_link.find('pose').text = '4.4 -3.6 0 0 0 0'
    
    # Add L-extension (side desk connecting to the left wall X=3.0)
    # Desk left edge is at X=4.4 - 0.8 = 3.6
    # Left wall is at X=3.0. Inner face is 3.075.
    # Extension from 3.075 to 3.6. Center X is 3.3375.
    # Relative to desk center 4.4, this is X=-1.0625.
    # Width = 3.6 - 3.075 = 0.525.
    
    # Check if already added
    if desk_link.find(".//visual[@name='desk_ext_top_vis']") is None:
        add_box(desk_link, 'desk_ext_top', '-1.06 -0.1 0.75 0 0 0', '0.52 0.5 0.02', 'Gazebo/White')
        add_box(desk_link, 'desk_ext_front', '-1.06 0.14 0.375 0 0 0', '0.52 0.02 0.75', 'Gazebo/White')
        
    # DETAILS: Add a telephone
    if desk_link.find(".//visual[@name='desk_phone_base_vis']") is None:
        add_box(desk_link, 'desk_phone_base', '-0.5 -0.1 0.76 0 0 0', '0.15 0.2 0.04', 'Gazebo/Black')
        add_box(desk_link, 'desk_phone_handset', '-0.5 -0.1 0.79 0 0 0', '0.04 0.22 0.03', 'Gazebo/DarkGrey')
        
    # DETAILS: Add a mouse
    if desk_link.find(".//visual[@name='desk_mouse_vis']") is None:
        add_box(desk_link, 'desk_mouse', '0.3 -0.3 0.76 0 0 0', '0.06 0.1 0.02', 'Gazebo/Grey')

    # DETAILS: Simulate UI on the monitor
    if desk_link.find(".//visual[@name='desk_ui_check_vis']") is None:
        # Green checkmark box
        add_box(desk_link, 'desk_ui_check', '0 -0.165 0.95 0 0 0', '0.1 0.006 0.1', 'Gazebo/Green')
        # White text lines
        add_box(desk_link, 'desk_ui_text1', '0 -0.165 0.85 0 0 0', '0.2 0.006 0.02', 'Gazebo/White')

# 2. Virtual PDA reposition
for l in ward.findall('.//link'):
    if l.attrib.get('name') == 'virtual_pda':
        l.find('pose').text = '4.9 -3.8 0.76 0 0 0'

# 3. Adjust Whiteboard position to be behind the desk
for l in ward.findall('.//link'):
    if l.attrib.get('name') == 'nurse_whiteboard':
        l.find('pose').text = '4.4 -4.92 1.5 0 0 0'

# 4. Where is the cabinet?
# If the user can't see the cabinet, let's make sure it's placed correctly.
# Back right corner is X=6.9, Y=-4.8.
if cabinet_link is not None:
    cabinet_link.find('pose').text = '6.2 -4.8 0 0 0 0'

tree.write(world_file, xml_declaration=True, encoding='utf-8')
print('Desk moved, made L-shaped, and details added.')
