"""
Launch file for BNO080 IMU sensor node.

This launch file starts the IMU node with configuration from
the imu_config.yaml file.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    """
    Generate launch description for IMU node.
    """
    
    # Declare launch arguments
    config_file_arg = DeclareLaunchArgument(
        'config_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('joy2_control'),
            'config',
            'imu_config.yaml'
        ]),
        description='Path to IMU configuration file'
    )
    
    debug_arg = DeclareLaunchArgument(
        'debug',
        default_value='false',
        description='Enable debug logging'
    )
    
    # Get launch configuration
    config_file = LaunchConfiguration('config_file')
    debug = LaunchConfiguration('debug')
    
    # IMU node
    imu_node = Node(
        package='joy2_control',
        executable='imu_node',
        name='imu_node',
        output='screen',
        parameters=[
            config_file
        ],
        # Optionally set log level based on debug flag
        # arguments=['--ros-args', '--log-level', 'DEBUG'] if debug else []
    )
    
    return LaunchDescription([
        # Set console output format for better readability
        SetEnvironmentVariable(
            name='RCUTILS_CONSOLE_OUTPUT_FORMAT',
            value='[{time}] [{severity}] [{name}]: {message}'
        ),
        
        # Launch arguments
        config_file_arg,
        debug_arg,
        
        # Nodes
        imu_node,
    ])