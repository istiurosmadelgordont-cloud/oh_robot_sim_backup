import xml.etree.ElementTree as ET

# 1. Fix SDF World
world_file = r'd:\飞腾派\plan\2\oh_robot_sim\assets\worlds\sdf\hospital_ward.classic.world'
tree = ET.parse(world_file)
ward = [m for m in tree.getroot().findall('.//model') if m.attrib.get('name') == 'hospital_ward'][0]

for i in range(1, 3):
    for j in range(1, 5):
        bed_name = f'bed_w{i}_{j}'
        bed = None
        for l in ward.findall('.//link'):
            if l.attrib.get('name') == bed_name: bed = l; break
        
        if bed is not None:
            parts = bed.find('pose').text.split()
            # Ward 1 (top): head to +Y -> yaw = 0
            # Ward 2 (bottom): head to -Y -> yaw = 3.14159
            yaw = '0' if i == 1 else '3.14159'
            bed.find('pose').text = f'{parts[0]} {parts[1]} {parts[2]} 0 0 {yaw}'
            
        sz_name = f'sign_zone_w{i}_{j}'
        sz = None
        for l in ward.findall('.//link'):
            if l.attrib.get('name') == sz_name: sz = l; break
            
        if sz is not None and bed is not None:
            bed_x = float(bed.find('pose').text.split()[0])
            bed_y = float(bed.find('pose').text.split()[1])
            new_x = bed_x + 0.75
            # Ward 1: foot is at -Y -> shift Y by -0.75
            # Ward 2: foot is at +Y -> shift Y by +0.75
            new_y = bed_y - 0.75 if i == 1 else bed_y + 0.75
            
            sz.find('pose').text = f'{new_x} {new_y} 0.005 0 0 0'
            box_size = sz.find('.//box/size')
            if box_size is not None:
                box_size.text = '0.5 0.5 0.01'

tree.write(world_file, xml_declaration=True, encoding='utf-8')

# 2. Fix task server
ts_file = r'd:\飞腾派\plan\2\oh_robot_sim\demos\demos\ward_task_server.py'
text = open(ts_file, encoding='utf-8').read()
text = text.replace("'bed_y': sy,", "'bed_y': sy - 0.75 if sy > 0 else sy + 0.75,")
open(ts_file, 'w', encoding='utf-8').write(text)

print('Fix applied successfully.')
