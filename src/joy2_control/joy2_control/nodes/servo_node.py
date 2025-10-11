import rclpy
from rclpy.node import Node
import time
import threading
from joy2_interfaces.msg import ServoCommand

# Import hardware classes
from joy2_control.hardware.servo import Servo, ContinuousServo
from joy2_control.hardware.pca9685 import PCA9685
from joy2_control.config.servo_config_loader import ServoConfigLoader


class ServoNode(Node):
    """
    ROS2 node for controlling robot servos.
    Provides ROS2 interface to existing Servo and ServoController classes.
    """

    def __init__(self):
        super().__init__('servo_node')

        # Declare configuration file parameter
        self.declare_parameter('config_file', 'src/joy2/config/servo_config.yaml')

        # Get configuration file path
        config_file = self.get_parameter('config_file').value

        # Load servo configuration
        try:
            self._config_loader = ServoConfigLoader(config_file)
            self.get_logger().info(f"Loaded servo configuration from {config_file}")
            self.get_logger().info(f"Configured servos: {self._config_loader.get_all_servo_ids()}")
        except Exception as e:
            self.get_logger().error(f"Failed to load servo configuration: {e}")
            self._config_loader = None
            return

        # Initialize PCA9685 using configuration
        try:
            pca_address = self._config_loader.get_pca_address()
            servo_frequency = self._config_loader.get_servo_frequency()

            self._pca = PCA9685(i2c_address=pca_address)
            self._pca.set_pwm_frequency(int(servo_frequency))
            self.get_logger().info(f"PCA9685 initialized at 0x{pca_address:02X} with {int(servo_frequency)}Hz")
        except Exception as e:
            self.get_logger().error(f"Failed to initialize PCA9685: {e}")
            self._pca = None
            return

        # Servo instances dictionary (servo_id -> servo instance)
        self._servos = {}

        # Create subscription to servo commands
        self._subscription = self.create_subscription(
            ServoCommand,
            'servo_command',
            self._command_callback,
            10
        )

        self.get_logger().info("Servo node initialized with configuration")

    def _command_callback(self, msg):
        """
        Handle incoming servo commands.

        Args:
            msg (ServoCommand): Command message containing servo_id and angle
        """
        if not self._pca or not self._config_loader:
            self.get_logger().error("PCA9685 or configuration not available")
            return

        servo_id = msg.servo_id
        angle = float(msg.angle)

        self.get_logger().info(f"Received servo command: id={servo_id}, angle={angle}")

        try:
            # Validate servo ID is configured
            if not self._config_loader.validate_servo_id(servo_id):
                self.get_logger().warning(f"Ignoring command for unknown servo ID: {servo_id}")
                return

            # Get servo configuration
            servo_config = self._config_loader.get_servo_config(servo_id)
            if not servo_config:
                self.get_logger().error(f"No configuration found for servo ID: {servo_id}")
                return

            # Create servo instance if not exists
            if servo_id not in self._servos:
                if servo_config['type'] == 'continuous':
                    self._servos[servo_id] = ContinuousServo.from_config(
                        self._pca, servo_id, servo_config['config']
                    )
                elif servo_config['type'] == 'positional':
                    self._servos[servo_id] = Servo.from_config(
                        self._pca, servo_id, servo_config['config']
                    )
                else:
                    self.get_logger().error(f"Unknown servo type for {servo_id}: {servo_config['type']}")
                    return

                self.get_logger().info(f"Created {servo_config['type']} servo instance for ID {servo_id}")

            # Control servo based on type
            servo = self._servos[servo_id]
            if servo_config['type'] == 'continuous':
                # Convert angle [0..180] to speed [-1.0..1.0]
                speed = (angle - 90.0) / 90.0
                servo.set_speed(speed)
                self.get_logger().info(f"Set continuous servo {servo_id} to speed {speed:.3f}")
            else:  # positional
                # Clamp angle to configured limits
                min_angle = servo_config['config']['min_angle']
                max_angle = servo_config['config']['max_angle']
                clamped_angle = max(min_angle, min(max_angle, angle))
                servo.set_angle(int(clamped_angle))
                self.get_logger().info(f"Set positional servo {servo_id} to angle {clamped_angle}")

        except Exception as e:
            self.get_logger().error(f"Error executing servo command: {e}")


    def destroy_node(self):
        """
        Cleanup when node is destroyed.
        """
        # Stop all servos
        for servo_id, servo in self._servos.items():
            if hasattr(servo, 'stop'):  # ContinuousServo has stop method
                servo.stop()

        # Stop all PWM signals
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