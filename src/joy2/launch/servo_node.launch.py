from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='joy2',
            executable='servo_node',
            name='servo_node',
            output='screen',
            parameters=[
                {'pca_address': 0x40},
                {'servo_frequency': 50.0},
                {'default_angle': 90.0}
            ],
        ),
    ])