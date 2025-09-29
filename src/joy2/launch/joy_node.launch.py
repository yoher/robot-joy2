from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='joy2',
            executable='joy_node',
            name='joy_node',
            output='screen',
            parameters=[
                {'device_id': 0},
                {'deadzone': 0.05},
                {'autorepeat_rate': 20.0},
                {'coalesce_interval': 0.01}
            ],
        ),
    ])