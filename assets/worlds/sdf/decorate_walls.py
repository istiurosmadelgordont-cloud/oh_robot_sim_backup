import xml.etree.ElementTree as ET

world_file = r'd:\飞腾派\plan\2\oh_robot_sim\assets\worlds\sdf\hospital_ward.classic.world'
tree = ET.parse(world_file)
ward = [m for m in tree.getroot().findall('.//model') if m.attrib.get('name') == 'hospital_ward'][0]

def create_sign(name, pose, size, bg_color, fg_color):
    link = ET.SubElement(ward, 'link', {'name': name})
    ET.SubElement(link, 'pose').text = pose
    vis = ET.SubElement(link, 'visual', {'name': name + '_bg'})
    geom = ET.SubElement(vis, 'geometry')
    ET.SubElement(geom, 'box').append(ET.fromstring(f'<size>{size}</size>'))
    mat = ET.SubElement(vis, 'material')
    if bg_color.startswith('Gazebo/'):
        scr = ET.SubElement(mat, 'script')
        ET.SubElement(scr, 'name').text = bg_color
    else:
        ET.SubElement(mat, 'ambient').text = bg_color
        ET.SubElement(mat, 'diffuse').text = bg_color
        
    parts = size.split()
    sx, sy, sz = float(parts[0]), float(parts[1]), float(parts[2])
    if sx < sy and sx < sz: 
        fg_size = f'{sx + 0.004} {sy*0.9} {sz*0.9}'
    elif sy < sx and sy < sz: 
        fg_size = f'{sx*0.9} {sy + 0.004} {sz*0.9}'
    else:
        fg_size = size
        
    vis2 = ET.SubElement(link, 'visual', {'name': name + '_fg'})
    ET.SubElement(vis2, 'pose').text = '0 0 0 0 0 0'
    geom2 = ET.SubElement(vis2, 'geometry')
    ET.SubElement(geom2, 'box').append(ET.fromstring(f'<size>{fg_size}</size>'))
    mat2 = ET.SubElement(vis2, 'material')
    if fg_color.startswith('Gazebo/'):
        scr = ET.SubElement(mat2, 'script')
        ET.SubElement(scr, 'name').text = fg_color
    else:
        ET.SubElement(mat2, 'ambient').text = fg_color
        ET.SubElement(mat2, 'diffuse').text = fg_color

def create_light(name, pose):
    link = ET.SubElement(ward, 'link', {'name': name})
    ET.SubElement(link, 'pose').text = pose
    vis = ET.SubElement(link, 'visual', {'name': name + '_vis'})
    geom = ET.SubElement(vis, 'geometry')
    ET.SubElement(geom, 'box').append(ET.fromstring('<size>1.2 0.3 0.05</size>'))
    mat = ET.SubElement(vis, 'material')
    ET.SubElement(mat, 'ambient').text = '1 1 1 1'
    ET.SubElement(mat, 'diffuse').text = '1 1 1 1'
    ET.SubElement(mat, 'emissive').text = '1 1 1 1'

# Clear old decorations
for l in ward.findall('.//link'):
    if l.attrib.get('name', '').startswith('decor_'):
        ward.remove(l)

# 1. Signs and Posters
create_sign('decor_sign_pharm_desk', '6.98 3.0 1.6 0 0 0', '0.01 0.8 0.4', 'Gazebo/White', 'Gazebo/Blue')
create_sign('decor_sign_pharm_door', '3.02 3.0 1.5 0 0 0', '0.01 0.6 0.8', 'Gazebo/White', '0.2 0.6 0.8 1')
create_sign('decor_sign_w1', '-2.0 4.98 1.5 0 0 0', '1.0 0.01 0.6', 'Gazebo/White', 'Gazebo/Green')
create_sign('decor_sign_w2', '-2.0 -4.98 1.5 0 0 0', '1.0 0.01 0.6', 'Gazebo/White', 'Gazebo/Green')
create_sign('decor_sign_corr', '0.0 1.02 1.5 0 0 0', '2.0 0.01 1.0', 'Gazebo/White', 'Gazebo/Grey')

# 2. Ceiling Lights (Z=2.8)
create_light('decor_light_pharm_1', '5.0 2.5 2.8 0 0 0')
create_light('decor_light_pharm_2', '5.0 4.0 2.8 0 0 0')
create_light('decor_light_nurse_1', '5.0 -2.5 2.8 0 0 0')
create_light('decor_light_nurse_2', '5.0 -4.0 2.8 0 0 0')
for i in range(-5, 6, 3):
    create_light(f'decor_light_corr_{i}', f'{i} 0.0 2.8 0 0 1.5708')
create_light('decor_light_w1_1', '-2.0 3.0 2.8 0 0 0')
create_light('decor_light_w1_2', '-5.0 3.0 2.8 0 0 0')
create_light('decor_light_w2_1', '-2.0 -3.0 2.8 0 0 0')
create_light('decor_light_w2_2', '-5.0 -3.0 2.8 0 0 0')

tree.write(world_file, xml_declaration=True, encoding='utf-8')
print("Decorations and lights added.")
