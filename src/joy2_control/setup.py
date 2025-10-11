from glob import glob
from os import path
from setuptools import find_packages, setup

package_name = 'joy2_control'

setup(
    name=package_name,
    version='1.2.0',
    packages=find_packages(include=['joy2_control', 'joy2_control.*']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (path.join('share', package_name, 'launch'), glob(path.join('launch', '*launch.py'))),
        (path.join('share', package_name, 'config'), glob(path.join('config', '*.yaml'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='yoann',
    maintainer_email='yoann.hervieux@gmail.com',
    description='Control nodes for Joy2 robot',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'test_talker = joy2_control.test_talker:main',
            'test_listener = joy2_control.test_listener:main',
            'buzzer_node = joy2_control.nodes.buzzer_node:main',
            'servo_node = joy2_control.nodes.servo_node:main',
            'joy2_teleop = joy2_control.nodes.joy2_teleop:main',
            'mecanum_node = joy2_control.nodes.mecanum_node:main',
            'camera_node = joy2_control.nodes.camera_node:main',
            'webrtc_node = joy2_control.nodes.webrtc_node:main',
            'imu_node = joy2_control.nodes.imu_node:main',
        ],
    },
)