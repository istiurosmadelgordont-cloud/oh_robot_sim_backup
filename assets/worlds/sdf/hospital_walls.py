import xml.etree.ElementTree as ET
import math

world_file = r'd:\飞腾派\plan\2\oh_robot_sim\assets\worlds\sdf\hospital_ward.classic.world'
tree = ET.parse(world_file)
ward = [m for m in tree.getroot().findall('.//model') if m.attrib.get('name') == 'hospital_ward'][0]

# 1. Remove old ugly decorations
to_remove = []
for l in ward.findall('.//link'):
    if l.attrib.get('name', '').startswith('decor_'):
        to_remove.append(l)
for l in to_remove:
    ward.remove(l)

# 2. Add Wall Skirting (Wainscoting)
wall_names = ['wall_north', 'wall_south', 'wall_west', 'wall_east', 
              'corr_n1', 'corr_n2', 'corr_n3', 'corr_s1', 'corr_s2', 'corr_s3', 
              'div_upper', 'div_lower']

skirt_color = '0.3 0.6 0.8 1' # Medical blue
skirt_thickness = 0.01
skirt_height = 0.8

# Remove existing skirts
for l in ward.findall('.//link'):
    if l.attrib.get('name', '').startswith('skirt_'):
        ward.remove(l)

def create_skirt(name, px, py, pz, roll, pitch, yaw, length, thickness):
    link = ET.SubElement(ward, 'link', {'name': name})
    ET.SubElement(link, 'pose').text = f"{px:.3f} {py:.3f} {pz:.3f} {roll} {pitch} {yaw}"
    vis = ET.SubElement(link, 'visual', {'name': name + '_vis'})
    geom = ET.SubElement(vis, 'geometry')
    ET.SubElement(geom, 'box').append(ET.fromstring(f'<size>{length:.3f} {thickness:.3f} {skirt_height:.3f}</size>'))
    mat = ET.SubElement(vis, 'material')
    ET.SubElement(mat, 'ambient').text = skirt_color
    ET.SubElement(mat, 'diffuse').text = skirt_color

skirt_idx = 0
for l in ward.findall('.//link'):
    name = l.attrib.get('name', '')
    if name in wall_names:
        pose = l.find('pose')
        size = l.find('.//visual/geometry/box/size')
        if pose is not None and size is not None:
            parts = pose.text.split()
            px, py, pz = float(parts[0]), float(parts[1]), float(parts[2])
            roll, pitch, yaw = parts[3], parts[4], parts[5]
            
            s_parts = size.text.split()
            L, W, H = float(s_parts[0]), float(s_parts[1]), float(s_parts[2])
            
            # Yaw could be '1.5708' or similar
            # If yaw is non-zero, parse it. Usually it's just 0 or 1.5708
            yaw_val = float(yaw)
            
            # Offset distance from wall center to outer face
            dY1 = W/2 + skirt_thickness/2
            dY2 = -W/2 - skirt_thickness/2
            
            # Skirt 1
            sx1 = px - dY1 * math.sin(yaw_val)
            sy1 = py + dY1 * math.cos(yaw_val)
            sz1 = skirt_height / 2.0  # Center Z of skirt is 0.4
            create_skirt(f'skirt_{skirt_idx}', sx1, sy1, sz1, roll, pitch, yaw, L, skirt_thickness)
            skirt_idx += 1
            
            # Skirt 2
            sx2 = px - dY2 * math.sin(yaw_val)
            sy2 = py + dY2 * math.cos(yaw_val)
            sz2 = skirt_height / 2.0
            create_skirt(f'skirt_{skirt_idx}', sx2, sy2, sz2, roll, pitch, yaw, L, skirt_thickness)
            skirt_idx += 1

tree.write(world_file, xml_declaration=True, encoding='utf-8')
print("Wall skirting added and ugly decorations removed.")
