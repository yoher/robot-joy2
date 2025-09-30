# joy2 - ROS2 Mecanum Robot Control Package

A comprehensive ROS2 package for controlling a mecanum-wheeled robot with joystick teleoperation, servo control, and buzzer functionality.

## Architecture

### System Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                         ROS2 joy2 System v1.2.0                        │
└────────────────────────────────────────────────────────────────────────┘

┌──────────────┐                              ┌──────────────┐
│  Gamepad     │                              │ USB Camera   │
│  (Physical)  │                              │ (UVC)        │
└──────┬───────┘                              └──────┬───────┘
       │ USB                                         │ USB
       ▼                                             ▼
┌──────────────┐       Joy messages          ┌──────────────┐
│  joy_node    ├──────────────────┐          │ camera_node  │
│  (ROS pkg)   │                  │          │ • V4L2/MJPEG │
└──────────────┘                  │          │ • 640x480@30 │
                                  ▼          └──────┬───────┘
                       ┌──────────────────────┐     │
                       │   joy2_teleop node   │     │ Image topics
                       │  • Input processing  │     │
                       │  • Mode switching    │     ▼
                       │  • Message routing   │ ┌───────────────┐
                       └───┬────┬────┬────┬───┘ │ webrtc_node   │
                           │    │    │    │     │ • Low latency │
       ┌───────────────────┘    │    │    │     │ • Port 8080   │
       │ TwistStamped           │    │    │     └───────┬───────┘
       │ /cmd_vel               │    │    │             │
       ▼                        │    │    │             │ WebRTC
┌───────────────┐               │    │    │             ▼
│ mecanum_node  │               │    │    │     ┌───────────────┐
│ • Motors      │               │    │    │     │ Web Browser   │
│ • PCA9685     │               │    │    │     │ • Video       │
└───────┬───────┘               │    │    │     │ • Controls    │
        │                       │    │    │     └───────────────┘
        ▼                       │    │    │
    [Motors]                    │    │    └─────────┐
    M1 M2                       │    │              │
    M3 M4                       │    │              ▼
                                │    │      ┌──────────────┐
                                │    │      │ buzzer_node  │
                                │    │      └──────┬───────┘
                                │    │             │
                                │    │             ▼
                                │    │         [Buzzer]
                                │    │
                                │    ▼
                                │  ┌──────────────┐
                                │  │  servo_node  │
                                │  └──────┬───────┘
                                │         │
                                │         ▼
                                │     [Servos]
                                │     p1 p2
                                │     c1 c2
                                ▼
                         (Future nodes)
```

### Message Flow

```
User Input → joy_node → joy2_teleop → [/cmd_vel | /servo_command | /buzzer_command]
                                            ↓            ↓              ↓
                                      mecanum_node  servo_node    buzzer_node
                                            ↓            ↓              ↓
                                        [Motors]     [Servos]      [Buzzer]
```

### Control Modes

The system operates in two mutually exclusive modes:

1. **Wheel Control Mode** (default)
   - Right joystick: Forward/backward and strafe left/right
   - Left joystick X: Rotation
   - Publishes to `/cmd_vel` → received by `mecanum_node`

2. **Servo Control Mode** (hold R1 button)
   - Left joystick: Controls continuous servos (c1, c2)
   - Right joystick: Controls positional servos (p1, p2)
   - Publishes to `/servo_command` → received by `servo_node`
   - Motors automatically stop when entering this mode

## Hardware Requirements

- **Mecanum Robot Platform**
  - 4x DC motors with mecanum wheels
  - PCA9685 PWM driver (I2C address: 0x60)
  - Motor driver circuits

- **Servos** (optional)
  - 2x Continuous rotation servos (channels 8, 9)
  - 2x Positional servos (channels 10, 11)

- **Camera System** (v1.1.0+)
  - USB camera (UVC compatible, supports MJPEG recommended)
  - Tested: Logitech C270/C920, generic UVC cameras

- **Peripherals**
  - Buzzer connected to PCA9685
  - USB gamepad/joystick controller

- **Computing Platform**
  - Raspberry Pi 4/5 or similar SBC
  - ROS2 Jazzy installed
  - I2C enabled
  - Camera dependencies: python3-opencv, python3-aiortc, python3-aiohttp

## Camera and Video Streaming (v1.1.0+)

### Overview

The joy2 package includes a complete low-latency video streaming system for remote teleoperation:
- **camera_node** - Captures video from USB camera, publishes ROS2 Image topics
- **webrtc_node** - Provides WebRTC streaming with built-in web interface
- **Low-latency optimizations** - Hardware MJPEG encoding, minimal buffering, optimized transport

### Camera Setup

```bash
# List available cameras
v4l2-ctl --list-devices

