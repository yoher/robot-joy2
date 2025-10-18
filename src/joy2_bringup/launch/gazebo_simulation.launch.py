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
import os

def generate_launch_description():

    # Launch arguments
    drive_type = LaunchConfiguration('drive_type')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    use_gui = LaunchConfiguration('use_gui', default='true')

    # Package shares
    joy2_bringup_share = FindPackageShare('joy2_bringup')
    joy2_description_share = FindPackageShare('joy2_description')

    # Gazebo launch
    gazebo_launch = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-s'],
        output='screen'
    )

    # Robot spawn (simplified)
    robot_spawn = ExecuteProcess(
        cmd=['gz', 'service', '-s', '/world/empty/create',
             '--reqtype', 'gz.msgs.EntityFactory',
             '--reptype', 'gz.msgs.Boolean',
             '--timeout', '5000',
             '--req', 'name: "joy2", pose: {position: {x: 0.0, y: 0.0, z: 0.1}}'],
        output='screen'
    )

    # Robot state publisher
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

    # ROS-Gazebo bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/imu/data@sensor_msgs/msg/Imu[gz.msgs.IMU',
            '/cmd_vel@geometry_msgs/msg/Twist[gz.msgs.Twist',
            '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model'
        ],
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # Control system
    control_system = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                joy2_bringup_share,
                'launch',
                'complete_system.launch.py'
            ])
        ),
        launch_arguments={
            'drive_type': drive_type,
            'use_sim_time': use_sim_time,
            'use_sim': 'true'
        }.items()
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

        # Timer to ensure Gazebo is ready before starting nodes
        TimerAction(
            period=3.0,
            actions=[
                robot_state_publisher,
                bridge,
                control_system,
                rviz
            ]
        ),

        # Robot spawn after delay
        TimerAction(
            period=6.0,
            actions=[robot_spawn]
        ),
    ])
