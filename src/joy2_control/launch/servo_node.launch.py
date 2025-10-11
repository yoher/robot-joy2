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
                # Use configuration file (can be overridden via command line)
                {'config_file': 'src/joy2/config/servo_config.yaml'}
            ],
        ),
    ])