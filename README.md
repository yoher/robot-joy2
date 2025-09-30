# ROS2 Mecanum Robot Workspace

A ROS2 workspace for controlling a mecanum-wheeled robot with comprehensive joystick teleoperation, servo control, camera streaming, and hardware interfaces.

## Workspace Overview

This workspace contains packages for building and controlling a mecanum-wheeled robot platform with ROS2 Jazzy.

```
ros1/                                    # Workspace root
├── src/
│   ├── joy2/                           # Main control package
│   │   ├── joy2/                       # Python package
│   │   │   ├── nodes/                  # ROS2 nodes
│   │   │   ├── control/                # Control algorithms
│   │   │   ├── hardware/               # Hardware drivers
│   │   │   └── config/                 # Config loaders
│   │   ├── config/                     # YAML configurations
│   │   ├── launch/                     # Launch files
│   │   ├── doc/                        # Documentation
│   │   └── README.md                   # Package documentation
│   │
│   └── joy2_interfaces/                # Custom message definitions
│       ├── msg/                        # Message definitions
│       │   ├── BuzzerCommand.msg
│       │   └── ServoCommand.msg
│       └── srv/                        # Service definitions
│
├── build/                              # Build artifacts
├── install/                            # Installed packages
├── log/                                # Build logs
└── README.md                           # This file
```

## Packages

### 1. joy2 Package

**Main robot control package** - Provides nodes for teleoperation, motor control, servo control, and peripheral management.

**Key Features:**
- 🎮 Joystick teleoperation with mode switching
- 🚗 Mecanum wheel motor control (decoupled architecture)
- 📹 Camera streaming with WebRTC teleoperation
- 🦾 Servo control (continuous and positional)
- 🔊 Buzzer control
- ⚡ Safety features (timeout-based auto-stop)
- 🔧 Configurable via YAML files

**Documentation:** See [`src/joy2/README.md`](src/joy2/README.md) for detailed setup, architecture, and usage instructions.

**Nodes:**
- `joy2_teleop` - Joystick input processing and message routing
- `mecanum_node` - Mecanum drive motor control (subscribes to `/cmd_vel`)
- `camera_node` - Camera capture and ROS2 image publishing
- `webrtc_node` - WebRTC video streaming for teleoperation
- `servo_node` - Servo position control
- `buzzer_node` - Buzzer activation control

### 2. joy2_interfaces Package

**Custom message and service definitions** used by the joy2 package.

**Messages:**
- `BuzzerCommand.msg` - Buzzer activation with frequency and duration
- `ServoCommand.msg` - Servo position commands with ID and angle

**Purpose:** Provides standardized interfaces for communication between nodes in the joy2 system.

## Quick Start

### Prerequisites

```bash
# Ensure ROS2 Jazzy is installed
# Ensure I2C is enabled on your platform

# Install dependencies
sudo apt install ros-jazzy-joy python3-smbus python3-dev i2c-tools
```

### Build Workspace

```bash
# Navigate to workspace
cd xxx

# Build all packages
colcon build

# Source the workspace
source install/setup.bash
```

### Launch Robot System

```bash
# Launch complete system (all nodes)
ros2 launch joy2 complete_system.launch.py
```

This starts:
- Joystick driver (`joy_node`)
- Teleoperation node (`joy2_teleop`)
- Motor controller (`mecanum_node`)
- Camera capture (`camera_node`)
- WebRTC streaming (`webrtc_node`)
- Servo controller (`servo_node`)
- Buzzer controller (`buzzer_node`)

## System Architecture

```
┌──────────────┐
│   Gamepad    │
│   (USB)      │
└──────┬───────┘
       │ Joy messages
       ▼
┌──────────────────────┐
│   joy2_teleop        │
│   (Input routing)    │
└──┬────────┬──────┬───┘
   │        │      │
   │        │      └────────────────┐
   │        │                       │
   │        │ ServoCommand          │ BuzzerCommand
   │        │ (joy2_interfaces)     │ (joy2_interfaces)
   │        │                       │
   │        ▼                       ▼
   │  ┌──────────┐           ┌──────────┐
   │  │servo_node│           │buzzer_node│
   │  └──────────┘           └──────────┘
   │
   │ TwistStamped
   │ /cmd_vel
   │
   ▼
┌──────────────┐    ┌──────────────┐
│ mecanum_node │    │  camera_node │
│ (Motors)     │    │  (USB Cam)   │
└──────────────┘    └──────┬───────┘
                           │ sensor_msgs/Image
                           │ /camera/image_raw
                           ▼
                    ┌──────────────┐
                    │ webrtc_node  │
                    │ (WebRTC)     │
                    │ Port 8080    │
                    └──────────────┘
```

