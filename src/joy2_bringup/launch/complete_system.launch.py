from launch import LaunchDescription
from launch.actions import (
    SetEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, EqualsSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    drive_type = LaunchConfiguration('drive_type')
    use_sim_time = LaunchConfiguration('use_sim_time')

    joy2_control_share = FindPackageShare('joy2_control')
    joy2_bringup_share = FindPackageShare('joy2_bringup')

    mecanum_controller_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                joy2_bringup_share,
                'launch',
                'mecanum_controller.launch.py'
            ])
        ),
        launch_arguments={
            'drive_type': drive_type,
            'use_sim_time': use_sim_time
        }.items(),
        condition=IfCondition(EqualsSubstitution(LaunchConfiguration('drive_type'), 'mecanum'))
    )

    diff_controller_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                joy2_bringup_share,
                'launch',
                'diff_controller.launch.py'
            ])
        ),
        launch_arguments={
            'drive_type': drive_type,
            'use_sim_time': use_sim_time
        }.items(),
        condition=IfCondition(EqualsSubstitution(LaunchConfiguration('drive_type'), 'diff'))
    )

    imu_node = Node(
        package='joy2_control',
        executable='imu_node',
        name='imu_node',
        output='screen',
        parameters=[{
            'config_file': PathJoinSubstitution([
                joy2_control_share,
                'config',
                'imu_config.yaml'
            ]),
            'use_sim_time': use_sim_time
        }]
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'drive_type',
            default_value='mecanum',
            description='Select drive type: mecanum or diff'
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation time if true'
        ),
        SetEnvironmentVariable(
            name='RCUTILS_CONSOLE_OUTPUT_FORMAT',
            value='[{time}] [{severity}] [{name}:{function_name}]: {message}'
        ),
        mecanum_controller_launch,
        diff_controller_launch,
        imu_node,
    ])