# Check camera capabilities
v4l2-ctl --device=/dev/video0 --list-formats-ext

# Test camera
ros2 run joy2 camera_node
ros2 topic hz /camera/image_raw
ros2 topic hz /camera/image_raw/compressed
```

### WebRTC Streaming

```bash
# Launch complete system (includes camera and WebRTC)
ros2 launch joy2 complete_system.launch.py

# Access web interface from any device on the network
# Open browser to: http://<raspberry_pi_ip>:8080/
```

### Camera Configuration

Edit [`config/camera_config.yaml`](config/camera_config.yaml):

```yaml
camera_node:
  ros__parameters:
    device_path: "/dev/video0"     # Camera device
    width: 640                      # Resolution
    height: 480
    fps: 30                         # Frame rate
    encoding: "bgr8"                # ROS encoding
```

### Low-Latency Features (v1.2.0)

The system is optimized for minimal latency:
- **Hardware MJPEG encoding** - Camera encodes in hardware
- **Single-frame buffers** - No buffering throughout pipeline
- **V4L2 backend** - Direct camera access without GStreamer overhead
- **60% JPEG quality** - Balance between quality and speed
- **Monotonic timestamps** - Consistent timing without jitter
- **Frame age monitoring** - Tracks and logs latency sources

### Camera Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/camera/image_raw` | `sensor_msgs/Image` | Uncompressed BGR8 images |
| `/camera/image_raw/compressed` | `sensor_msgs/CompressedImage` | JPEG compressed images |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | Camera calibration data |

### WebRTC Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `http://<host>:8080/` | GET | Web interface with video player |
| `http://<host>:8080/offer` | POST | WebRTC signaling endpoint |

### Using Custom Web Applications

The WebRTC node provides standard WebRTC peer connections. Example JavaScript:

```javascript
// Create peer connection
const pc = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
});

// Request video from server
pc.addTransceiver('video', { direction: 'recvonly' });

// Handle incoming video
pc.ontrack = (event) => {
    if (event.track.kind === 'video') {
        videoElement.srcObject = event.streams[0];
    }
};

// Create and send offer
const offer = await pc.createOffer();
await pc.setLocalDescription(offer);

const response = await fetch('http://<robot-ip>:8080/offer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        sdp: offer.sdp,
        type: offer.type
    })
});

const answer = await response.json();
await pc.setRemoteDescription(answer);
```

### Performance Tuning

**For Lower Latency (at cost of quality):**
- Reduce resolution to 320x240 in camera_config.yaml
- Lower JPEG quality (edit camera_node.py, line 155)
- Ensure camera supports MJPEG hardware encoding

**For Better Quality (at cost of latency):**
- Increase resolution to 1280x720
- Increase JPEG quality to 80-90%
- Note: Higher resolutions may not maintain 30fps on some systems

### Latency Analysis

Current latency breakdown (~500ms total):
- Camera capture: ~5ms
- JPEG encoding: ~10ms (hardware MJPEG)
- ROS2 transport: <1ms
- JPEG decode: ~5ms
- VP8/H.264 encode: ~50-100ms (software on Raspberry Pi)
- WebRTC transport: ~20-50ms
- Browser decode/render: ~50-100ms
- Network latency: varies

**Major bottleneck**: Software VP8/H.264 encoding on Raspberry Pi. Future hardware H.264 encoding could reduce this to <10ms.

