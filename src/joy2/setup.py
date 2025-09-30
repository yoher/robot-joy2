from glob import glob
from os import path
from setuptools import find_packages, setup

package_name = 'joy2'

setup(
    name=package_name,
    version='1.2.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (path.join('share', package_name, 'launch'), glob(path.join('launch', '*launch.py'))),
        (path.join('share', package_name, 'urdf'), glob(path.join('description', 'urdf', '*.xacro'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='yoann',
    maintainer_email='yoann.hervieux@gmail.com',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'test_talker = joy2.test_talker:main',
            'test_listener = joy2.test_listener:main',
            'buzzer_node = joy2.nodes.buzzer_node:main',
            'servo_node = joy2.nodes.servo_node:main',
            'joy2_teleop = joy2.nodes.joy2_teleop:main',
            'mecanum_node = joy2.nodes.mecanum_node:main',
            'camera_node = joy2.nodes.camera_node:main',
            'webrtc_node = joy2.nodes.webrtc_node:main',
        ],
    },
)
