# Changelog

All notable changes to the joy2 ROS2 package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-09-30

### Added

#### Core Architecture
- **Decoupled mecanum controller** - Created standalone `mecanum_node.py` as separate ROS2 node
- **Standard ROS2 interfaces** - Implemented `geometry_msgs/TwistStamped` on `/cmd_vel` topic
- **Safety features** - Added 1.0 second command timeout with automatic motor stop
- **Configuration system** - Comprehensive YAML-based parameter configuration

#### New Nodes
- `mecanum_node` - Standalone motor control node
  - Subscribes to `/cmd_vel` (TwistStamped)
  - Hardware initialization (PCA9685, DCMotorDriver)
  - Configurable parameters via ROS2 parameter system
  - Safety timeout protection
  - Graceful shutdown with motor stop

#### Configuration Files
- `config/mecanum_config.yaml` - Motor control parameters
  - Hardware settings (I2C address, PWM frequency)
  - Control scales (translation, rotation)
  - Safety timeout configuration
  - Performance tuning (eps parameter)

#### Documentation
- `README.md` - Workspace-level documentation
- `src/joy2/README.md` - Comprehensive package documentation with:
  - System architecture diagrams
  - Setup and installation instructions
  - Usage guide with control modes
  - Troubleshooting section
  - Quick reference commands
- `doc/plan_mecanum_refactor.md` - Architectural planning and design decisions
- `doc/mecanum_refactor_summary.md` - Implementation summary and testing guide

#### Launch Files
- Updated `complete_system.launch.py` to include mecanum_node with full parameter configuration

### Changed

#### joy2_teleop Node
- **Removed** direct motor hardware control
- **Removed** PCA9685 and DCMotorDriver initialization
- **Removed** MecanumDriveController instantiation
- **Added** TwistStamped publisher for `/cmd_vel` topic
- **Modified** `_control_wheels()` to publish velocity commands instead of direct motor control
- **Added** `_send_zero_velocity()` helper method for stopping robot
- **Simplified** cleanup in `destroy_node()`

#### setup.py
- Added `mecanum_node` entry point to console scripts

### Technical Details

#### Message Flow
```
joy_node → joy2_teleop → /cmd_vel (TwistStamped) → mecanum_node → Motors
```

#### Velocity Mapping
- Right joystick Y → `twist.linear.x` (forward/backward)
- Right joystick X → `twist.linear.y` (strafe left/right)
- Left joystick X → `twist.angular.z` (rotation)

#### Parameters (mecanum_node)
- `pca_address`: I2C address (default: 0x60)
- `motor_frequency`: PWM frequency (default: 50.0 Hz)
- `translation_scale`: Linear movement scale (default: 0.6)
- `rotation_scale`: Rotation scale (default: 0.6)
- `eps`: Change detection threshold (default: 0.02)
- `invert_omega`: Rotation direction inversion (default: false)
- `verbose`: Debug logging (default: false)
- `cmd_timeout`: Safety timeout (default: 1.0s)

### Benefits
- ✅ Separation of concerns (input processing vs motor control)
- ✅ Reusability (any node can publish to `/cmd_vel`)
- ✅ Testability (motor control independent from teleop)
- ✅ Standard ROS2 interface (TwistStamped)
- ✅ Safety (automatic timeout-based stop)
- ✅ Maintainability (cleaner code organization)

### Migration Guide

#### For Developers
No changes required for existing functionality. The system behaves identically to the previous version but with improved architecture.

#### Building
```bash
cd /home/yoann/dev/ros1
colcon build --packages-select joy2
source install/setup.bash
```

#### Running
```bash
# Launch complete system (unchanged)
ros2 launch joy2 complete_system.launch.py
```

### Known Issues
None at this time.

### Future Enhancements
- Odometry publishing for SLAM
- Diagnostics publishing
- Configurable acceleration limits
- Motor current monitoring
- Emergency stop service
- Camera calibration integration
- Multiple camera support

---

## [1.1.0] - 2025-09-30

### Added

#### Camera Streaming System
- **ROS2 camera node** - Created `camera_node.py` for video capture and publishing
- **WebRTC streaming node** - Created `webrtc_node.py` for low-latency video streaming
- **Standard ROS2 interfaces** - Implemented `sensor_msgs/Image` and `sensor_msgs/CameraInfo` topics
- **WebRTC teleoperation** - Built-in HTML interface with joystick controls

#### New Nodes
- `camera_node` - OpenCV-based camera capture and ROS2 publishing
  - Configurable resolution, FPS, and encoding
  - Publishes to `/camera/image_raw` and `/camera/camera_info`
  - Automatic fallback between device path and ID
  - QoS-optimized for real-time streaming