## Installation

### Prerequisites

```bash
# Install ROS2 Jazzy (if not already installed)
# Follow: https://docs.ros.org/en/jazzy/Installation.html

# Install dependencies
sudo apt install ros-jazzy-joy python3-smbus python3-dev i2c-tools
```

### Build Package

```bash
# Navigate to your ROS2 workspace
cd xxx

# Build the joy2 package
colcon build --packages-select joy2 joy2_interfaces

# Source the workspace
source install/setup.bash
```

### Hardware Setup

```bash
# Enable I2C on Raspberry Pi
sudo raspi-config
# Interface Options → I2C → Enable

# Verify I2C device
i2cdetect -y 1
# Should show device at address 0x60
```

## Configuration

### Main Configuration Files

1. **[`config/teleop_config.yaml`](config/teleop_config.yaml)**
   - Joystick button/axis mappings
   - Servo control settings
   - Deadzone configuration
   - Buzzer settings

2. **[`config/mecanum_config.yaml`](config/mecanum_config.yaml)**
   - Motor control parameters
   - Translation and rotation scales
   - Safety timeout settings
   - I2C configuration

3. **[`config/servo_config.yaml`](config/servo_config.yaml)**
   - Servo channel mappings
   - PWM pulse width ranges
   - Servo type configuration

### Key Parameters

#### Mecanum Controller
```yaml
mecanum_node:
  ros__parameters:
    pca_address: 0x60           # I2C address
    motor_frequency: 50.0       # PWM frequency (Hz)
    translation_scale: 0.6      # Movement speed (0.0-1.0)
    rotation_scale: 0.6         # Rotation speed (0.0-1.0)
    cmd_timeout: 1.0            # Safety timeout (seconds)
```

#### Teleop Controller
```yaml
teleop:
  ros__parameters:
    alt_button_index: 7         # R1 button for mode switching
    deadzone: 0.05              # Joystick deadzone
    wheel_deadzone: 0.05        # Motor control deadzone
```

## Launch Instructions

### Quick Start - Complete System

```bash
# Launch all nodes
ros2 launch joy2 complete_system.launch.py
```

This launches:
- `joy_node` - Gamepad input
- `joy2_teleop` - Teleoperation logic
- `mecanum_node` - Motor control
- `servo_node` - Servo control
- `buzzer_node` - Buzzer control
- `camera_node` - Video capture (v1.1.0+)
- `webrtc_node` - WebRTC streaming (v1.1.0+)

### Launch Individual Nodes

```bash
# Launch only motor control
ros2 run joy2 mecanum_node

# Launch only teleop
ros2 run joy2 joy2_teleop

# Launch joy node separately
ros2 run joy joy_node
```

### Custom Launch with Parameters

```bash
# Launch with custom translation scale
ros2 run joy2 mecanum_node --ros-args \
  -p translation_scale:=0.8 \
  -p rotation_scale:=0.8 \
  -p verbose:=true
```

## Usage

### Basic Operation

1. **Start the system**
   ```bash
   ros2 launch joy2 complete_system.launch.py
   ```

2. **Wheel Control Mode** (default)
   - Move **right joystick forward/back** → Robot moves forward/backward
   - Move **right joystick left/right** → Robot strafes left/right
   - Move **left joystick left/right** → Robot rotates
   - All movements can be combined for omnidirectional control

3. **Servo Control Mode**
   - **Hold R1 button** → Enable servo mode (motors stop)
   - **Left joystick** → Control continuous servos
   - **Right joystick** → Control positional servos
   - **Release R1** → Return to wheel control

4. **Buzzer**
   - Press **B button** → Trigger buzzer (works in any mode)

### Monitoring

```bash
# View all nodes
ros2 node list

# Monitor velocity commands
ros2 topic echo /cmd_vel

# Check motor node status
ros2 node info /mecanum_node

# View parameters
ros2 param list /mecanum_node
ros2 param get /mecanum_node translation_scale
```

### Adjusting Parameters at Runtime

