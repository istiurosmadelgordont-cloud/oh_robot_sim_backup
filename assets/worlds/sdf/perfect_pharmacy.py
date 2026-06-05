import xml.etree.ElementTree as ET

world_file = r'd:\飞腾派\plan\2\oh_robot_sim\assets\worlds\sdf\hospital_ward.classic.world'
tree = ET.parse(world_file)
ward = [m for m in tree.getroot().findall('.//model') if m.attrib.get('name') == 'hospital_ward'][0]

def update_link(name, pose=None, size=None):
    for link in ward.findall('.//link'):
        if link.attrib.get('name') == name:
            if pose: link.find('pose').text = pose
            if size:
                for target in ['.//visual/geometry/box/size', './/collision/geometry/box/size']:
                    elem = link.find(target)
                    if elem is not None: elem.text = size

# 1. Fix top board (Z=1.99)
update_link('shelf_board_top', pose='5.0 4.8 1.99 0 0 0', size='2.02 0.22 0.02')

# 2. Fix back panel (goes from Z=0.79 to Z=2.0 -> height 1.21, center 1.395)
update_link('shelf_back', pose='5.0 4.905 1.395 0 0 0', size='2.02 0.01 1.21')

# 3. Fix legs to go from Z=0 to Z=2.0 (height 2.0, center 1.0)
for i in range(1, 5):
    x = [4.0, 6.0, 4.0, 6.0][i-1]
    y = [4.7, 4.7, 4.9, 4.9][i-1]
    update_link(f'shelf_leg_{i}', pose=f"{x} {y} 1.0 0 0 0", size='0.04 0.04 2.0')

# 4. Fix Tags Z coordinate so they don't stick up above the board
for link in ward.findall('.//link'):
    name = link.attrib.get('name', '')
    if name.startswith('shelf_tag_'):
        pose = link.find('pose')
        if pose is not None:
            parts = pose.text.split()
            z = float(parts[2])
            # if z is 0.8, 1.2, 1.6, we lower it by 0.02 so it sits flush with the surface
            if z in [0.8, 1.2, 1.6]:
                parts[2] = f"{z - 0.02:.3f}"
                pose.text = ' '.join(parts)

# 5. Fix Monitor - add a glowing blue screen
for link in ward.findall('.//link'):
    if link.attrib.get('name') == 'server_monitor':
        # Add a blue screen visual slightly in front of the monitor
        screen_vis = ET.SubElement(link, 'visual', {'name': 'server_monitor_screen'})
        ET.SubElement(screen_vis, 'pose').text = '0 -0.011 0 0 0 0' # Slightly in front of -Y face
        geom = ET.SubElement(screen_vis, 'geometry')
        box = ET.SubElement(geom, 'box')
        ET.SubElement(box, 'size').text = '0.38 0.001 0.23' # Slightly smaller than monitor
        mat = ET.SubElement(screen_vis, 'material')
        ET.SubElement(mat, 'ambient').text = '0.1 0.6 1.0 1'
        ET.SubElement(mat, 'diffuse').text = '0.1 0.6 1.0 1'
        # Optional: emissive for glow
        ET.SubElement(mat, 'emissive').text = '0.1 0.4 0.8 1'

# 6. Grab Zone - Add Yellow and Black Hazard Stripes
for link in ward.findall('.//link'):
    if link.attrib.get('name') == 'grab_zone_pharmacy':
        # Clear existing visuals
        for vis in link.findall('visual'): link.remove(vis)
        
        # Base yellow
        base_vis = ET.SubElement(link, 'visual', {'name': 'gz_base'})
        geom = ET.SubElement(base_vis, 'geometry')
        ET.SubElement(geom, 'box').append(ET.fromstring('<size>2.0 0.3 0.01</size>'))
        mat = ET.SubElement(base_vis, 'material')
        ET.SubElement(mat, 'script').append(ET.fromstring('<name>Gazebo/Yellow</name>'))
        
        # Black stripes (straight vertical stripes to emulate hazard area)
        for i in range(10):
            x_offset = -0.9 + i * 0.2
            s_vis = ET.SubElement(link, 'visual', {'name': f'gz_stripe_{i}'})
            ET.SubElement(s_vis, 'pose').text = f'{x_offset:.1f} 0 0.001 0 0 0' # slightly above base
            s_geom = ET.SubElement(s_vis, 'geometry')
            ET.SubElement(s_geom, 'box').append(ET.fromstring('<size>0.1 0.3 0.01</size>'))
            s_mat = ET.SubElement(s_vis, 'material')
            ET.SubElement(s_mat, 'script').append(ET.fromstring('<name>Gazebo/Black</name>'))

tree.write(world_file, xml_declaration=True, encoding='utf-8')
print("Pharmacy perfected.")
