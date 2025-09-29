import rclpy
from rclpy.node import Node
import time
import threading
from joy2_interfaces.msg import BuzzerCommand

import sys
import os
from joy2.lib.hardware.buzzer import Buzzer


class BuzzerNode(Node):
    """
    ROS2 node for controlling the robot buzzer.
    Provides ROS2 interface to the existing Buzzer hardware class.
    """

    def __init__(self):
        super().__init__('buzzer_node')

        # Initialize buzzer hardware
        try:
            self._buzzer = Buzzer()
            self.get_logger().info("Buzzer hardware initialized successfully")
        except RuntimeError as e:
            self.get_logger().error(f"Failed to initialize buzzer: {e}")
            self._buzzer = None
        self.get_logger().info("DUMMY Buzzer hardware initialized successfully")

        # Current state
        self._current_frequency = 0
        self._current_duration = 0
        self._is_active = False
        self._timer = None

        # Create subscription to buzzer commands
        self._subscription = self.create_subscription(
            BuzzerCommand,
            'buzzer_command',
            self._command_callback,
            10
        )

        self.get_logger().info("Buzzer node initialized")

    def _command_callback(self, msg):
        """
        Handle incoming buzzer commands.

        Args:
            msg (BuzzerCommand): Command message containing active state, frequency, and duration
        """
        if not self._buzzer:
            self.get_logger().error("Buzzer hardware not available")
            return

        self.get_logger().info(f"Received buzzer command: active={msg.active}, freq={msg.frequency}, duration={msg.duration}")

        # Stop current buzzer if active
        if self._is_active:
            self._stop_buzzer()

        # Handle new command
        if msg.active and msg.frequency > 0:
            self._start_buzzer(msg.frequency, msg.duration)
        elif not msg.active:
            self._stop_buzzer()

    def _start_buzzer(self, frequency, duration):
        """
        Start buzzer with specified frequency and duration.

        Args:
            frequency (int): Frequency in Hz
            duration (int): Duration in milliseconds
        """
        self.get_logger().info(f"TEST Started buzzer at {frequency}Hz for {duration}ms")
        if not self._buzzer:
            return

        try:
            # Set the tone
            self._buzzer.set_tone(frequency)
            self._current_frequency = frequency
            self._current_duration = duration
            self._is_active = True

            self.get_logger().info(f"Started buzzer at {frequency}Hz for {duration}ms")

            # Set timer to stop buzzer after duration
            if duration > 0:
                self._timer = threading.Timer(duration / 1000.0, self._stop_buzzer)
                self._timer.start()

        except Exception as e:
            self.get_logger().error(f"Error starting buzzer: {e}")
            self._is_active = False

    def _stop_buzzer(self):
        """
        Stop the buzzer and cancel any pending timer.
        """
        self.get_logger().info("Buzzer stopped")
        if not self._buzzer:
            return

        try:
            # Cancel timer if active
            if self._timer and self._timer.is_alive():
                self._timer.cancel()
                self._timer = None

            # Stop buzzer
            self._buzzer.stop()
            self._is_active = False

            self.get_logger().info("Buzzer stopped")

        except Exception as e:
            self.get_logger().error(f"Error stopping buzzer: {e}")

    def destroy_node(self):
        """
        Cleanup when node is destroyed.
        """
        self._stop_buzzer()
        if self._buzzer:
            self._buzzer.close()
        super().destroy_node()


def main(args=None):
    """
    Main function to run the buzzer node.
    """
    rclpy.init(args=args)

    buzzer_node = BuzzerNode()

    try:
        rclpy.spin(buzzer_node)
    except KeyboardInterrupt:
        pass
    finally:
        buzzer_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()