```bash
# Increase motor speed
ros2 param set /mecanum_node translation_scale 0.8

# Change rotation speed
ros2 param set /mecanum_node rotation_scale 0.7

# Adjust safety timeout
ros2 param set /mecanum_node cmd_timeout 2.0

# Enable debug output
ros2 param set /mecanum_node verbose true
```

## Safety Features

### Automatic Motor Stop
- **Timeout Protection**: Motors automatically stop if no commands received for 1.0 second (configurable)
- **Mode Switching**: Motors stop when entering servo control mode
- **Graceful Shutdown**: All motors stopped when nodes are terminated

### Emergency Stop
```bash
# Press Ctrl+C in terminal running the launch file
# Or manually stop motors:
ros2 topic pub /cmd_vel geometry_msgs/msg/TwistStamped \
"{twist: {linear: {x: 0.0, y: 0.0}, angular: {z: 0.0}}}"
```

## Troubleshooting

### Motors Don't Respond

**Check node status:**
```bash
ros2 node list  # Verify mecanum_node is running
ros2 topic info /cmd_vel  # Check publishers/subscribers
```

**Verify I2C connection:**
```bash
i2cdetect -y 1  # Should show device at 0x60
```

**Check logs:**
```bash
ros2 run joy2 mecanum_node --ros-args --log-level debug
```

### Joystick Not Detected

```bash
# List joystick devices
ls /dev/input/js*

# Test joystick
jstest /dev/input/js0

# Verify joy_node
ros2 run joy joy_node --ros-args --log-level debug
```

### Wrong Rotation Direction

```bash
# Invert rotation
ros2 param set /mecanum_node invert_omega true

# Or edit mecanum_config.yaml and rebuild
```

### Motors Too Fast/Slow

```bash
# Adjust translation scale (0.0 to 1.0)
ros2 param set /mecanum_node translation_scale 0.5

# Adjust rotation scale
ros2 param set /mecanum_node rotation_scale 0.4
```

### Camera Not Working (v1.1.0+)

**Check camera device:**
```bash
# List cameras
v4l2-ctl --list-devices

# Verify device exists
ls -l /dev/video0

# Test camera directly
ros2 run joy2 camera_node --ros-args --log-level debug
```

**Check topics:**
```bash
# Verify publishing
ros2 topic hz /camera/image_raw/compressed

# Check frame rate
ros2 topic bw /camera/image_raw/compressed
```

### WebRTC Not Connecting (v1.1.0+)

**Verify server is running:**
```bash
# Check if port 8080 is listening
ss -tlnp | grep 8080

# Test HTTP endpoint
curl http://localhost:8080/

# Check WebRTC node logs
ros2 run joy2 webrtc_node --ros-args --log-level debug
```

**Check browser console** for JavaScript errors

**Firewall issues:**
```bash
# On robot, allow port 8080
sudo ufw allow 8080/tcp
```

### High Video Latency (v1.2.0+)

**Check frame age:**
```bash
ros2 run joy2 webrtc_node --ros-args --log-level debug
# Look for "Frame X: age=XXms" messages
```

**Reduce latency:**
```yaml
# Edit camera_config.yaml
width: 320
height: 240
```

**Check CPU usage:**
```bash
htop
# webrtc_node using >50%? Consider lower resolution
```

## Development

### Package Structure

```
joy2/
├── config/                      # Configuration files
│   ├── buzzer_config.yaml
│   ├── camera_config.yaml       # Camera parameters (v1.1.0+)
│   ├── mecanum_config.yaml
│   ├── servo_config.yaml
│   └── teleop_config.yaml
├── doc/                         # Documentation
│   ├── CHANGELOG.md
│   ├── plan_camera_streaming.md
│   ├── plan_mecanum_refactor.md
│   ├── mecanum_refactor_summary.md
│   └── video_streaming_implementation.md  # v1.2.0
├── joy2/                        # Python package
│   ├── config/                  # Config loaders
│   ├── control/                 # Control algorithms
│   │   └── mecanum_controller.py
│   ├── hardware/                # Hardware drivers
│   │   ├── buzzer.py
│   │   ├── motor.py
│   │   ├── pca9685.py
│   │   └── servo.py
│   └── nodes/                   # ROS2 nodes
│       ├── buzzer_node.py
│       ├── camera_node.py       # Camera capture (v1.1.0+)
│       ├── joy2_teleop.py
│       ├── mecanum_node.py
│       ├── servo_node.py
│       └── webrtc_node.py       # WebRTC streaming (v1.1.0+)
├── launch/                      # Launch files
│   ├── complete_system.launch.py
│   ├── joy_node.launch.py
│   └── servo_node.launch.py
├── test/                        # Tests
├── package.xml                  # Package metadata
├── setup.py                     # Python setup
└── README.md                    # This file
```

