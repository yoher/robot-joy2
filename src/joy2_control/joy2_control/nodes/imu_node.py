"""
ROS2 IMU sensor node for BNO080.

This node provides a ROS2 interface to the BNO080 IMU sensor,
publishing sensor_msgs/Imu messages compatible with ros2_control
IMU Sensor Broadcaster.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Imu, MagneticField
from std_msgs.msg import Header
import time

from joy2_control.hardware.bno080 import BNO080, IMUData
from joy2_control.config.imu_config_loader import IMUConfigLoader


class IMUNode(Node):
    """
    ROS2 node for BNO080 IMU sensor.
    
    Publishes sensor_msgs/Imu messages at configured rate,
    compatible with ros2_control IMU Sensor Broadcaster.
    """
    
    def __init__(self):
        super().__init__('imu_node')
        
        # Declare configuration file parameter
        self.declare_parameter('config_file', 'src/joy2/config/imu_config.yaml')
        
        # Get configuration file path
        config_file = self.get_parameter('config_file').value
        
        # Load configuration
        try:
            self.config_loader = IMUConfigLoader(config_file)
            self.get_logger().info(f"Loaded IMU configuration from {config_file}")
        except Exception as e:
            self.get_logger().error(f"Failed to load IMU configuration: {e}")
            raise
        
        # Get configuration values
        i2c_address = self.config_loader.get_i2c_address()
        i2c_bus = self.config_loader.get_i2c_bus()
        debug = self.config_loader.is_debug_enabled()
        self.frame_id = self.config_loader.get_frame_id()
        self.update_rate = self.config_loader.get_update_rate()
        self.timeout_ms = self.config_loader.get_timeout_ms()
        
        # Covariance matrices
        self.base_orientation_cov = self.config_loader.get_orientation_covariance()
        self.base_angular_vel_cov = self.config_loader.get_angular_velocity_covariance()
        self.base_linear_accel_cov = self.config_loader.get_linear_acceleration_covariance()
        self.covariance_scale = self.config_loader.get_covariance_scale()
        
        # Initialize BNO080 driver
        try:
            self.bno = BNO080(i2c_address=i2c_address, i2c_bus=i2c_bus, debug=debug)
            self.get_logger().info(f"Initialized BNO080 at I2C address 0x{i2c_address:02X}")
        except Exception as e:
            self.get_logger().error(f"Failed to initialize BNO080: {e}")
            raise
        
        # Initialize sensor
        if not self.bno.initialize():
            self.get_logger().error("Failed to initialize BNO080 sensor")
            raise RuntimeError("BNO080 initialization failed")
        
        # Log product ID
        product_id = self.bno.product_id
        self.get_logger().info(
            f"BNO080 Product ID: SW v{product_id.get('sw_major', 0)}."
            f"{product_id.get('sw_minor', 0)}.{product_id.get('sw_version_patch', 0)}"
        )
        
        # Configure sensor based on mode
        sensor_mode = self.config_loader.get_sensor_mode()
        use_magnetometer = self.config_loader.use_magnetometer()
        
        if not self.bno.enable_rotation_vector(self.update_rate, use_magnetometer):
            self.get_logger().error("Failed to enable rotation vector")
            raise RuntimeError("Failed to enable rotation vector")
        
        self.get_logger().info(
            f"Enabled {sensor_mode} mode at {self.update_rate} Hz "
            f"(magnetometer: {use_magnetometer})"
        )
        
        # Enable additional sensors for complete IMU data
        if not self.bno.enable_gyroscope(self.update_rate):
            self.get_logger().warn("Failed to enable gyroscope")
        
        if not self.bno.enable_linear_acceleration(self.update_rate):
            self.get_logger().warn("Failed to enable linear acceleration")
        
        # Configure calibration
        calib_config = self.config_loader.get_calibration_config()
        if calib_config['auto_calibrate']:
            if not self.bno.calibrate(
                accel=calib_config['accel_calibration'],
                gyro=calib_config['gyro_calibration'],
                mag=calib_config['mag_calibration']
            ):
                self.get_logger().warn("Failed to configure calibration")
            else:
                self.get_logger().info(
                    f"Calibration enabled: accel={calib_config['accel_calibration']}, "
                    f"gyro={calib_config['gyro_calibration']}, "
                    f"mag={calib_config['mag_calibration']}"
                )
        
        # Create QoS profile for sensor data
        # Use reliable communication for control systems
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # Create IMU data publisher
        self.imu_publisher = self.create_publisher(Imu, 'imu/data', qos)
        self.get_logger().info("Created IMU publisher on topic 'imu/data'")
        
        # Optional publishers
        self.mag_publisher = None
        if self.config_loader.should_publish_mag() and use_magnetometer:
            self.mag_publisher = self.create_publisher(
                MagneticField, 'imu/mag', qos
            )
            self.get_logger().info("Created magnetometer publisher on topic 'imu/mag'")
        
        # Create timer for reading and publishing IMU data
        # Use a slightly higher rate than sensor update to avoid missing data
        timer_period = 1.0 / (self.update_rate * 1.2)
        self.timer = self.create_timer(timer_period, self.timer_callback)
        
        # Statistics
        self.message_count = 0
        self.last_accuracy_status = -1
        
        self.get_logger().info(
            f"IMU node initialized successfully - publishing at ~{self.update_rate} Hz"
        )
    
    def timer_callback(self):
        """
        Timer callback to read and publish IMU data.
        """
        try:
            # Read sensor data from BNO080
            imu_data = self.bno.read_sensor_data(timeout_ms=self.timeout_ms)
            
            if imu_data is None:
                # No new data available
                return
            
            # Create and publish IMU message
            imu_msg = self._create_imu_message(imu_data)
            self.imu_publisher.publish(imu_msg)
            
            # Update statistics
            self.message_count += 1
            
            # Log accuracy status changes
            accuracy_status = imu_data.status & 0x03
            if accuracy_status != self.last_accuracy_status:
                accuracy_str, _ = self.bno.get_accuracy()
                self.get_logger().info(f"IMU accuracy: {accuracy_str}")
                self.last_accuracy_status = accuracy_status
            
            # Log periodic statistics (every 100 messages)
            if self.message_count % 100 == 0:
                accuracy_str, _ = self.bno.get_accuracy()
                self.get_logger().info(
                    f"Published {self.message_count} IMU messages "
                    f"(accuracy: {accuracy_str})"
                )
        
        except Exception as e:
            self.get_logger().error(f"Error in timer callback: {e}")
    
    def _create_imu_message(self, imu_data: IMUData) -> Imu:
        """
        Create sensor_msgs/Imu message from BNO080 data.
        
        Args:
            imu_data: IMU data from BNO080
        
        Returns:
            Filled sensor_msgs/Imu message
        """
        msg = Imu()
        
        # Header with timestamp
        # Subtract the sensor delay to get accurate timestamp
        current_time = self.get_clock().now()
        delay_seconds = imu_data.delay_us / 1_000_000.0
        msg.header.stamp = (current_time.seconds_nanoseconds()[0] - delay_seconds, 
                           current_time.seconds_nanoseconds()[1])
        msg.header.stamp = current_time.to_msg()  # Use current time for now
        msg.header.frame_id = self.frame_id
        
        # Orientation (quaternion from rotation vector)
        msg.orientation.w = imu_data.quat_w
        msg.orientation.x = imu_data.quat_x
        msg.orientation.y = imu_data.quat_y
        msg.orientation.z = imu_data.quat_z
        
        # Angular velocity (rad/s from calibrated gyroscope)
        msg.angular_velocity.x = imu_data.gyro_x
        msg.angular_velocity.y = imu_data.gyro_y
        msg.angular_velocity.z = imu_data.gyro_z
        
        # Linear acceleration (m/s² with gravity removed)
        msg.linear_acceleration.x = imu_data.accel_x
        msg.linear_acceleration.y = imu_data.accel_y
        msg.linear_acceleration.z = imu_data.accel_z
        
        # Set covariance matrices based on accuracy
        accuracy_level = self._get_accuracy_level(imu_data.status & 0x03)
        scale = self.covariance_scale[accuracy_level]
        
        msg.orientation_covariance = [c * scale for c in self.base_orientation_cov]
        msg.angular_velocity_covariance = [c * scale for c in self.base_angular_vel_cov]
        msg.linear_acceleration_covariance = [c * scale for c in self.base_linear_accel_cov]
        
        return msg
    
    def _get_accuracy_level(self, status_code: int) -> str:
        """
        Convert BNO080 accuracy status code to string key.
        
        Args:
            status_code: Status bits 1:0 from BNO080
                        0=unreliable, 1=low, 2=medium, 3=high
        
        Returns:
            Accuracy level string for covariance scaling
        """
        accuracy_map = {
            0: 'unreliable',
            1: 'low',
            2: 'medium',
            3: 'high'
        }
        return accuracy_map.get(status_code, 'unreliable')
    
    def destroy_node(self):
        """
        Cleanup when node is destroyed.
        """
        self.get_logger().info("Shutting down IMU node...")
        
        # Close BNO080 connection
        if hasattr(self, 'bno'):
            self.bno.close()
        
        super().destroy_node()


def main(args=None):
    """
    Main function to run the IMU node.
    """
    rclpy.init(args=args)
    
    try:
        imu_node = IMUNode()
        rclpy.spin(imu_node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'imu_node' in locals():
            imu_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()