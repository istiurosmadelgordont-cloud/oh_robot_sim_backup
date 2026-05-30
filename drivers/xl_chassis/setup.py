import os
from setuptools import find_packages, setup

package_name = "xl_chassis"

def recursive_get_files(domain_dir: str):
    target = []
    for root, _, files in os.walk(domain_dir):
        files_path = [os.path.join(root, f) for f in files]
        if files_path:
            # 目标路径：share/${package_name}/${domain_dir}/相对路径
            dest = os.path.join('share', package_name, root)
            target.append((dest, files_path))
    return target

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        *recursive_get_files('launch'),
        *recursive_get_files('config'),
    ],
    install_requires=["setuptools", "requests"],
    zip_safe=True,
    maintainer="hydroiodic",
    maintainer_email="liao_chengfan@sjtu.edu.cn",
    description="TODO: Package description",
    license="TODO: License declaration",
    extras_require={
        "test": [
            "pytest",
        ],
    },
    entry_points={
        "console_scripts": [
            "controller_node = xl_chassis.controller_node:main",
            "pose_node = xl_chassis.pose_node:main",
            "lazer_node = xl_chassis.lazer_node:main",
            "rnav2_node = xl_chassis.navigation2node:main",
            "nav2_node = xl_chassis.navigation_node:main"
        ],
    },
)
