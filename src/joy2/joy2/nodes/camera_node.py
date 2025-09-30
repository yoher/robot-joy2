#!/usr/bin/env python3
"""
ROS2 Camera Node for Joy2 Robot.

Captures video from USB camera and publishes sensor_msgs/Image and sensor_msgs/CameraInfo.
Provides the foundation for teleoperation streaming and future VSLAM integration.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy
from sensor_msgs.msg import Image, CameraInfo, CompressedImage
from cv_bridge import CvBridge
import cv2
import numpy as np
from typing import Optional


class CameraNode(Node):
    """ROS2 camera node using OpenCV VideoCapture."""

    def __init__(self):
        super().__init__('camera_node')

        # Declare parameters with defaults
        self.declare_parameter('device_id', 0)
        self.declare_parameter('device_path', '/dev/video0')
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 30)
        self.declare_parameter('encoding', 'bgr8')
        self.declare_parameter('frame_id', 'camera_optical_frame')
        self.declare_parameter('camera_name', 'usb_camera')
        self.declare_parameter('publish_camera_info', True)
        self.declare_parameter('buffer_size', 1)

        # Get parameter values
        self.device_id = self.get_parameter('device_id').value
        self.device_path = self.get_parameter('device_path').value
        self.width = self.get_parameter('width').value
        self.height = self.get_parameter('height').value
        self.fps = self.get_parameter('fps').value
        self.encoding = self.get_parameter('encoding').value
        self.frame_id = self.get_parameter('frame_id').value
        self.camera_name = self.get_parameter('camera_name').value
        self.publish_camera_info = self.get_parameter('publish_camera_info').value

        # QoS profile for camera topics (best effort, volatile)
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            depth=self.get_parameter('buffer_size').value
        )

        # Publishers
        self.image_pub = self.create_publisher(
            Image, 'camera/image_raw', qos_profile
        )

        self.compressed_pub = self.create_publisher(
            CompressedImage, 'camera/image_raw/compressed', qos_profile
        )

        self.info_pub = None
        if self.publish_camera_info:
            self.info_pub = self.create_publisher(
                CameraInfo, 'camera/camera_info', qos_profile
            )

        # OpenCV bridge and camera
        self.bridge = CvBridge()
        self.cap = None
        self.timer = None

        # Initialize camera
        self._initialize_camera()

        # Log configuration
        self.get_logger().info(
            f'Camera node initialized: {self.width}x{self.height}@{self.fps}fps '
            f'(device: {self.device_path}, encoding: {self.encoding})'
        )

    def _initialize_camera(self):
        """Initialize camera capture."""
        try:
            # Try device path first with V4L2 backend, then device ID with V4L2 backend
            self.cap = cv2.VideoCapture(self.device_path, cv2.CAP_V4L2)
            if not self.cap.isOpened():
                self.get_logger().warning(
                    f'Failed to open camera at {self.device_path} with V4L2, '
                    f'trying device ID {self.device_id} with V4L2'
                )
                self.cap = cv2.VideoCapture(self.device_id, cv2.CAP_V4L2)

            if not self.cap.isOpened():
                raise RuntimeError(
                    f'Could not open camera {self.device_path} or device ID {self.device_id}'
                )

            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)

            # Verify settings were applied
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

            self.get_logger().info(
                f'Camera properties set: {actual_width}x{actual_height}@{actual_fps}fps'
            )

            # Create timer for publishing
            timer_period = 1.0 / self.fps
            self.timer = self.create_timer(timer_period, self._timer_callback)

        except Exception as e:
            self.get_logger().error(f'Failed to initialize camera: {e}')
            raise

    def _timer_callback(self):
        """Timer callback to capture and publish frames."""
        if self.cap is None or not self.cap.isOpened():
            self.get_logger().warning('Camera not available')
            return

        try:
            # Capture frame
            ret, frame = self.cap.read()
            if not ret:
                self.get_logger().warning('Failed to capture frame')
                return

            # Get current timestamp
            now = self.get_clock().now()

            # Convert to ROS Image message
            try:
                img_msg = self.bridge.cv2_to_imgmsg(frame, encoding=self.encoding)
                img_msg.header.stamp = now.to_msg()
                img_msg.header.frame_id = self.frame_id

                # Publish image
                self.image_pub.publish(img_msg)

                # Publish compressed image
                try:
                    compressed_msg = CompressedImage()
                    compressed_msg.header = img_msg.header
                    compressed_msg.format = "jpeg"

                    # Encode frame as JPEG
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]  # 80% quality
                    _, encoded_img = cv2.imencode('.jpg', frame, encode_param)
                    compressed_msg.data = encoded_img.tobytes()

                    self.compressed_pub.publish(compressed_msg)

                except Exception as e:
                    self.get_logger().error(f'Failed to publish compressed image: {e}')

            except Exception as e:
                self.get_logger().error(f'Failed to convert/publish image: {e}')
                return

            # Publish camera info if enabled
            if self.info_pub is not None:
                info_msg = CameraInfo()
                info_msg.header = img_msg.header
                info_msg.width = self.width
                info_msg.height = self.height
                info_msg.distortion_model = 'plumb_bob'  # Default model

                # Default camera matrices (identity for now)
                # These should be calibrated for accurate VSLAM
                info_msg.k = [1.0, 0.0, self.width/2.0,
                             0.0, 1.0, self.height/2.0,
                             0.0, 0.0, 1.0]  # Intrinsic matrix

                info_msg.r = [1.0, 0.0, 0.0,
                             0.0, 1.0, 0.0,
                             0.0, 0.0, 1.0]  # Rectification matrix

                info_msg.p = [1.0, 0.0, self.width/2.0, 0.0,
                             0.0, 1.0, self.height/2.0, 0.0,
                             0.0, 0.0, 1.0, 0.0]  # Projection matrix

                self.info_pub.publish(info_msg)

        except Exception as e:
            self.get_logger().error(f'Error in timer callback: {e}')

    def destroy_node(self):
        """Clean up resources."""
        if self.timer is not None:
            self.timer.cancel()

        if self.cap is not None:
            self.cap.release()

        super().destroy_node()


def main(args=None):
    """Main entry point."""
    rclpy.init(args=args)

    try:
        node = CameraNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'Error: {e}')
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()