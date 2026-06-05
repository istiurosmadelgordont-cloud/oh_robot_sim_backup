import xml.etree.ElementTree as ET

world_file = r'd:\飞腾派\plan\2\oh_robot_sim\assets\worlds\sdf\hospital_ward.classic.world'
tree = ET.parse(world_file)
ward = [m for m in tree.getroot().findall('.//model') if m.attrib.get('name') == 'hospital_ward'][0]

# 1. Remove old pharmacy elements
to_remove = []
for l in ward.findall('.//link'):
    name = l.attrib.get('name', '')
    if 'shelf' in name or name in ['grab_zone_pharmacy', 'pharmacy_desk', 'server_node']:
        to_remove.append(l)

for l in to_remove:
    ward.remove(l)

# Helper function to create links
def create_link(name, pose, size, color):
    link = ET.SubElement(ward, 'link', {'name': name})
    ET.SubElement(link, 'pose').text = pose
    vis = ET.SubElement(link, 'visual', {'name': name + '_vis'})
    geom = ET.SubElement(vis, 'geometry')
    ET.SubElement(geom, 'box').append(ET.fromstring(f'<size>{size}</size>'))
    mat = ET.SubElement(vis, 'material')
    if color.startswith('Gazebo/'):
        scr = ET.SubElement(mat, 'script')
        ET.SubElement(scr, 'name').text = color
    else:
        ET.SubElement(mat, 'ambient').text = color
        ET.SubElement(mat, 'diffuse').text = color
    return link

# 2. Rebuild Pharmacy Shelf
# Center of shelf: X=5.0, Y=4.8. Width=2.0 (X: 4.0 to 6.0), Depth=0.2 (Y: 4.7 to 4.9)
shelf_color = '0.6 0.6 0.6 1' # Grey metal

# Legs
create_link('shelf_leg_1', '4.0 4.7 0.9 0 0 0', '0.02 0.02 1.8', shelf_color)
create_link('shelf_leg_2', '6.0 4.7 0.9 0 0 0', '0.02 0.02 1.8', shelf_color)
create_link('shelf_leg_3', '4.0 4.9 0.9 0 0 0', '0.02 0.02 1.8', shelf_color)
create_link('shelf_leg_4', '6.0 4.9 0.9 0 0 0', '0.02 0.02 1.8', shelf_color)

# Boards (Z=0.8, 1.2, 1.6, 1.8)
create_link('shelf_board_1', '5.0 4.8 0.79 0 0 0', '2.02 0.22 0.02', shelf_color)
create_link('shelf_board_2', '5.0 4.8 1.19 0 0 0', '2.02 0.22 0.02', shelf_color)
create_link('shelf_board_3', '5.0 4.8 1.59 0 0 0', '2.02 0.22 0.02', shelf_color)
create_link('shelf_board_top', '5.0 4.8 1.81 0 0 0', '2.02 0.22 0.02', shelf_color)

# Back panel
create_link('shelf_back', '5.0 4.9 1.3 0 0 0', '2.02 0.01 1.0', '0.7 0.7 0.7 1')

# Dividers & Tags
colors = ['Gazebo/Red', 'Gazebo/Green', 'Gazebo/Blue', 'Gazebo/Yellow', 'Gazebo/Purple']
tag_idx = 0
for layer, z in enumerate([0.99, 1.39, 1.79]): # Center Z for dividers (height 0.38)
    for i in range(11):
        x = 4.0 + i * 0.2
        create_link(f'shelf_div_L{layer}_{i}', f'{x} 4.8 {z} 0 0 0', '0.01 0.2 0.38', shelf_color)
        
    for i in range(10):
        x = 4.1 + i * 0.2
        # Tag on the front edge of the board. Board is at Y=4.8, depth=0.22 -> front is 4.69
        # Z of board top is 0.8, 1.2, 1.6.
        tag_z = 0.8 + layer * 0.4
        create_link(f'shelf_tag_L{layer}_{i}', f'{x} 4.685 {tag_z} 0 0 0', '0.1 0.01 0.04', colors[tag_idx % len(colors)])
        tag_idx += 1

# 3. Grab Zone
# Y = 4.55, size 2.0 x 0.3
create_link('grab_zone_pharmacy', '5.0 4.55 0.005 0 0 0', '2.0 0.3 0.01', 'Gazebo/Yellow')

# 4. Desk and Server Node
# Desk at X=6.2, Y=3.0 (Right side of pharmacy)
desk_color = '0.9 0.9 0.9 1'
create_link('pharmacy_desk_top', '6.2 3.0 0.75 0 0 0', '1.0 0.6 0.02', desk_color)
create_link('pharmacy_desk_leg1', '5.75 2.75 0.375 0 0 0', '0.04 0.04 0.75', shelf_color)
create_link('pharmacy_desk_leg2', '6.65 2.75 0.375 0 0 0', '0.04 0.04 0.75', shelf_color)
create_link('pharmacy_desk_leg3', '5.75 3.25 0.375 0 0 0', '0.04 0.04 0.75', shelf_color)
create_link('pharmacy_desk_leg4', '6.65 3.25 0.375 0 0 0', '0.04 0.04 0.75', shelf_color)

# Computer Monitor (on desk)
create_link('server_monitor', '6.2 3.2 0.9 0 0.1 0', '0.4 0.02 0.25', '0.1 0.1 0.1 1')
create_link('server_monitor_stand', '6.2 3.25 0.8 0 0 0', '0.1 0.1 0.1', '0.2 0.2 0.2 1')
# Computer Keyboard
create_link('server_keyboard', '6.2 2.9 0.76 0 0 0', '0.3 0.12 0.01', '0.8 0.8 0.8 1')
# Computer Tower (under desk)
create_link('server_tower', '6.5 3.1 0.2 0 0 0', '0.15 0.35 0.4', '0.1 0.1 0.1 1')

tree.write(world_file, xml_declaration=True, encoding='utf-8')
print("Pharmacy rebuilt.")
