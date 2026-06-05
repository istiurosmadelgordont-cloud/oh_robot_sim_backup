import os
import tarfile

base_dir = r"d:\飞腾派\plan\2\oh_robot_sim\assets\models\sdf"
extract_dir = os.path.join(base_dir, "extracted")

if not os.path.exists(extract_dir):
    os.makedirs(extract_dir)

targets = [
    "assets_models_aws_robomaker_warehouse_DeskC_01.tar.xz",
    "assets_models_aws_robomaker_residential_Wardrobe_01.tar.xz",
    "assets_models_aws_robomaker_residential_Tablet_01.tar.xz",
    "assets_models_aws_robomaker_residential_TV_01.tar.xz",
    "assets_models_aws_robomaker_residential_Bed_01.tar.xz"
]

for target in targets:
    tar_path = os.path.join(base_dir, target)
    print(f"Extracting {target}...")
    try:
        with tarfile.open(tar_path, "r:xz") as t:
            t.extractall(path=extract_dir)
        print("Success.")
    except Exception as e:
        print(f"Failed to extract {target}: {e}")

print("All extractions completed.")
