import xml.etree.ElementTree as ET

world_file = r'd:\飞腾派\plan\2\oh_robot_sim\assets\worlds\sdf\hospital_ward.classic.world'
tree = ET.parse(world_file)
ward = [m for m in tree.getroot().findall('.//model') if m.attrib.get('name') == 'hospital_ward'][0]

# 1. Fix Wall Materials
wall_names = ['wall_north', 'wall_south', 'wall_west', 'wall_east', 
              'corr_n1', 'corr_n2', 'corr_n3', 'corr_s1', 'corr_s2', 'corr_s3', 
              'div_upper', 'div_lower']

for l in ward.findall('.//link'):
    if l.attrib.get('name') in wall_names:
        mat = l.find('.//visual/material')
        if mat is not None:
            for tag in ['ambient', 'diffuse', 'script']:
                for e in mat.findall(tag): mat.remove(e)
            scr = ET.SubElement(mat, 'script')
            ET.SubElement(scr, 'name').text = 'Gazebo/White'

# 2. Fix Poster Poses (Z=0.8)
def update_pose(name, pose):
    for l in ward.findall('.//link'):
        if l.attrib.get('name') == name:
            l.find('pose').text = pose

update_pose('decor_sign_pharm_desk', '6.92 3.0 0.8 0 0 0')
update_pose('decor_sign_pharm_door', '3.08 3.0 0.8 0 0 0')
update_pose('decor_sign_w1', '-2.0 4.92 0.8 0 0 0')
update_pose('decor_sign_w2', '-2.0 -4.92 0.8 0 0 0')
update_pose('decor_sign_corr', '0.0 0.92 0.8 0 0 0')

# 3. Fix Ceiling Lights (Z=1.3)
for l in ward.findall('.//link'):
    if l.attrib.get('name', '').startswith('decor_light_'):
        pose = l.find('pose')
        if pose is not None:
            parts = pose.text.split()
            parts[2] = '1.3'
            pose.text = ' '.join(parts)

tree.write(world_file, xml_declaration=True, encoding='utf-8')
print('Walls updated and decorations fixed.')
