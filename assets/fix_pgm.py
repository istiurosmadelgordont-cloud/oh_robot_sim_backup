import os
from PIL import Image

def fix_map(map_path):
    img = Image.open(map_path)
    img = img.convert('L')
    pixels = img.load()
    width, height = img.size

    origin_x = -8.5
    origin_y = -6.5
    resolution = 0.05

    # North Ward clearing
    for x in range(int((-6.8 - origin_x)/resolution), int((2.8 - origin_x)/resolution)):
        for y in range(int((1.1 - origin_y)/resolution), int((4.9 - origin_y)/resolution)):
            py = height - 1 - y
            if 0 <= x < width and 0 <= py < height:
                pixels[x, py] = 254

    # South Ward clearing
    for x in range(int((-6.8 - origin_x)/resolution), int((2.8 - origin_x)/resolution)):
        for y in range(int((-4.9 - origin_y)/resolution), int((-1.1 - origin_y)/resolution)):
            py = height - 1 - y
            if 0 <= x < width and 0 <= py < height:
                pixels[x, py] = 254

    img.save(map_path)
    print(f"Fixed {map_path}")

src_path = "/root/workspace/assets/maps/slam2d/hospital_ward.pgm"
install_path = "/root/workspace/install/asset_maps/share/asset_maps/slam2d/hospital_ward.pgm"

fix_map(src_path)
fix_map(install_path)
