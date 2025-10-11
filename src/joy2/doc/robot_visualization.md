# Robot Visualization in RViz

This document explains how to visualize your Joy2 robot in RViz.

## Prerequisites

Make sure you have the required ROS2 packages installed:

```bash
sudo apt update
sudo apt install ros-jazzy-rviz2 ros-jazzy-joint-state-publisher-gui ros-jazzy-robot-state-publisher
```

## Launching Robot Visualization

To visualize your robot in RViz, run the visualization launch file:

```bash
ros2 launch joy2 robot_visualization.launch.py
```

## What You'll See

The launch file will start:

1. **Robot State Publisher** - Publishes your robot's URDF description and transforms
2. **Joint State Publisher GUI** - Interactive GUI to control joint positions (for testing)
3. **RViz** - 3D visualization of your robot
4. **Static Transform Publisher** - Provides odom → base_link transform

## RViz Displays

The default RViz configuration includes:

- **Grid** - Reference grid on the ground plane
- **RobotModel** - 3D model of your mecanum wheeled robot
- **TF** - Transform tree visualization showing coordinate frames
- **Odometry** - (Disabled by default) Can show robot movement if odometry is published

## Robot Features Visualized

Your Joy2 robot model includes:

- **Base chassis** (blue rectangular body)
- **4 mecanum wheels** (black cylinders) positioned at the corners
- **IMU sensor** (small red box) mounted on top
- **Proper joint definitions** for wheel rotation
- **Collision geometries** for physics simulation compatibility

## Interactive Controls

- Use the **Joint State Publisher GUI** to manually position joints
- Use **RViz camera controls** to orbit, zoom, and pan around your robot
- **Mouse controls**:
  - Left click + drag: Rotate view
  - Right click + drag: Pan view
  - Mouse wheel: Zoom in/out

## Customization

To modify the RViz configuration:

1. In RViz, go to **Panels → Add New Panel**
2. Add displays like LaserScan, PointCloud, etc. for additional sensors
3. Save your configuration via **File → Save Config**

## Troubleshooting

**Robot not visible in RViz:**
- Check that the robot description is being published: `ros2 topic list`
- Verify the fixed frame in RViz matches your robot's base frame (usually `base_link`)
- Check RViz console output for error messages

**Wheels not rotating:**
- The wheels are defined as continuous joints but need velocity commands to move
- Use the teleop nodes to control wheel movement

## Integration with Real Robot

When running with your physical robot:

1. Remove or disable the static transform publisher
2. Use real odometry data from your robot's wheel encoders
3. Add sensor data displays (IMU, camera, etc.)
4. The robot model will update based on real joint states and odometry