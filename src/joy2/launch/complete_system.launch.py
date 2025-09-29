from launch import LaunchDescription
from launch.actions import SetEnvironmentVariable
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        
        SetEnvironmentVariable(
            name='RCUTILS_CONSOLE_OUTPUT_FORMAT',
            # value='[{time}] [{severity}] [{name}]: {message}'
            value='[{time}] [{severity}] [{name}:{function_name}]: {message}'
        ),
        
        # Gamepad input node
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            output='screen',
            parameters=[
                {'device_id': 0},
                {'deadzone': 0.05},
                {'autorepeat_rate': 20.0},
                {'coalesce_interval': 0.001}
            ],
        ),

        # Buzzer control node
        Node(
            package='joy2',
            executable='buzzer_node',
            name='buzzer_node',
            output='screen',
            parameters=[],
        ),

        # Joy2 Teleoperation node
        Node(
            package='joy2',
            executable='joy2_teleop',
            name='joy2_teleop',
            output='screen',
            parameters=[],
        ),

        # Servo control node
        Node(
            package='joy2',
            executable='servo_node',
            name='servo_node',
            output='screen',
            parameters=[
                {'pca_address': 0x60},
                {'servo_frequency': 50.0},
                {'allowed_continuous_channels': [8, 9]},
                {'allow_positional': False},
            ],
        ),

        # # Mecanum drive control node
        # Node(
        #     package='joy2',
        #     executable='mecanum_node',
        #     name='mecanum_node',
        #     output='screen',
        #     parameters=[
        #         {'pca_address': 0x60},
        #         {'motor_frequency': 50.0},
        #         {'translation_scale': 0.6},
        #         {'rotation_scale': 0.6}
        #     ],
        # ),
        
        # # Camera streaming node
        # Node(
        #     package='joy2',
        #     executable='camera_node',
        #     name='camera_node',
        #     output='screen',
        #     parameters=[
        #         {'camera_id': 0},
        #         {'width': 640},
        #         {'height': 480},
        #         {'fps': 30},
        #         {'device': '/dev/video0'}
        #     ],
        # ),
        
        # # Web bridge node for web interface
        # Node(
        #     package='joy2',
        #     executable='web_bridge_node',
        #     name='web_bridge_node',
        #     output='screen',
        #     parameters=[
        #         {'websocket.host': '0.0.0.0'},
        #         {'websocket.port': 8081},
        #         {'websocket.max_connections': 10},
        #         {'websocket.ping_interval': 20},
        #         {'websocket.ping_timeout': 10},
        #         {'websocket.close_timeout': 5},
        #         {'security.enable_auth': True},
        #         {'security.session_timeout': 3600},
        #         {'websocket.max_message_rate': 100},
        #         {'compression.enable': True},
        #         {'compression.threshold': 1024}
        #     ],
        # ),
    ])