from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    TimerAction,
    OpaqueFunction
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command, TextSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():

    # Launch arguments
    drive_type = LaunchConfiguration('drive_type')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    use_gui = LaunchConfiguration('use_gui', default='true')

    # Package shares
    joy2_bringup_share = FindPackageShare('joy2_bringup')
    joy2_description_share = FindPackageShare('joy2_description')

    # World file path - get as string
    world_file = os.path.join(
        get_package_share_directory('joy2_bringup'),
        'worlds',
        'empty_world.sdf'
    )

    # Set up Gazebo environment - add ros2_control plugin path
    gz_env = os.environ.copy()
    gz_plugin_path = '/opt/ros/jazzy/lib'
    if 'GZ_SIM_SYSTEM_PLUGIN_PATH' in gz_env:
        gz_env['GZ_SIM_SYSTEM_PLUGIN_PATH'] = gz_env['GZ_SIM_SYSTEM_PLUGIN_PATH'] + ':' + gz_plugin_path
    else:
        gz_env['GZ_SIM_SYSTEM_PLUGIN_PATH'] = gz_plugin_path

    # Gazebo launch with GUI
    gazebo_launch_gui = ExecuteProcess(
        cmd=['gz', 'sim', '-r', world_file],
        output='screen',
        additional_env=gz_env,
        condition=IfCondition(use_gui)
    )
    
    # Gazebo launch headless
    gazebo_launch_headless = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-s', world_file],
        output='screen',
        additional_env=gz_env,
        condition=UnlessCondition(use_gui)
    )

    # Robot spawn using ros_gz_sim spawner (more reliable)
    robot_spawn = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_robot',
        arguments=[
            '-world', 'empty_world',
            '-topic', '/robot_description',
            '-name', 'joy2',
            '-x', '0.0',
            '-y', '0.0', 
            '-z', '0.15'  # Spawn 15cm above ground to prevent collision on spawn
        ],
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

    # Joint state publisher GUI for manual control (when ROS2 Control isn't available)
    # This publishes joint states which robot_state_publisher uses to compute TF transforms
    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(use_gui)
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

        # Start Gazebo (conditional GUI)
        gazebo_launch_gui,
        gazebo_launch_headless,

        # Timer to ensure Gazebo is ready before starting nodes
        TimerAction(
            period=5.0,  # Increased from 3.0 to give Gazebo more time
            actions=[
                robot_state_publisher,
                bridge,
                joint_state_publisher_gui,
            ]
        ),

        # Start control system after robot description is available
        TimerAction(
            period=7.0,  # Increased timing
            actions=[
                control_system,
                rviz
            ]
        ),

        # Robot spawn after everything else is ready
        TimerAction(
            period=10.0,  # Increased from 6.0 to ensure everything is ready
            actions=[robot_spawn]
        ),
    ])
