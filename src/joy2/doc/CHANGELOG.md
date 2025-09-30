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
- Camera streaming (WebRTC and RTSP) - planned for v1.1.0
- Odometry publishing for SLAM
- Diagnostics publishing
- Configurable acceleration limits
- Motor current monitoring
- Emergency stop service

---

## [Unreleased]

### Planned for v1.1.0
- Camera streaming node with WebRTC support
- RTSP server for SLAM applications
- Web interface integration

---

**Version History:**
- **v1.0.0** (2025-09-30) - Initial ROS2 release with decoupled architecture