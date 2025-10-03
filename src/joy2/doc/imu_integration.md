# BNO080 IMU Integration Guide

## Overview

This document describes the integration of the BNO080 9-axis IMU sensor into the joy2 package. The BNO080 provides sensor fusion, combining data from its accelerometer, gyroscope, and magnetometer to produce accurate orientation data.

### Features

- **Sensor Fusion**: 9-axis (with magnetometer) or 6-axis (without magnetometer) orientation
- **High Update Rate**: Configurable up to 400Hz for rotation vectors, 1000Hz for gyro rotation vector
- **Automatic Calibration**: Dynamic calibration of accelerometer, gyroscope, and magnetometer
- **ros2_control Compatible**: Publishes `sensor_msgs/Imu` messages compatible with IMU Sensor Broadcaster
- **I2C Communication**: Uses I2C at address 0x4B (configurable to 0x4A)
- **SHTP Protocol**: Implements Hillcrest's Sensor Hub Transport Protocol

## Hardware Setup

### Requirements

- BNO080 IMU sensor module
- I2C connection to Raspberry Pi or compatible board
- Pull-up resistors on I2C lines (usually built into modules)

### Wiring

Connect the BNO080 to your Raspberry Pi:

```
BNO080          Raspberry Pi
------          ------------
VDD    ------>  3.3V (Pin 1)
GND    ------>  GND (Pin 6)
SDA    ------>  SDA (GPIO 2, Pin 3)
SCL    ------>  SCL (GPIO 3, Pin 5)
```

**I2C Address Configuration:**
- The BNO080 I2C address is determined by the SA0 pin
- SA0 = GND: Address 0x4A
- SA0 = VDD: Address 0x4B (default in our configuration)

### Verify I2C Connection

Before running the IMU node, verify the BNO080 is detected:

```bash
# Install i2c-tools if not already installed
sudo apt-get install i2c-tools

# Scan I2C bus 1
i2cdetect -y 1
```

You should see the device at address 0x4b (or 0x4a depending on SA0 pin):

```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
40: -- -- -- -- -- -- -- -- -- -- -- 4b -- -- -- -- 
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
70: -- -- -- -- -- -- -- --
```

## Configuration

### Configuration File

The IMU is configured via [`config/imu_config.yaml`](../config/imu_config.yaml). Key parameters:

```yaml
imu:
  ros__parameters:
    # I2C Configuration
    i2c_bus: 1              # I2C bus number
    i2c_address: 0x4B       # BNO080 I2C address
    
    # Sensor Mode
    sensor_mode: "game_rv"  # Options: "game_rv", "rotation_vector", "gyro_rv"
    
    # Update Rate
    update_rate_hz: 30.0    # 10-400Hz for RV, up to 1000Hz for gyro_rv
    
    # Frame ID for TF
    frame_id: "imu_link"
```

### Sensor Modes

1. **`game_rv`** (Game Rotation Vector - Default)
   - 6-axis fusion (accelerometer + gyroscope)
   - No magnetometer, so no absolute heading
   - More stable in environments with magnetic interference
   - Suitable for most robotic applications

2. **`rotation_vector`** (Full Rotation Vector)
   - 9-axis fusion (accelerometer + gyroscope + magnetometer)
   - Provides absolute heading relative to magnetic north
   - Requires calibration by rotating device
   - Best for navigation applications

3. **`gyro_rv`** (Gyro Rotation Vector)
   - High-speed mode up to 1000Hz
   - Optimized for VR/AR head tracking
   - Lower latency but may drift over time

### Calibration Configuration

```yaml
calibration:
  auto_calibrate: true      # Enable automatic calibration
  accel_calibration: true   # Calibrate accelerometer
  gyro_calibration: true    # Calibrate gyroscope
  mag_calibration: true     # Calibrate magnetometer (for rotation_vector mode)
```

## Usage

### Launch IMU Node Standalone

```bash
# Launch only the IMU node
ros2 launch joy2 imu_node.launch.py

# Or with custom config file
ros2 launch joy2 imu_node.launch.py config_file:=/path/to/custom_config.yaml
```

### Launch Complete System

The IMU node is included in the complete system launch file:

```bash
ros2 launch joy2 complete_system.launch.py
```

### Monitor IMU Data

```bash
# View IMU messages
ros2 topic echo /imu/data

# View IMU message rate
ros2 topic hz /imu/data

# View IMU topics
ros2 topic list | grep imu
```

### Visualize in RViz

```bash
# Launch RViz
rviz2

# Add -> By topic -> /imu/data -> Imu
# Set Fixed Frame to "imu_link" or your robot's base frame
```

## ROS2 Topics

### Published Topics