## Hardware Support

- **Motors:** 4x DC motors with mecanum wheels (via PCA9685)
- **Camera:** USB camera (V4L2 compatible, e.g., Logitech C920)
- **Servos:** Continuous and positional servos (via PCA9685)
- **Peripherals:** Buzzer, I2C devices
- **Input:** USB gamepad/joystick
- **Platform:** Raspberry Pi or similar SBC

## Control Modes

### Wheel Control (Default)
- Right joystick: Forward/backward + strafe left/right
- Left joystick X: Rotation
- All movements can be combined for omnidirectional drive

### Servo Control (Hold R1)
- Left joystick: Continuous servos (c1, c2)
- Right joystick: Positional servos (p1, p2)
- Motors automatically stop in this mode

### Buzzer (Any Mode)
- Press B button: Trigger buzzer

## Configuration

Configuration files are located in `src/joy2/config/`:

- **`teleop_config.yaml`** - Joystick mappings, deadzones, button assignments
- **`mecanum_config.yaml`** - Motor control parameters, scales, safety settings
- **`camera_config.yaml`** - Camera hardware and streaming parameters
- **`servo_config.yaml`** - Servo channel mappings, pulse widths
- **`buzzer_config.yaml`** - Buzzer configuration

## Development

### Building Individual Packages

```bash
# Build only joy2_interfaces
colcon build --packages-select joy2_interfaces

# Build only joy2
colcon build --packages-select joy2

# Build with verbose output
colcon build --event-handlers console_direct+
```

### Testing

```bash
# Run tests
colcon test --packages-select joy2

# View test results
colcon test-result --verbose
```

### Adding Custom Messages

1. Define message in `src/joy2_interfaces/msg/YourMessage.msg`
2. Update `src/joy2_interfaces/CMakeLists.txt`
3. Rebuild: `colcon build --packages-select joy2_interfaces`
4. Source workspace and use in your nodes

## Monitoring and Debugging

```bash
# List all nodes
ros2 node list

# List all topics
ros2 topic list

# Monitor velocity commands
ros2 topic echo /cmd_vel

# Check node status
ros2 node info /mecanum_node

# View parameters
ros2 param list /mecanum_node

# Visualize node graph
rqt_graph
```

## Safety Features

- **Timeout Protection:** Motors auto-stop after 1 second without commands
- **Mode Isolation:** Motors stop when switching to servo mode
- **Graceful Shutdown:** All hardware stopped cleanly on node termination

## Documentation

- **Main Package:** [`src/joy2/README.md`](src/joy2/README.md) - Complete setup and usage guide
- **Architecture Plan:** [`src/joy2/doc/plan_mecanum_refactor.md`](src/joy2/doc/plan_mecanum_refactor.md) - Design decisions
- **Implementation:** [`src/joy2/doc/mecanum_refactor_summary.md`](src/joy2/doc/mecanum_refactor_summary.md) - Testing guide

## Troubleshooting

### Build Issues

```bash
# Clean build
rm -rf build/ install/ log/
colcon build
```

### I2C Issues

```bash
# Check I2C devices
i2cdetect -y 1

# Enable I2C (Raspberry Pi)
sudo raspi-config  # Interface Options → I2C
```

### Node Communication Issues

```bash
# Check topic connections
ros2 topic info /cmd_vel

# Monitor message flow
ros2 topic hz /cmd_vel

# Enable debug logging
ros2 run joy2 mecanum_node --ros-args --log-level debug
```

## Contributing

When making changes:

1. Update relevant documentation
2. Test all affected nodes
3. Update configuration files if needed
4. Run tests: `colcon test`

## License

Apache License 2.0

## Maintainer

Yoann Hervieux (yoann.hervieux@gmail.com)

## Version

- **joy2:** 1.1.0 (Camera streaming with WebRTC)
- **joy2_interfaces:** 0.0.0 (Development)
- **ROS2 Distribution:** Jazzy

## Additional Resources

- [ROS2 Jazzy Documentation](https://docs.ros.org/en/jazzy/)
- [ROS REP 103](https://www.ros.org/reps/rep-0103.html) - Standard Units and Coordinate Conventions
- [geometry_msgs Documentation](https://docs.ros2.org/latest/api/geometry_msgs/)

---

## Quick Command Reference

```bash
# Build workspace
colcon build
source install/setup.bash

# Launch system
ros2 launch joy2 complete_system.launch.py

# Monitor topics
ros2 topic list
ros2 topic echo /cmd_vel

# Adjust parameters
ros2 param set /mecanum_node translation_scale 0.8

# Stop all (Ctrl+C in launch terminal)
```

For detailed documentation, see [`src/joy2/README.md`](src/joy2/README.md).