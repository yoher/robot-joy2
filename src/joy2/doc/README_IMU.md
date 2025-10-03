# BNO080 IMU Quick Start Guide

## Quick Start

### 1. Hardware Setup
Connect BNO080 to Raspberry Pi I2C:
- VDD → 3.3V
- GND → GND  
- SDA → GPIO 2 (Pin 3)
- SCL → GPIO 3 (Pin 5)

### 2. Verify Connection
```bash
i2cdetect -y 1
# Should show device at 0x4b
```

### 3. Launch IMU Node
```bash
# Standalone
ros2 launch joy2 imu_node.launch.py

# Or with complete system
ros2 launch joy2 complete_system.launch.py
```

### 4. Monitor IMU Data
```bash
# View messages
ros2 topic echo /imu/data

# Check rate
ros2 topic hz /imu/data
```

## Configuration

Edit [`config/imu_config.yaml`](../config/imu_config.yaml):

```yaml
sensor_mode: "game_rv"      # "game_rv" or "rotation_vector"
update_rate_hz: 30.0        # 10-400 Hz
frame_id: "imu_link"
```

## Calibration

### Gyroscope (Automatic)
Place robot still for 2-3 seconds

### Accelerometer (Automatic)  
Move to 4-6 orientations, hold each 1 second

### Magnetometer (Manual, rotation_vector mode only)
Rotate 180° on each axis (X, Y, Z)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Device not detected | Check wiring, enable I2C: `sudo raspi-config` |
| Node fails | Check I2C permissions: `sudo usermod -a -G i2c $USER` |
| Low accuracy | Perform calibration procedures |
| Drift | Use `game_rv` mode, enable gyro calibration |

## ros2_control Integration

Add to controller config:
```yaml
imu_sensor_broadcaster:
  type: imu_sensor_broadcaster/IMUSensorBroadcaster
  ros__parameters:
    sensor_name: bno080_imu
    frame_id: imu_link
```

## Files Created

- **Hardware**: `joy2/hardware/shtp.py`, `joy2/hardware/bno080.py`
- **Node**: `joy2/nodes/imu_node.py`
- **Config**: `config/imu_config.yaml`, `joy2/config/imu_config_loader.py`
- **Launch**: `launch/imu_node.launch.py`
- **Docs**: `doc/imu_integration.md` (detailed guide)

## Full Documentation

See [imu_integration.md](imu_integration.md) for complete documentation.

## Topics

- `/imu/data` - `sensor_msgs/Imu` - Complete IMU data with orientation, angular velocity, linear acceleration

## Support

Check logs with debug enabled:
```bash
# In config/imu_config.yaml set: debug: true
ros2 launch joy2 imu_node.launch.py
```

Reference: [BNO080 Datasheet](../../doc/BNO080_Datasheet_v1.3.pdf)