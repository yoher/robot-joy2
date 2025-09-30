# Mecanum Controller Refactoring Plan

**Date**: 2025-09-30  
**Status**: Planning Complete, Ready for Implementation  
**Goal**: Decouple mecanum controller from teleop node into a standalone ROS2 node

---

## Current Architecture (Before Refactoring)

```
┌─────────────┐
│  joy_node   │
└──────┬──────┘
       │ Joy
       ▼
┌─────────────────────────────────────────┐
│         joy2_teleop Node                │
│  ┌────────────────────────────────┐    │
│  │  - Joystick input processing   │    │
│  │  - Servo command publishing    │    │
│  │  - Buzzer command publishing   │    │
│  │  - Direct motor control        │◄───┼── TIGHTLY COUPLED
│  │  - PCA9685 initialization      │    │
│  │  - MecanumDriveController      │    │
│  └────────────────────────────────┘    │
└─────────┬───────────┬────────────┬─────┘
          │           │            │
          ▼           ▼            ▼
    ┌─────────┐ ┌──────────┐ ┌──────────┐
    │ Motors  │ │  Servos  │ │  Buzzer  │
    └─────────┘ └──────────┘ └──────────┘
```

**Problems:**
- Teleop node has multiple responsibilities
- Cannot control motors from other sources
- Difficult to test motor control independently
- Hardware initialization duplicated

---

## Target Architecture (After Refactoring)

```
                    ┌─────────────┐
                    │  joy_node   │
                    └──────┬──────┘
                           │ Joy
                           ▼
          ┌────────────────────────────────┐
          │      joy2_teleop Node          │
          │  - Joystick input processing   │
          │  - Velocity command publishing │
          │  - Servo command publishing    │
          │  - Buzzer command publishing   │
          └──┬────────────┬─────────────┬──┘
             │            │             │
             │TwistStamped│ServoCommand │BuzzerCommand
             │/cmd_vel    │             │
             ▼            ▼             ▼
     ┌──────────────┐ ┌──────────┐ ┌──────────┐
     │mecanum_node  │ │servo_node│ │buzzer_node│
     │              │ └──────────┘ └──────────┘
     │ - Subscribe  │
     │   /cmd_vel   │
     │ - Motor      │
     │   control    │
     │ - PCA9685    │
     │   hardware   │
     └──────┬───────┘
            │
            ▼
      ┌──────────┐
      │  Motors  │
      │ (PCA9685)│
      └──────────┘
```

**Benefits:**
- ✅ Separation of concerns (teleop vs motor control)
- ✅ Reusable: any node can publish `/cmd_vel`
- ✅ Testable: motor control independent from input
- ✅ Standard ROS2 interface (TwistStamped)
- ✅ Safety: timeout-based auto-stop
- ✅ Flexible: can swap teleop without changing motor control

---

## Implementation Tasks

### Task 1: Create mecanum_node.py ✅ COMPLETED

**File**: `src/joy2/joy2/nodes/mecanum_node.py`

**Features:**
- Subscribe to `geometry_msgs/msg/TwistStamped` on `/cmd_vel` topic
- Initialize motor hardware (PCA9685, DCMotorDriver)
- Use existing `MecanumDriveController` class
- Configurable parameters via ROS2 parameter system
- Safety timeout: auto-stop if no commands for 1 second
- Proper cleanup on shutdown

**Parameters:**
- `pca_address`: I2C address (default: 0x60)
- `motor_frequency`: PWM frequency in Hz (default: 50.0)
- `translation_scale`: Translation movement scale (default: 0.6)
- `rotation_scale`: Rotation movement scale (default: 0.6)
- `eps`: Change detection threshold (default: 0.02)
- `invert_omega`: Invert rotation direction (default: False)
- `verbose`: Enable debug logging (default: False)
- `cmd_timeout`: Safety timeout in seconds (default: 1.0)

**Key Methods:**
- `__init__()`: Initialize hardware and parameters
- `_cmd_vel_callback()`: Process incoming velocity commands
- `_safety_timer_callback()`: Check for command timeout and stop motors
- `destroy_node()`: Cleanup motors on shutdown

---

### Task 2: Update joy2_teleop.py ✅ COMPLETED

**File**: `src/joy2/joy2/nodes/joy2_teleop.py`

**Changes:**

**REMOVED:**
- Motor hardware initialization (PCA9685, DCMotorDriver)
- MecanumDriveController instantiation
- Direct motor control in `_control_wheels()`
- Motor cleanup in `destroy_node()`

**ADDED:**
- Publisher for `TwistStamped` messages on `/cmd_vel`
- Message construction in `_control_wheels()`:
  ```python
  msg = TwistStamped()
  msg.header.stamp = self.get_clock().now().to_msg()
  msg.header.frame_id = 'base_link'
  msg.twist.linear.x = vx_scaled
  msg.twist.linear.y = vy_scaled
  msg.twist.angular.z = omega_scaled
  self._cmd_vel_publisher.publish(msg)
  ```

**Mapping:**
- Right joystick Y → linear.x (forward/backward)
- Right joystick X → linear.y (strafe left/right)
- Left joystick X → angular.z (rotation)

---

### Task 3: Create mecanum_config.yaml ✅ COMPLETED

**File**: `src/joy2/config/mecanum_config.yaml`