- `webrtc_node` - WebRTC streaming server
  - Subscribes to `/camera/image_raw/compressed`
  - Provides WebRTC peer connections on port 8080
  - Built-in HTML teleoperation interface
  - Automatic frame conversion for WebRTC

#### Configuration Files
- `config/camera_config.yaml` - Camera hardware and streaming parameters
  - Device configuration (path/ID, resolution, FPS)
  - ROS2 topic settings (frame_id, QoS)
  - Performance tuning options

#### Dependencies
- Added `python3-opencv`, `python3-aiortc`, `python3-aiohttp` to package.xml
- Integrated with ROS2 `cv_bridge` and `image_transport`

#### Launch Integration
- Updated `complete_system.launch.py` to include camera and WebRTC nodes
- Configurable parameters for all camera streaming components

### Changed

#### setup.py
- Added `camera_node` and `webrtc_node` entry points

#### package.xml
- Added camera and WebRTC dependencies
- Updated build and runtime dependencies

### Technical Details

#### Camera Pipeline
```
USB Camera → camera_node → /camera/image_raw (sensor_msgs/Image)
                      → /camera/camera_info (sensor_msgs/CameraInfo)
                      → image_transport → /camera/image_raw/compressed
                      → webrtc_node → WebRTC streams (port 8080)
```

#### WebRTC Architecture
- **Signaling**: HTTP endpoints (`/offer`, `/`) on port 8080
- **Streaming**: Standard WebRTC peer connections
- **Interface**: Built-in HTML page with video and controls
- **Compatibility**: Works with any WebRTC-compatible webapp

#### Parameters (camera_node)
- `device_id`: Camera device ID (default: 0)
- `device_path`: Camera device path (default: "/dev/video0")
- `width/height`: Resolution (default: 640x480)
- `fps`: Target frame rate (default: 30)
- `encoding`: Image encoding (default: "bgr8")
- `frame_id`: TF frame ID (default: "camera_optical_frame")
- `publish_camera_info`: Enable camera info publishing (default: true)

#### Parameters (webrtc_node)
- `port`: WebRTC server port (default: 8080)
- `host`: Server bind address (default: "0.0.0.0")
- `camera_topic`: ROS2 topic to subscribe to (default: "camera/image_raw/compressed")

### Benefits
- ✅ **Low-latency streaming** - WebRTC provides <100ms latency
- ✅ **Standard ROS2 topics** - Compatible with existing SLAM packages
- ✅ **WebRTC native** - Works with custom webapps using standard WebRTC APIs
- ✅ **Built-in interface** - Immediate teleoperation capability
- ✅ **VSLAM ready** - Standard Image+CameraInfo topics
- ✅ **Configurable** - Adjustable resolution, FPS, and quality

### Usage

#### Basic Camera Testing
```bash
# Test camera node
ros2 run joy2 camera_node

# Check topics
ros2 topic list | grep camera
ros2 topic hz /camera/image_raw
```

#### WebRTC Streaming
```bash
# Launch complete system with camera
ros2 launch joy2 complete_system.launch.py

# Access web interface
# Open browser to http://<raspberry_pi_ip>:8080/
```

#### Integration with Custom Webapp
```javascript
// Standard WebRTC connection
const pc = new RTCPeerConnection();
const offer = await pc.createOffer();
// Send to /offer endpoint, receive answer
// Video stream will be available in pc.ontrack
```

### Migration Guide

#### For v1.0.0 Users
Camera streaming is automatically included in the launch file. No changes required for basic operation.

#### For Custom Webapp Developers
The WebRTC node provides standard WebRTC streams. Replace any custom streaming code with standard WebRTC peer connections to `ws://<host>:8080/offer`.

### Known Issues
- WebRTC node requires `python3-aiortc` and `python3-aiohttp` system packages
- Camera initialization may show GStreamer warnings (normal)
- Frame rate may be limited by USB bandwidth

### Future Enhancements
- Camera calibration integration
- Multiple camera support
- H.264 hardware encoding
- RTSP server for alternative clients
- Recording capabilities

---

## [Unreleased]

### Planned for v1.2.0
- Camera calibration tools
- Odometry publishing
- Diagnostics and monitoring
- Advanced motor control features

---

**Version History:**
- **v1.1.0** (2025-09-30) - Camera streaming with WebRTC support
- **v1.0.0** (2025-09-30) - Initial ROS2 release with decoupled architecture