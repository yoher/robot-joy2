from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='joy2',
            executable='buzzer_node',
            name='buzzer_node',
            output='screen',
            parameters=[],
        ),
    ])