**Content:**
```yaml
mecanum_node:
  ros__parameters:
    # Hardware configuration
    pca_address: 0x60
    motor_frequency: 50.0
    
    # Control scaling
    translation_scale: 0.6
    rotation_scale: 0.6
    
    # Performance tuning
    eps: 0.02  # Change detection threshold (reduces I2C spam)
    
    # Kinematics
    invert_omega: false  # Set true if rotation direction is wrong
    
    # Safety
    cmd_timeout: 1.0  # Auto-stop after 1 second without commands
    
    # Debugging
    verbose: false  # Enable detailed motor command logging
```

**Parameter Descriptions:**

- **eps (epsilon)**: Change detection threshold to reduce I2C bus traffic
  - Only sends motor commands when speed changes by more than this value
  - Range: 0.0-1.0 (typically 0.01-0.05)
  - Smaller = more responsive but more I2C traffic
  - Larger = less responsive but less bus load

---

### Task 4: Update setup.py ✅ COMPLETED

**File**: `src/joy2/setup.py`

**Changes:**
```python
entry_points={
    'console_scripts': [
        'test_talker = joy2.test_talker:main',
        'test_listener = joy2.test_listener:main',
        'buzzer_node = joy2.nodes.buzzer_node:main',
        'servo_node = joy2.nodes.servo_node:main',
        'joy2_teleop = joy2.nodes.joy2_teleop:main',
        'mecanum_node = joy2.nodes.mecanum_node:main',  # NEW
    ],
},
```

---

### Task 5: Update complete_system.launch.py ✅ COMPLETED

**File**: `src/joy2/launch/complete_system.launch.py`

**Added:**
```python
# Mecanum drive control node
Node(
    package='joy2',
    executable='mecanum_node',
    name='mecanum_node',
    output='screen',
    parameters=[
        {'pca_address': 0x60},
        {'motor_frequency': 50.0},
        {'translation_scale': 0.6},
        {'rotation_scale': 0.6},
        {'eps': 0.02},
        {'invert_omega': False},
        {'verbose': False},
        {'cmd_timeout': 1.0}
    ],
),
```

---

## Message Flow

### TwistStamped Message Structure

```
Header header
  builtin_interfaces/Time stamp
  string frame_id = "base_link"
Twist twist
  Vector3 linear
    float64 x  # Forward/backward velocity
    float64 y  # Left/right strafe velocity
    float64 z  # (unused for mecanum)
  Vector3 angular
    float64 x  # (unused)
    float64 y  # (unused)
    float64 z  # Rotation (yaw) velocity
```

### Velocity to Motor Mapping (Mecanum Kinematics)

```python
# Input from TwistStamped
vx = msg.twist.linear.x      # Forward/backward
vy = msg.twist.linear.y      # Strafe left/right
omega = msg.twist.angular.z  # Rotation

# Motor mixing (after scaling)
FL (M1) = vx + vy + omega   # Front-Left
FR (M2) = vx - vy - omega   # Front-Right
RL (M3) = vx - vy + omega   # Rear-Left
RR (M4) = vx + vy - omega   # Rear-Right

# Normalization applied if any motor > 1.0
```

---

## Testing Plan

### 1. Unit Testing
- [ ] Test mecanum_node subscribes to `/cmd_vel`
- [ ] Test motor mixing calculations
- [ ] Test safety timeout functionality
- [ ] Test parameter loading

### 2. Integration Testing
- [ ] Test joy_node → joy2_teleop → mecanum_node pipeline
- [ ] Verify motors respond correctly to joystick input
- [ ] Test mode switching (servo vs wheel control)
- [ ] Test emergency stop on timeout

### 3. System Testing
- [ ] Launch complete system
- [ ] Verify all nodes start correctly
- [ ] Test full robot control flow
- [ ] Monitor I2C bus for proper communication

---

## Safety Features

### 1. Command Timeout
- Mecanum node monitors last command timestamp
- If no commands received for `cmd_timeout` seconds (default: 1.0s)
- Automatically stops all motors
- Prevents runaway robot if teleop crashes

### 2. Graceful Shutdown
- `destroy_node()` explicitly stops all motors
- Ensures motors don't continue running after node termination
- Calls `release_all()` on motor driver

### 3. Change Detection
- `eps` parameter prevents motor jitter
- Reduces I2C bus traffic
- Only sends commands when meaningful change occurs

---

## Troubleshooting

### Motors don't respond
1. Check if mecanum_node is running: `ros2 node list`
2. Verify topic connection: `ros2 topic info /cmd_vel`
3. Monitor messages: `ros2 topic echo /cmd_vel`
4. Check PCA9685 I2C address (should be 0x60)

### Motors stop unexpectedly
1. Check command timeout setting (default 1.0s)
2. Verify continuous message stream from teleop
3. Check for errors in mecanum_node logs

### Wrong rotation direction
1. Set `invert_omega: true` in mecanum_config.yaml
2. Or swap motor connections

### Motors move but wrong direction
1. Check motor wiring to PCA9685
2. Verify motor order (M1=FL, M2=FR, M3=RL, M4=RR)
3. Review mecanum mixing equations in MecanumDriveController

---

## Future Enhancements

- [ ] Add odometry publishing for SLAM
- [ ] Add diagnostics publishing (motor health, I2C status)
- [ ] Add configurable acceleration limits
- [ ] Add motor current monitoring
- [ ] Add emergency stop service
- [ ] Add velocity ramping for smooth acceleration

---

## References

- ROS REP 103: Standard Units and Coordinate Conventions
- geometry_msgs/TwistStamped documentation
- PCA9685 datasheet
- Mecanum wheel kinematics

---

**Last Updated**: 2025-09-30  
**Status**: Documentation Complete, Ready for Code Mode Implementation