from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    TimerAction
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command, TextSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    # Launch arguments
    drive_type = LaunchConfiguration('drive_type')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    use_gui = LaunchConfiguration('use_gui', default='true')

    # Package shares
    joy2_bringup_share = FindPackageShare('joy2_bringup')
    joy2_description_share = FindPackageShare('joy2_description')

    # Simple Gazebo launch (just start the simulator)
    gazebo_launch = ExecuteProcess(
        cmd=['gz', 'sim', '-v', '4'],  # Verbose mode to see what's happening
        output='screen'
    )

    # Robot state publisher (always needed)
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': ParameterValue(
                Command([
                    'xacro ',
                    PathJoinSubstitution([joy2_description_share, 'urdf', 'joy2.urdf.xacro']),
                    TextSubstitution(text=' drive_type:='),
                    drive_type
                ]),
                value_type=str
            ),
            'use_sim_time': use_sim_time
        }]
    )

    # Joint state publisher (for manual control if needed)
    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # RViz visualization
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', PathJoinSubstitution([
            joy2_description_share,
            'rviz',
            'robot_view.rviz'
        ])],
        condition=IfCondition(use_gui),
        parameters=[{'use_sim_time': use_sim_time}]
    )

    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument(
            'drive_type',
            default_value='mecanum',
            description='Robot drive type: mecanum or diff'
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time'
        ),
        DeclareLaunchArgument(
            'use_gui',
            default_value='true',
            description='Launch GUI windows (Gazebo and RViz)'
        ),

        # Start Gazebo
        gazebo_launch,

        # Start robot description after short delay
        TimerAction(
            period=3.0,
            actions=[
                robot_state_publisher,
                joint_state_publisher,
                rviz
            ]
        ),
    ])