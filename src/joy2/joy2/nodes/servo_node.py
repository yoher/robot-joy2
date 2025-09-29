import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.action import CancelResponse, GoalResponse
import time
import threading
from joy2_interfaces.msg import ServoCommand
# from joy2_interfaces.action import ServoCalibration

# Import des classes existantes
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../src'))
from joy2.hardware.servo import Servo, ContinuousServo
from joy2.hardware.pca9685 import PCA9685
from joy2.control.servo_controller import ServoController
from joy2.config.config import get_servos_cfg


class ServoNode(Node):
    """
    ROS2 node for controlling robot servos.
    Provides ROS2 interface to existing Servo and ServoController classes.
    """

    def __init__(self):
        super().__init__('servo_node')

        # Initialize PCA9685
        try:
            self._pca = PCA9685()
            self._pca.set_pwm_freq(50)  # Standard servo frequency
            self.get_logger().info("PCA9685 initialized successfully")
        except Exception as e:
            self.get_logger().error(f"Failed to initialize PCA9685: {e}")
            self._pca = None

        # Initialize servo controller for continuous servos
        self._servo_controller = None
        if self._pca:
            try:
                # Load configuration
                from joy2.config.config import load_config
                cfg = load_config()
                self._servo_controller = ServoController(self._pca, cfg, verbose=False)
                self.get_logger().info("ServoController initialized successfully")
            except Exception as e:
                self.get_logger().error(f"Failed to initialize ServoController: {e}")

        # Individual servos dictionary (servo_id -> Servo instance)
        self._servos = {}
        self._current_angles = {}

        # Create subscription to servo commands
        self._subscription = self.create_subscription(
            ServoCommand,
            'servo_command',
            self._command_callback,
            10
        )

        # Create action server for calibration
        self._action_server = ActionServer(
            self,
            ServoCalibration,
            'servo_calibration',
            execute_callback=self._calibration_execute_callback,
            cancel_callback=self._calibration_cancel_callback,
            goal_callback=self._calibration_goal_callback
        )

        self.get_logger().info("Servo node initialized")

    def _command_callback(self, msg):
        """
        Handle incoming servo commands.

        Args:
            msg (ServoCommand): Command message containing servo_id, angle, and speed
        """
        if not self._pca:
            self.get_logger().error("PCA9685 not available")
            return

        self.get_logger().info(f"Received servo command: id={msg.servo_id}, angle={msg.angle}, speed={msg.speed}")

        try:
            if msg.servo_id < 0:
                # Control continuous servos through ServoController
                if self._servo_controller:
                    self._servo_controller.set_speeds(msg.angle, msg.speed)
                    self.get_logger().info(f"Set continuous servo speeds: s1={msg.angle}, s2={msg.speed}")
                else:
                    self.get_logger().error("ServoController not available")
            else:
                # Control individual positional servo
                if msg.servo_id not in self._servos:
                    self._servos[msg.servo_id] = Servo(self._pca, msg.servo_id)
                    self.get_logger().info(f"Created servo instance for ID {msg.servo_id}")

                servo = self._servos[msg.servo_id]
                servo.set_angle(int(msg.angle))
                self._current_angles[msg.servo_id] = msg.angle
                self.get_logger().info(f"Set servo {msg.servo_id} to angle {msg.angle}")

        except Exception as e:
            self.get_logger().error(f"Error executing servo command: {e}")

    def _calibration_goal_callback(self, goal_request):
        """
        Accept or reject calibration goal.

        Args:
            goal_request: Calibration goal request

        Returns:
            GoalResponse: ACCEPT or REJECT
        """
        self.get_logger().info("Received calibration goal request")
        return GoalResponse.ACCEPT

    def _calibration_cancel_callback(self, goal_handle):
        """
        Handle calibration cancellation.

        Args:
            goal_handle: Goal handle to cancel

        Returns:
            CancelResponse: ACCEPT or REJECT
        """
        self.get_logger().info("Calibration cancelled")
        return CancelResponse.ACCEPT

    def _calibration_execute_callback(self, goal_handle):
        """
        Execute servo calibration action.

        Args:
            goal_handle: Goal handle for the calibration action

        Returns:
            ServoCalibration.Result: Calibration result
        """
        self.get_logger().info("Executing servo calibration")

        feedback_msg = ServoCalibration.Feedback()
        result = ServoCalibration.Result()

        try:
            # Perform calibration sequence
            for servo_id in range(16):  # Test all 16 channels
                if goal_handle.is_cancel_requested:
                    result.success = False
                    result.message = "Calibration cancelled"
                    goal_handle.canceled()
                    return result

                # Move to center position
                if servo_id in self._servos:
                    self._servos[servo_id].set_angle(90)
                    feedback_msg.current_servo = servo_id
                    feedback_msg.progress = (servo_id + 1) / 16.0 * 100.0
                    goal_handle.publish_feedback(feedback_msg)
                    time.sleep(0.1)

            result.success = True
            result.message = "Calibration completed successfully"
            goal_handle.succeed(result)

        except Exception as e:
            result.success = False
            result.message = f"Calibration failed: {e}"
            goal_handle.abort(result)

        return result

    def destroy_node(self):
        """
        Cleanup when node is destroyed.
        """
        if self._servo_controller:
            self._servo_controller.stop_all()
        if self._pca:
            self._pca.set_all_pwm(0, 0)  # Stop all PWM signals
        super().destroy_node()


def main(args=None):
    """
    Main function to run the servo node.
    """
    rclpy.init(args=args)

    servo_node = ServoNode()

    try:
        rclpy.spin(servo_node)
    except KeyboardInterrupt:
        pass
    finally:
        servo_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()