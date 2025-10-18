from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='joy2_control',
            executable='buzzer_node',
            name='buzzer_node',
            output='screen',
            parameters=[],
        ),
    ])