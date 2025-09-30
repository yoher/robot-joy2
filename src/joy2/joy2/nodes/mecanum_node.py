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
from geometry_msgs.msg import TwistStamped
from joy2.hardware.motor import DCMotorDriver
from joy2.hardware.pca9685 import PCA9685
from joy2.control.mecanum_controller import MecanumDriveController


class MecanumNode(Node):
    """
    ROS2 node for mecanum drive motor control.
    Subscribes to TwistStamped messages and controls mecanum wheels.
    """

    def __init__(self):
        super().__init__('mecanum_node')

        # Declare parameters
        self.declare_parameter('pca_address', 0x60)
        self.declare_parameter('motor_frequency', 50.0)
        self.declare_parameter('translation_scale', 0.6)
        self.declare_parameter('rotation_scale', 0.6)
        self.declare_parameter('eps', 0.02)
        self.declare_parameter('invert_omega', False)
        self.declare_parameter('verbose', False)
        self.declare_parameter('cmd_timeout', 1.0)

        # Get parameters
        pca_address = self.get_parameter('pca_address').value
        motor_frequency = self.get_parameter('motor_frequency').value
        translation_scale = self.get_parameter('translation_scale').value
        rotation_scale = self.get_parameter('rotation_scale').value
        eps = self.get_parameter('eps').value
        invert_omega = self.get_parameter('invert_omega').value
        verbose = self.get_parameter('verbose').value
        self.cmd_timeout = self.get_parameter('cmd_timeout').value

        # Initialize motor hardware
        try:
            self._motor_pca = PCA9685(i2c_address=pca_address)
            self._motor_pca.set_pwm_frequency(int(motor_frequency))
            
            self._motor_driver = DCMotorDriver(self._motor_pca, verbose=verbose)
            self._mecanum_controller = MecanumDriveController(
                self._motor_driver,
                translation_scale=translation_scale,
                rotation_scale=rotation_scale,
                eps=eps,
                invert_omega=invert_omega,
                verbose=verbose
            )
            
            self.get_logger().info(f"Motor hardware initialized at I2C address 0x{pca_address:02X}")
            self.get_logger().info(f"Motor PWM frequency: {motor_frequency}Hz")
            self.get_logger().info(f"Translation scale: {translation_scale}, Rotation scale: {rotation_scale}")
            self.get_logger().info(f"Epsilon (change threshold): {eps}")
            self.get_logger().info(f"Invert omega: {invert_omega}")
            self.get_logger().info(f"Command timeout: {self.cmd_timeout}s")
            
        except Exception as e:
            self.get_logger().error(f"Failed to initialize motor hardware: {e}")
            self._motor_driver = None
            self._mecanum_controller = None
            return

        # Track last command time for safety timeout
        self._last_cmd_time = self.get_clock().now()
        self._timeout_active = False

        # Create subscription to cmd_vel topic
        self._cmd_vel_subscription = self.create_subscription(
            TwistStamped,
            'cmd_vel',
            self._cmd_vel_callback,
            10
        )

        # Create timer for safety timeout checking
        self._safety_timer = self.create_timer(0.1, self._safety_timer_callback)

        self.get_logger().info("Mecanum node initialized and ready")
        self.get_logger().info("Subscribing to /cmd_vel (geometry_msgs/TwistStamped)")

    def _cmd_vel_callback(self, msg):
        """
        Handle incoming velocity commands.
        
        Args:
            msg (TwistStamped): Velocity command message
        """
        if not self._mecanum_controller:
            return

        try:
            # Extract velocity components
            vx = msg.twist.linear.x      # Forward/backward
            vy = msg.twist.linear.y      # Strafe left/right
            omega = msg.twist.angular.z  # Rotation

            # Update last command time
            self._last_cmd_time = self.get_clock().now()
            self._timeout_active = False

            # Send to mecanum controller
            self._mecanum_controller.drive(vx, vy, omega)

            self.get_logger().debug(
                f"Velocity command: vx={vx:.3f}, vy={vy:.3f}, omega={omega:.3f}"
            )

        except Exception as e:
            self.get_logger().error(f"Error processing velocity command: {e}")

    def _safety_timer_callback(self):
        """
        Check for command timeout and stop motors if necessary.
        This provides a safety feature to stop the robot if no commands are received.
        """
        if not self._mecanum_controller:
            return

        try:
            current_time = self.get_clock().now()
            time_since_last_cmd = (current_time - self._last_cmd_time).nanoseconds / 1e9

            # If timeout exceeded and not already in timeout state, stop motors
            if time_since_last_cmd > self.cmd_timeout and not self._timeout_active:
                self.get_logger().warn(
                    f"Command timeout ({self.cmd_timeout}s) exceeded. Stopping motors for safety."
                )
                self._mecanum_controller.stop()
                self._timeout_active = True

        except Exception as e:
            self.get_logger().error(f"Error in safety timer: {e}")

    def destroy_node(self):
        """
        Cleanup when node is destroyed.
        Ensures all motors are stopped properly.
        """
        self.get_logger().info("Shutting down mecanum node...")
        
        # Stop all motors
        if self._mecanum_controller:
            self._mecanum_controller.stop()
            self.get_logger().info("Motors stopped")

        # Release all motors
        if self._motor_driver:
            self._motor_driver.release_all()
            self.get_logger().info("All motors released")

        # Stop all PWM signals
        if self._motor_pca:
            self._motor_pca.set_all_pwm(0, 0)
            self.get_logger().info("PWM signals stopped")

        super().destroy_node()


def main(args=None):
    """
    Main function to run the mecanum node.
    """
    rclpy.init(args=args)

    mecanum_node = MecanumNode()

    try:
        rclpy.spin(mecanum_node)
    except KeyboardInterrupt:
        pass
    finally:
        mecanum_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()