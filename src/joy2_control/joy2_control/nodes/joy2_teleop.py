#!/usr/bin/env python3
# Copyright 2024 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import TwistStamped
from joy2_interfaces.msg import BuzzerCommand, ServoCommand
from joy2_control.config.teleop_config_loader import TeleopConfigLoader


class Joy2Teleop(Node):
    """
    ROS2 node for joystick teleoperation control.
    Subscribes to joy topic and triggers buzzer when B button is pressed.
    """

    def __init__(self):
        super().__init__('joy2_teleop')

        # Declare configuration file parameter
        self.declare_parameter('config_file', 'src/joy2/config/teleop_config.yaml')

        # Get configuration file path
        config_file = self.get_parameter('config_file').value

        # Load teleop configuration
        try:
            self._config_loader = TeleopConfigLoader(config_file)
            self.get_logger().info(f"Loaded teleop configuration from {config_file}")
        except Exception as e:
            self.get_logger().error(f"Failed to load teleop configuration: {e}")
            self._config_loader = None
            return

        # Load configuration values
        self._alt_button_index = self._config_loader.get_alt_button_index()
        self._alt_button_name = self._config_loader.get_alt_button_name()
        self._buzzer_button_index = self._config_loader.get_buzzer_button_index()
        self._buzzer_frequency = self._config_loader.get_buzzer_frequency()
        self._buzzer_duration = self._config_loader.get_buzzer_duration()
        self._deadzone = self._config_loader.get_deadzone()
        self._min_angle = self._config_loader.get_min_angle()
        self._max_angle = self._config_loader.get_max_angle()

        # Joystick axes (loaded from config)
        self._left_x_axis = self._config_loader.get_left_joystick_x_axis()
        self._left_y_axis = self._config_loader.get_left_joystick_y_axis()
        self._right_x_axis = self._config_loader.get_right_joystick_x_axis()
        self._right_y_axis = self._config_loader.get_right_joystick_y_axis()

        # Servo mappings (loaded from config)
        self._servo_mapping = self._config_loader.get_servo_mapping()

        # Servo instances dictionary (servo_id -> servo instance)
        self._servos = {}

        # Track previous button and axes state
        self._previous_buttons = None
        self._previous_axes = None
        self._alt_pressed = False

        # Track previous deadzone state for each axis (for return-to-center logic)
        self._previous_left_x_in_deadzone = True
        self._previous_left_y_in_deadzone = True
        self._previous_right_x_in_deadzone = True
        self._previous_right_y_in_deadzone = True

        # Track previous deadzone state for wheel control
        self._previous_wheel_vx_in_deadzone = True
        self._previous_wheel_vy_in_deadzone = True
        self._previous_wheel_omega_in_deadzone = True

        # Create publishers
        self._buzzer_publisher = self.create_publisher(
            BuzzerCommand,
            'buzzer_command',
            10
        )

        self._servo_publisher = self.create_publisher(
            ServoCommand,
            'servo_command',
            10
        )

        # Create publisher for velocity commands (mecanum wheel control)
        self._cmd_vel_publisher = self.create_publisher(
            TwistStamped,
            'cmd_vel',
            10
        )

        # Create subscription to joy topic
        self._joy_subscription = self.create_subscription(
            Joy,
            'joy',
            self._joy_callback,
            10
        )

        self.get_logger().info("Joy2Teleop node initialized with configuration")
        self.get_logger().info(f"Alt button: {self._alt_button_name} (index {self._alt_button_index})")
        self.get_logger().info(f"Buzzer button index: {self._buzzer_button_index}")
        self.get_logger().info(f"Buzzer settings - Frequency: {self._buzzer_frequency}Hz, Duration: {self._buzzer_duration}ms")
        self.get_logger().info(f"Servo deadzone: {self._deadzone}")
        self.get_logger().info(f"Wheel deadzone: {self._config_loader.get_wheel_deadzone()}")
        self.get_logger().info(f"Servo mappings: {self._servo_mapping}")
        self.get_logger().info("Publishing velocity commands to /cmd_vel topic")

    def _joy_callback(self, msg):
        """
        Handle incoming joy messages and control both buzzer and servos.

        Args:
            msg (Joy): Joystick message containing axes and buttons state
        """
        try:
            # Initialize previous states if None
            if (self._previous_buttons is None or self._previous_axes is None or
                self._previous_left_x_in_deadzone or
                self._previous_wheel_vx_in_deadzone):
                self._previous_buttons = list(msg.buttons)
                self._previous_axes = list(msg.axes)

                # Initialize deadzone states - initialize to False to ensure centering at start
                self._previous_left_x_in_deadzone = False
                self._previous_left_y_in_deadzone = False
                self._previous_right_x_in_deadzone = False
                self._previous_right_y_in_deadzone = False

                # Initialize wheel deadzone states
                self._previous_wheel_vx_in_deadzone = False
                self._previous_wheel_vy_in_deadzone = False
                self._previous_wheel_omega_in_deadzone = False
                return

            # Check Alt button state (R1 button 7)
            current_alt_state = msg.buttons[self._alt_button_index] if self._alt_button_index < len(msg.buttons) else 0
            previous_alt_state = self._previous_buttons[self._alt_button_index] if self._alt_button_index < len(self._previous_buttons) else 0

            # Update Alt pressed state
            self._alt_pressed = (current_alt_state == 1)

            # Log Alt button state changes
            if current_alt_state == 1 and previous_alt_state == 0:
                self.get_logger().info(f"{self._alt_button_name} pressed - Servo control enabled")
                # Send zero velocity command when switching to servo mode
                self._send_zero_velocity()
            elif current_alt_state == 0 and previous_alt_state == 1:
                self.get_logger().info(f"{self._alt_button_name} released - Servo control disabled")

            # Handle button presses (B button for buzzer) - always available
            current_b_state = msg.buttons[self._buzzer_button_index] if self._buzzer_button_index < len(msg.buttons) else 0
            previous_b_state = self._previous_buttons[self._buzzer_button_index] if self._buzzer_button_index < len(self._previous_buttons) else 0

            if current_b_state == 1 and previous_b_state == 0:
                self.get_logger().info("B button pressed - triggering buzzer")
                self._trigger_buzzer()

            # Handle servo control only when Alt is pressed
            if self._alt_pressed:
                self._control_servos(msg)
            else:
                # Handle wheel control when Alt is not pressed
                self._control_wheels(msg)

                # Log when servo control is disabled but joysticks are moved
                if self._should_log_servo_disabled(msg):
                    self.get_logger().debug("Servo control disabled - Hold R1 to control servos")

            # Update previous states
            self._previous_buttons = list(msg.buttons)
            self._previous_axes = list(msg.axes)

        except Exception as e:
            self.get_logger().error(f"Error processing joy message: {e}")

    def _trigger_buzzer(self):
        """
        Publish buzzer command to activate the buzzer.
        """
        try:
            msg = BuzzerCommand()
            msg.active = True
            msg.frequency = self._buzzer_frequency
            msg.duration = self._buzzer_duration

            self._buzzer_publisher.publish(msg)
            self.get_logger().info(f"Buzzer command sent: active={msg.active}, freq={msg.frequency}Hz, duration={msg.duration}ms")

        except Exception as e:
            self.get_logger().error(f"Error triggering buzzer: {e}")

    def _control_servos(self, msg):
        """
        Control servos based on joystick axes (only when Alt is pressed).

        Args:
            msg (Joy): Joystick message containing current axes state
        """
        try:
            # Get current axes values for both joysticks
            current_left_x = msg.axes[self._left_x_axis] if self._left_x_axis < len(msg.axes) else 0.0
            current_left_y = msg.axes[self._left_y_axis] if self._left_y_axis < len(msg.axes) else 0.0
            current_right_x = msg.axes[self._right_x_axis] if self._right_x_axis < len(msg.axes) else 0.0
            current_right_y = msg.axes[self._right_y_axis] if self._right_y_axis < len(msg.axes) else 0.0

            # Get previous axes values for comparison
            prev_left_x = self._previous_axes[self._left_x_axis] if self._left_x_axis < len(self._previous_axes) else 0.0
            prev_left_y = self._previous_axes[self._left_y_axis] if self._left_y_axis < len(self._previous_axes) else 0.0
            prev_right_x = self._previous_axes[self._right_x_axis] if self._right_x_axis < len(self._previous_axes) else 0.0
            prev_right_y = self._previous_axes[self._right_y_axis] if self._right_y_axis < len(self._previous_axes) else 0.0

            # Apply deadzone with smooth scaling to prevent jitter and sudden jumps
            def apply_deadzone_smooth(value, deadzone):
                """Apply deadzone with smooth scaling outside deadzone."""
                if abs(value) < deadzone:
                    # Within deadzone - return center position for smooth operation
                    return 0.0
                else:
                    # Outside deadzone - scale from deadzone edge to prevent jumps
                    # Map: deadzone → 0.0, 1.0 → (1.0 - deadzone) scaled
                    sign = 1 if value > 0 else -1
                    scaled_value = (abs(value) - deadzone) / (1.0 - deadzone)
                    return sign * scaled_value

            # Check if raw values are in deadzone (before applying smooth deadzone)
            def is_in_deadzone(value, deadzone):
                return abs(value) < deadzone

            current_left_x_in_deadzone = is_in_deadzone(current_left_x, self._deadzone)
            current_left_y_in_deadzone = is_in_deadzone(current_left_y, self._deadzone)
            current_right_x_in_deadzone = is_in_deadzone(current_right_x, self._deadzone)
            current_right_y_in_deadzone = is_in_deadzone(current_right_y, self._deadzone)

            # Apply smooth deadzone scaling
            left_x = apply_deadzone_smooth(current_left_x, self._deadzone)
            left_y = apply_deadzone_smooth(current_left_y, self._deadzone)
            right_x = apply_deadzone_smooth(current_right_x, self._deadzone)
            right_y = apply_deadzone_smooth(current_right_y, self._deadzone)

            # Control servo 1 with left joystick X axis (continuous servo c1)
            if left_x != 0.0:
                # Outside deadzone - send scaled command
                angle_x = self._convert_joystick_to_angle(left_x)
                servo_id = self._servo_mapping.get('left_x_servo', 'c1')
                self._send_servo_command(servo_id, angle_x)
                self.get_logger().debug(f"Left X ({servo_id}): {left_x:.3f} -> {angle_x:.1f}°")
            elif current_left_x_in_deadzone and not self._previous_left_x_in_deadzone:
                # Transitioning into deadzone - send center command
                servo_id = self._servo_mapping.get('left_x_servo', 'c1')
                self._send_servo_command(servo_id, 90.0)
                self.get_logger().debug(f"Left X ({servo_id}): returned to center (deadzone)")

            # Control servo 2 with left joystick Y axis (continuous servo c2)
            if left_y != 0.0:
                # Outside deadzone - send scaled command
                angle_y = self._convert_joystick_to_angle(left_y)
                servo_id = self._servo_mapping.get('left_y_servo', 'c2')
                self._send_servo_command(servo_id, angle_y)
                self.get_logger().debug(f"Left Y ({servo_id}): {left_y:.3f} -> {angle_y:.1f}°")
            elif current_left_y_in_deadzone and not self._previous_left_y_in_deadzone:
                # Transitioning into deadzone - send center command
                servo_id = self._servo_mapping.get('left_y_servo', 'c2')
                self._send_servo_command(servo_id, 90.0)
                self.get_logger().debug(f"Left Y ({servo_id}): returned to center (deadzone)")

            # Control servo 3 with right joystick X axis (positional servo p1)
            if right_x != 0.0:
                # Outside deadzone - send scaled command
                angle_x = self._convert_joystick_to_angle(right_x)
                servo_id = self._servo_mapping.get('right_x_servo', 'p1')
                self._send_servo_command(servo_id, angle_x)
                self.get_logger().debug(f"Right X ({servo_id}): {right_x:.3f} -> {angle_x:.1f}°")
            elif current_right_x_in_deadzone and not self._previous_right_x_in_deadzone:
                # Transitioning into deadzone - send center command
                servo_id = self._servo_mapping.get('right_x_servo', 'p1')
                self._send_servo_command(servo_id, 90.0)
                self.get_logger().debug(f"Right X ({servo_id}): returned to center (deadzone)")

            # Control servo 4 with right joystick Y axis (positional servo p2)
            if right_y != 0.0:
                # Outside deadzone - send scaled command
                angle_y = self._convert_joystick_to_angle(right_y)
                servo_id = self._servo_mapping.get('right_y_servo', 'p2')
                self._send_servo_command(servo_id, angle_y)
                self.get_logger().debug(f"Right Y ({servo_id}): {right_y:.3f} -> {angle_y:.1f}°")
            elif current_right_y_in_deadzone and not self._previous_right_y_in_deadzone:
                # Transitioning into deadzone - send center command
                servo_id = self._servo_mapping.get('right_y_servo', 'p2')
                self._send_servo_command(servo_id, 90.0)
                self.get_logger().debug(f"Right Y ({servo_id}): returned to center (deadzone)")

            # Update previous deadzone states for next iteration
            self._previous_left_x_in_deadzone = current_left_x_in_deadzone
            self._previous_left_y_in_deadzone = current_left_y_in_deadzone
            self._previous_right_x_in_deadzone = current_right_x_in_deadzone
            self._previous_right_y_in_deadzone = current_right_y_in_deadzone

        except Exception as e:
            self.get_logger().error(f"Error controlling servos: {e}")

    def _should_log_servo_disabled(self, msg):
        """
        Check if we should log that servo control is disabled.
        Only log when there's significant joystick movement outside deadzone.

        Args:
            msg (Joy): Current joystick message

        Returns:
            bool: True if we should log the disabled state
        """
        try:
            # Check if any joystick axis has significant movement outside deadzone
            left_x = msg.axes[self._left_x_axis] if self._left_x_axis < len(msg.axes) else 0.0
            left_y = msg.axes[self._left_y_axis] if self._left_y_axis < len(msg.axes) else 0.0
            right_x = msg.axes[self._right_x_axis] if self._right_x_axis < len(msg.axes) else 0.0
            right_y = msg.axes[self._right_y_axis] if self._right_y_axis < len(msg.axes) else 0.0

            # Apply smooth deadzone and check if any axis has significant movement
            def apply_deadzone_smooth(value, deadzone):
                if abs(value) < deadzone:
                    return 0.0
                else:
                    sign = 1 if value > 0 else -1
                    scaled_value = (abs(value) - deadzone) / (1.0 - deadzone)
                    return sign * scaled_value

            # Check if any axis has movement outside deadzone
            return (abs(apply_deadzone_smooth(left_x, self._deadzone)) > 0.001 or
                    abs(apply_deadzone_smooth(left_y, self._deadzone)) > 0.001 or
                    abs(apply_deadzone_smooth(right_x, self._deadzone)) > 0.001 or
                    abs(apply_deadzone_smooth(right_y, self._deadzone)) > 0.001)

        except Exception:
            return False

    def _convert_joystick_to_angle(self, joystick_value):
        """
        Convert joystick axis value (-1.0 to 1.0) to servo angle (0.0 to 180.0).

        Args:
            joystick_value (float): Joystick axis value between -1.0 and 1.0

        Returns:
            float: Servo angle between min_angle and max_angle
        """
        # Clamp joystick value to [-1.0, 1.0] range
        joystick_value = max(-1.0, min(1.0, joystick_value))

        # Convert from [-1.0, 1.0] to [0.0, 1.0] range
        normalized_value = (joystick_value + 1.0) / 2.0

        # Convert to servo angle range using configuration values
        angle = self._min_angle + (normalized_value * (self._max_angle - self._min_angle))

        # Clamp to servo limits
        angle = max(self._min_angle, min(self._max_angle, angle))

        return angle

    def _send_servo_command(self, servo_id, angle):
        """
        Send servo command message.

        Args:
            servo_id (str): ID of the servo to control
            angle (float): Target angle for the servo
        """
        try:
            msg = ServoCommand()
            msg.servo_id = servo_id
            msg.angle = angle

            self._servo_publisher.publish(msg)
            self.get_logger().debug(f"Servo command sent: servo_id={servo_id}, angle={angle:.1f}°")

        except Exception as e:
            self.get_logger().error(f"Error sending servo command: {e}")

    def _control_wheels(self, msg):
        """
        Publish velocity commands for mecanum wheels when Alt is not pressed.

        Args:
            msg (Joy): Joystick message containing current axes state
        """
        try:
            # Get joystick values for wheel control
            # Left joystick X (axis 0) for rotation (omega)
            left_x = msg.axes[self._left_x_axis] if self._left_x_axis < len(msg.axes) else 0.0

            # Right joystick for translation
            # Right X (axis 2) for left/right strafing (vx)
            # Right Y (axis 3) for forward/backward (vy)
            right_x = msg.axes[self._right_x_axis] if self._right_x_axis < len(msg.axes) else 0.0
            right_y = msg.axes[self._right_y_axis] if self._right_y_axis < len(msg.axes) else 0.0

            # Map to mecanum controller inputs (ROS REP 103):
            # vx: forward (+) / backward (-)   [right_y]
            # vy: strafe left (+) / right (-)  [right_x]
            # omega: positive CCW rotation     [left_x]
            vx = -right_y    # Right Y for forward/backward
            vy = -right_x    # Right X for strafing
            omega = left_x   # Left X for rotation

            # Check if raw values are in deadzone (before applying smooth deadzone)
            def is_in_deadzone(value, deadzone):
                return abs(value) < deadzone

            wheel_deadzone = self._config_loader.get_wheel_deadzone()
            current_vx_in_deadzone = is_in_deadzone(vx, wheel_deadzone)
            current_vy_in_deadzone = is_in_deadzone(vy, wheel_deadzone)
            current_omega_in_deadzone = is_in_deadzone(omega, wheel_deadzone)

            # Apply deadzone to wheel control inputs
            def apply_deadzone(value, deadzone):
                if abs(value) < deadzone:
                    return 0.0
                else:
                    sign = 1 if value > 0 else -1
                    scaled_value = (abs(value) - deadzone) / (1.0 - deadzone)
                    return sign * scaled_value

            vx_scaled = apply_deadzone(vx, wheel_deadzone)
            vy_scaled = apply_deadzone(vy, wheel_deadzone)
            omega_scaled = apply_deadzone(omega, wheel_deadzone)

            # Publish velocity command
            twist_msg = TwistStamped()
            twist_msg.header.stamp = self.get_clock().now().to_msg()
            twist_msg.header.frame_id = 'base_link'
            twist_msg.twist.linear.x = vx_scaled
            twist_msg.twist.linear.y = vy_scaled
            twist_msg.twist.angular.z = omega_scaled

            self._cmd_vel_publisher.publish(twist_msg)

            if vx_scaled != 0.0 or vy_scaled != 0.0 or omega_scaled != 0.0:
                self.get_logger().debug(
                    f"Publishing velocity: vx={vx_scaled:.3f}, vy={vy_scaled:.3f}, omega={omega_scaled:.3f}"
                )

            # Update previous wheel deadzone states for next iteration
            self._previous_wheel_vx_in_deadzone = current_vx_in_deadzone
            self._previous_wheel_vy_in_deadzone = current_vy_in_deadzone
            self._previous_wheel_omega_in_deadzone = current_omega_in_deadzone

        except Exception as e:
            self.get_logger().error(f"Error publishing velocity command: {e}")

    def _send_zero_velocity(self):
        """
        Send a zero velocity command to stop the robot.
        """
        try:
            twist_msg = TwistStamped()
            twist_msg.header.stamp = self.get_clock().now().to_msg()
            twist_msg.header.frame_id = 'base_link'
            twist_msg.twist.linear.x = 0.0
            twist_msg.twist.linear.y = 0.0
            twist_msg.twist.angular.z = 0.0

            self._cmd_vel_publisher.publish(twist_msg)
            self.get_logger().debug("Sent zero velocity command")

        except Exception as e:
            self.get_logger().error(f"Error sending zero velocity: {e}")

    def destroy_node(self):
        """
        Cleanup when node is destroyed.
        """
        # Send final zero velocity command
        self._send_zero_velocity()

        # Stop all servos
        for servo_id, servo in self._servos.items():
            if hasattr(servo, 'stop'):  # ContinuousServo has stop method
                servo.stop()

        super().destroy_node()


def main(args=None):
    """
    Main function to run the joy2_teleop node.
    """
    rclpy.init(args=args)

    joy2_teleop = Joy2Teleop()

    try:
        rclpy.spin(joy2_teleop)
    except KeyboardInterrupt:
        pass
    finally:
        joy2_teleop.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()