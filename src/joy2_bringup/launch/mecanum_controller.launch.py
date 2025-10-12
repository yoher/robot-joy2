from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
    Command,
    FindExecutable,
    PythonExpression,
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    drive_type = LaunchConfiguration('drive_type')
    use_sim_time = LaunchConfiguration('use_sim_time')

    joy2_description_share = FindPackageShare('joy2_description')
    joy2_share = FindPackageShare('joy2')

    xacro_file = PathJoinSubstitution([joy2_description_share, 'urdf', 'joy2.urdf.xacro'])
    drive_param = PythonExpression(["'drive_type:=' + '", drive_type, "'"])

    robot_description = ParameterValue(
        Command([
            FindExecutable(name='xacro'),
            ' ',
            xacro_file,
            ' ',
            PythonExpression(["'drive_type:=' + '", drive_type, "'"])
        ]),
        value_type=str
    )

    mecanum_config = PathJoinSubstitution([joy2_share, 'config', 'mecanum_controller.yaml'])

    controller_manager_node = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[mecanum_config, {'robot_description': robot_description, 'use_sim_time': use_sim_time}],
        output='screen'
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        output='screen'
    )

    mecanum_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['mecanum_controller'],
        output='screen'
    )

    return LaunchDescription([
        DeclareLaunchArgument('drive_type', default_value='mecanum'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        controller_manager_node,
        joint_state_broadcaster_spawner,
        mecanum_controller_spawner
    ])