### Custom Nodes

To create a custom velocity control node:

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped

class CustomController(Node):
    def __init__(self):
        super().__init__('custom_controller')
        self.publisher = self.create_publisher(TwistStamped, 'cmd_vel', 10)
        
    def send_velocity(self, vx, vy, omega):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist.linear.x = vx
        msg.twist.linear.y = vy
        msg.twist.angular.z = omega
        self.publisher.publish(msg)
```

### Running Tests

```bash
# Run all tests
colcon test --packages-select joy2

# Run specific test
python3 src/joy2/test_wheel_control.py
```

## Related Packages

- **joy2_interfaces** - Custom message definitions
- **joy** - Standard ROS2 joystick driver

## Documentation

- [CHANGELOG](doc/CHANGELOG.md) - Version history and release notes
- [Video Streaming Implementation](doc/video_streaming_implementation.md) - Low-latency streaming details (v1.2.0)
- [Camera Streaming Plan](doc/plan_camera_streaming.md) - Original design document
- [Mecanum Refactoring Plan](doc/plan_mecanum_refactor.md) - Architecture design
- [Implementation Summary](doc/mecanum_refactor_summary.md) - Refactoring details
- [ROS REP 103](https://www.ros.org/reps/rep-0103.html) - Standard Units and Coordinate Conventions

## License

Apache License 2.0

## Maintainer

Yoann Hervieux (yoann.hervieux@gmail.com)

## Version

1.2.0 - Low-Latency Video Streaming

---

## Quick Reference

### Common Commands

```bash
# Launch complete system
ros2 launch joy2 complete_system.launch.py

# Monitor velocity commands
ros2 topic echo /cmd_vel

# Stop all motors
ros2 topic pub /cmd_vel geometry_msgs/msg/TwistStamped \
"{twist: {linear: {x: 0.0}, angular: {z: 0.0}}}"

# Change motor speed
ros2 param set /mecanum_node translation_scale 0.7

# View node graph
rqt_graph

# Check I2C
i2cdetect -y 1
```

### Topic Reference

| Topic | Type | Description |
|-------|------|-------------|
| `/joy` | `sensor_msgs/Joy` | Raw joystick input |
| `/cmd_vel` | `geometry_msgs/TwistStamped` | Velocity commands for motors |
| `/servo_command` | `joy2_interfaces/ServoCommand` | Servo position commands |
| `/buzzer_command` | `joy2_interfaces/BuzzerCommand` | Buzzer activation |
| `/camera/image_raw` | `sensor_msgs/Image` | Uncompressed camera images (v1.1.0+) |
| `/camera/image_raw/compressed` | `sensor_msgs/CompressedImage` | JPEG compressed images (v1.1.0+) |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | Camera calibration data (v1.1.0+) |

### Node Reference

| Node | Package | Purpose |
|------|---------|---------|
| `joy_node` | `joy` | Gamepad driver |
| `joy2_teleop` | `joy2` | Input processing & routing |
| `mecanum_node` | `joy2` | Motor control |
| `servo_node` | `joy2` | Servo control |
| `buzzer_node` | `joy2` | Buzzer control |
| `camera_node` | `joy2` | Camera capture & publishing (v1.1.0+) |
| `webrtc_node` | `joy2` | WebRTC video streaming (v1.1.0+) |