- **`/imu/data`** ([`sensor_msgs/Imu`](http://docs.ros.org/en/api/sensor_msgs/html/msg/Imu.html))
  - Complete IMU data with orientation, angular velocity, and linear acceleration
  - Compatible with ros2_control IMU Sensor Broadcaster

### Message Format

```
header:
  stamp: <timestamp>
  frame_id: "imu_link"
orientation:           # Quaternion from sensor fusion
  x: <float>
  y: <float>
  z: <float>
  w: <float>
orientation_covariance: [9 floats]  # Row-major 3x3 matrix
angular_velocity:      # rad/s from calibrated gyroscope
  x: <float>
  y: <float>
  z: <float>
angular_velocity_covariance: [9 floats]
linear_acceleration:   # m/s² with gravity removed
  x: <float>
  y: <float>
  z: <float>
linear_acceleration_covariance: [9 floats]
```

## ros2_control Integration

The IMU node is compatible with the ros2_control framework's IMU Sensor Broadcaster.

### Controller Configuration

Add to your robot's controller configuration:

```yaml
controller_manager:
  ros__parameters:
    update_rate: 100  # Hz
    
    # IMU sensor broadcaster
    imu_sensor_broadcaster:
      type: imu_sensor_broadcaster/IMUSensorBroadcaster

imu_sensor_broadcaster:
  ros__parameters:
    sensor_name: bno080_imu
    frame_id: imu_link
```

### URDF Integration

Add IMU link to your robot's URDF:

```xml
<link name="imu_link">
  <visual>
    <geometry>
      <box size="0.025 0.025 0.01"/>
    </geometry>
    <material name="blue"/>
  </visual>
</link>

<joint name="imu_joint" type="fixed">
  <parent link="base_link"/>
  <child link="imu_link"/>
  <origin xyz="0.0 0.0 0.05" rpy="0 0 0"/>
</joint>
```

### Launch with ros2_control

```bash
# Start the IMU node
ros2 launch joy2 imu_node.launch.py

# Load and start the IMU sensor broadcaster
ros2 control load_controller imu_sensor_broadcaster
ros2 control set_controller_state imu_sensor_broadcaster start
```

## Calibration Procedure

### Accelerometer Calibration (Automatic)

The accelerometer calibrates automatically by detecting when the sensor is stable.

**For best results:**
1. Place the robot on a level surface
2. Keep it stationary for 2-3 seconds
3. Move to 4-6 different orientations
4. Hold each orientation for about 1 second

### Gyroscope Calibration (Automatic)

The gyroscope calibrates its zero-rate offset when stationary.

**For best results:**
1. Place the robot on a stable surface
2. Keep completely still for 2-3 seconds
3. Calibration status will improve to "High"

### Magnetometer Calibration (Manual - for rotation_vector mode only)

If using `sensor_mode: "rotation_vector"`, calibrate the magnetometer:

1. Enable rotation_vector mode in config
2. Launch the IMU node
3. Perform the following movements:
   - **Roll**: Rotate 180° around X-axis and back
   - **Pitch**: Rotate 180° around Y-axis and back  
   - **Yaw**: Rotate 180° around Z-axis and back
4. Take about 2 seconds for each axis rotation
5. Monitor calibration status in node logs

### Checking Calibration Status

The IMU node logs calibration accuracy:

```
[INFO] [imu_node]: IMU accuracy: Low
[INFO] [imu_node]: IMU accuracy: Medium
[INFO] [imu_node]: IMU accuracy: High
```

Status levels:
- **Unreliable**: Sensor just started or significant disturbance
- **Low**: Initial calibration in progress
- **Medium**: Partially calibrated
- **High**: Fully calibrated (best accuracy)

## Troubleshooting

### IMU Not Detected

**Problem**: `i2cdetect` doesn't show device at 0x4B

**Solutions:**
1. Check wiring connections
2. Verify 3.3V power supply
3. Check I2C pull-up resistors (2.2kΩ-4.7kΩ)
4. Try different I2C address if SA0 pin is different
5. Enable I2C on Raspberry Pi:
   ```bash
   sudo raspi-config
   # Interface Options -> I2C -> Enable
   ```

### Node Fails to Initialize

**Problem**: IMU node exits with "Failed to initialize BNO080"

**Solutions:**
1. Check I2C permissions:
   ```bash
   sudo usermod -a -G i2c $USER
   # Log out and back in
   ```
2. Verify I2C bus number in config (usually 1 for Raspberry Pi)
3. Check if another process is using the I2C device
4. Try power cycling the BNO080

### Low or Unreliable Accuracy

**Problem**: Accuracy status remains "Low" or "Unreliable"

**Solutions:**
1. Perform calibration procedures (see above)
2. Keep robot stationary for gyroscope calibration
3. For magnetometer: move away from magnetic interference
4. Check for loose connections causing vibration
5. Increase update rate if too low

### High Latency or Low Update Rate

**Problem**: Messages published slower than expected

**Solutions:**
1. Check configured `update_rate_hz` in config file
2. Monitor I2C bus for errors: `dmesg | grep i2c`
3. Reduce I2C traffic from other devices
4. Check system CPU load

### Drift in Orientation

**Problem**: Orientation drifts over time

**Solutions:**
1. Use `game_rv` mode to avoid magnetometer drift
2. Enable gyroscope calibration
3. Keep robot still periodically for recalibration
4. Check for temperature variations
5. Consider using `rotation_vector` mode with good mag calibration

### Magnetic Interference

**Problem**: Heading jumps or is inaccurate (rotation_vector mode)

**Solutions:**
1. Switch to `game_rv` mode (no magnetometer)
2. Move IMU away from motors, batteries, magnets
3. Recalibrate magnetometer after moving IMU
4. Add magnetic shielding if necessary

## Architecture

### Component Structure

```
joy2/
├── hardware/
│   ├── shtp.py          # SHTP protocol implementation
│   ├── bno080.py        # BNO080 driver
│   └── __init__.py
├── nodes/
│   ├── imu_node.py      # ROS2 IMU publisher node
│   └── __init__.py
├── config/
│   ├── imu_config.yaml          # IMU configuration
│   └── imu_config_loader.py     # Configuration loader
└── launch/
    └── imu_node.launch.py       # Launch file
```

### Communication Flow

```
IMU Node
   ↓
BNO080 Driver
   ↓
SHTP Protocol Handler
   ↓
I2C Bus (smbus2)
   ↓
BNO080 Hardware
```

### Data Flow

```
BNO080 Sensor Fusion
   ↓
Quaternion + Gyro + Accel
   ↓
SHTP Packet
   ↓
IMU Node Processing
   ↓
sensor_msgs/Imu Message
   ↓
ROS2 Topic (/imu/data)
   ↓
ros2_control IMU Broadcaster (optional)
```

## Performance Characteristics

### Update Rates
- **Rotation Vector**: 10-400 Hz
- **Game Rotation Vector**: 10-400 Hz
- **Gyro Rotation Vector**: 10-1000 Hz (for VR/AR)

### Accuracy (from BNO080 datasheet)
- **Rotation Vector**: ±3.5° dynamic, ±2.0° static
- **Game Rotation Vector**: ±2.5° dynamic, ±1.5° static
- **Gyroscope**: ±3.1°/s dynamic accuracy
- **Accelerometer**: ±0.3 m/s² dynamic accuracy

### Latency
- **Typical**: 3-7ms at 100-200 Hz
- **High-speed mode**: <4ms at 1000 Hz

## Testing

### Unit Tests

Test SHTP protocol and BNO080 driver:

```bash
# Run unit tests (to be implemented)
python3 -m pytest src/joy2/test/test_bno080.py
```

### Integration Test

Test complete IMU node:

```bash
# Launch node
ros2 launch joy2 imu_node.launch.py

# In another terminal, check data
ros2 topic echo /imu/data --once

# Check message rate
ros2 topic hz /imu/data

# Should see: "average rate: ~30.000" (or your configured rate)
```

### Verify Orientation

Test orientation accuracy:

```bash
# Terminal 1: Launch IMU
ros2 launch joy2 imu_node.launch.py

# Terminal 2: Monitor orientation
ros2 topic echo /imu/data/orientation

# Physically rotate the robot and verify quaternion changes correctly
```

## API Reference

### BNO080 Driver

See [`joy2/hardware/bno080.py`](../joy2/hardware/bno080.py) for complete API.

**Key Methods:**
- `initialize()`: Initialize sensor
- `enable_rotation_vector(rate_hz, use_magnetometer)`: Enable rotation vector output
- `read_sensor_data(timeout_ms)`: Read IMU data
- `calibrate(accel, gyro, mag)`: Configure calibration
- `get_accuracy()`: Get current accuracy status

### IMU Node

See [`joy2/nodes/imu_node.py`](../joy2/nodes/imu_node.py) for implementation.

**Published Topics:**
- `/imu/data` - Complete IMU data

**Parameters:**
- `config_file` - Path to configuration YAML file

## References

1. [BNO080 Datasheet](../doc/BNO080_Datasheet_v1.3.pdf)
2. [sensor_msgs/Imu Message](http://docs.ros.org/en/api/sensor_msgs/html/msg/Imu.html)
3. [ros2_control IMU Sensor Broadcaster](https://control.ros.org/master/doc/ros2_controllers/imu_sensor_broadcaster/doc/userdoc.html)
4. [I2C on Raspberry Pi](https://www.raspberrypi.com/documentation/computers/os.html#i2c)

## Support

For issues or questions:
1. Check this documentation
2. Review the [BNO080 datasheet](../doc/BNO080_Datasheet_v1.3.pdf)
3. Check ROS logs: `ros2 launch joy2 imu_node.launch.py`
4. Enable debug mode in `imu_config.yaml`: `debug: true`

## License

Apache License 2.0 - See package LICENSE file.