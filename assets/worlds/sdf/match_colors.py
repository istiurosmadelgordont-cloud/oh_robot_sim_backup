import xml.etree.ElementTree as ET

world_file = r'd:\飞腾派\plan\2\oh_robot_sim\assets\worlds\sdf\hospital_ward.classic.world'
tree = ET.parse(world_file)
ward = [m for m in tree.getroot().findall('.//model') if m.attrib.get('name') == 'hospital_ward'][0]
root = tree.getroot()

med_colors = {}
for m in root.findall('.//model'):
    name = m.attrib.get('name', '')
    if name.startswith('medicine_box_'):
        parts = name.split('_')
        L = int(parts[2][1:]) - 1
        i = int(parts[3]) - 1
        ambient = m.find('.//material/ambient')
        diffuse = m.find('.//material/diffuse')
        if ambient is not None and diffuse is not None:
            med_colors[f'L{L}_{i}'] = (ambient.text, diffuse.text)

for link in ward.findall('.//link'):
    name = link.attrib.get('name', '')
    if name.startswith('shelf_tag_'):
        parts = name.split('_')
        key = f'{parts[2]}_{parts[3]}'
        if key in med_colors:
            mat = link.find('.//visual/material')
            if mat is not None:
                scr = mat.find('script')
                if scr is not None: mat.remove(scr)
                
                amb = mat.find('ambient')
                if amb is None: amb = ET.SubElement(mat, 'ambient')
                amb.text = med_colors[key][0]
                
                diff = mat.find('diffuse')
                if diff is None: diff = ET.SubElement(mat, 'diffuse')
                diff.text = med_colors[key][1]

tree.write(world_file, xml_declaration=True, encoding='utf-8')
print("Colors matched.")
