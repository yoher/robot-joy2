# joy2 - ROS2 Mecanum Robot Control Package

A comprehensive ROS2 package for controlling a mecanum-wheeled robot with joystick teleoperation, servo control, and buzzer functionality.

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         ROS2 joy2 System                        │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  Gamepad     │
│  (Physical)  │
└──────┬───────┘
       │ USB
       ▼
┌──────────────┐       Joy messages
│  joy_node    ├───────────────────┐
│  (ROS pkg)   │                   │
└──────────────┘                   │
                                   ▼
                        ┌──────────────────────┐
                        │   joy2_teleop node   │
                        │  • Input processing  │
                        │  • Mode switching    │
                        │  • Message routing   │
                        └───┬────┬────┬────┬───┘
                            │    │    │    │
        ┌───────────────────┘    │    │    └───────────────────┐
        │ TwistStamped           │    │              BuzzerCmd │
        │ /cmd_vel               │    │ ServoCmd               │
        ▼                        │    │                        ▼
┌───────────────┐                │    │                ┌──────────────┐
│ mecanum_node  │                │    │                │ buzzer_node  │
│ • Subscribe   │                │    │                │              │
│   /cmd_vel    │                │    │                └──────┬───────┘
│ • Motor       │                │    │                       │
│   control     │                │    │                       ▼
│ • PCA9685     │                │    │                   [Buzzer]
│   (0x60)      │                │    │
└───────┬───────┘                │    │
        │                        │    │
        ▼                        │    ▼
    [Motors]                     │  ┌──────────────┐
    M1 M2                        │  │  servo_node  │
    M3 M4                        │  │              │
                                 │  └──────┬───────┘
                                 │         │
                                 │         ▼
                                 │     [Servos]
                                 │     p1 p2
                                 │     c1 c2
                                 │
                                 ▼
                          (Future nodes)
                          • camera_node
                          • web_bridge_node
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

- **Peripherals**
  - Buzzer connected to PCA9685
  - USB gamepad/joystick controller

- **Computing Platform**
  - Raspberry Pi or similar SBC
  - ROS2 Jazzy installed
  - I2C enabled

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

## Development

### Package Structure

```
joy2/
├── config/                      # Configuration files
│   ├── buzzer_config.yaml
│   ├── mecanum_config.yaml
│   ├── servo_config.yaml
│   └── teleop_config.yaml
├── doc/                         # Documentation
│   ├── plan_mecanum_refactor.md
│   └── mecanum_refactor_summary.md
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
│       ├── joy2_teleop.py
│       ├── mecanum_node.py
│       └── servo_node.py
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

- [Detailed Refactoring Plan](doc/plan_mecanum_refactor.md)
- [Implementation Summary](doc/mecanum_refactor_summary.md)
- [ROS REP 103](https://www.ros.org/reps/rep-0103.html) - Standard Units and Coordinate Conventions

## License

Apache License 2.0

## Maintainer

Yoann Hervieux (yoann.hervieux@gmail.com)

## Version

0.0.0 (Development)

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

### Node Reference

| Node | Package | Purpose |
|------|---------|---------|
| `joy_node` | `joy` | Gamepad driver |
| `joy2_teleop` | `joy2` | Input processing & routing |
| `mecanum_node` | `joy2` | Motor control |
| `servo_node` | `joy2` | Servo control |
| `buzzer_node` | `joy2` | Buzzer control |