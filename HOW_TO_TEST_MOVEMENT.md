# How to Test Robot Movement

## Simulation is Running ✅

The Gazebo simulation with GUI is currently running in the background.
You should see:
- Gazebo window with the robot on a ground plane
- RViz window showing the robot model

## Wait for Controllers to Load

Give it about 25-30 seconds after launch for all controllers to initialize.

## Check Controller Status

Open a **NEW terminal** and run:

```bash
cd ~/dev/yhx/robot-joy2
source install/setup.bash
ros2 control list_controllers
```

You should see:
```
joint_state_broadcaster[joint_state_broadcaster/JointStateBroadcaster] active
mecanum_controller[mecanum_drive_controller/MecanumDriveController] active
```

## Test Robot Movement

### 1. Forward Movement
```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --rate 10
```
**Expected**: Robot moves forward
**To stop**: Press `Ctrl+C`

### 2. Backward Movement
```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: -0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --rate 10
```

### 3. Sideways (Left)
```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.5, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --rate 10
```

### 4. Sideways (Right)
```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: -0.5, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --rate 10
```

### 5. Rotate (Counter-clockwise)
```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}" --rate 10
```

### 6. Diagonal Movement (Forward-Right)
```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5, y: -0.5, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --rate 10
```

### 7. Stop the Robot
```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{}" --once
```

## Monitor Joint States

In another terminal:
```bash
cd ~/dev/yhx/robot-joy2
source install/setup.bash
ros2 topic echo /joint_states
```

## Check Odometry

```bash
ros2 topic echo /odom
```

## Troubleshooting

### Controllers not loading
Check the log:
```bash
tail -100 /tmp/gazebo_sim.log | grep -E "(ERROR|controller|mecanum)"
```

### Robot not moving
1. Make sure controller is active: `ros2 control list_controllers`
2. Check cmd_vel topic: `ros2 topic info /cmd_vel`
3. Echo cmd_vel to verify commands: `ros2 topic echo /cmd_vel`

### To restart simulation
Kill the current one:
```bash
pkill -f "ros2 launch"
pkill -f "gz sim"
```

Then relaunch:
```bash
cd ~/dev/yhx/robot-joy2
source install/setup.bash
ros2 launch joy2_bringup gazebo_simulation.launch.py
```

## Success Indicators

✅ Gazebo GUI shows robot on ground plane  
✅ RViz shows robot model with all wheels  
✅ Controllers listed as "active"  
✅ Robot responds to `/cmd_vel` commands  
✅ Wheels rotate in Gazebo when commands sent  
✅ `/odom` topic publishes robot position  
✅ `/joint_states` topic shows wheel positions/velocities  

---

**Note**: The simulation is running in terminal ID: `254649c4-bc32-443c-86a4-e9f55e17a979`  
Log file: `/tmp/gazebo_sim.log`
