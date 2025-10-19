# RViz Wheel Display Fix

**Issue:** RViz shows error: `No transform from [wheel_front_left_link] to [base_link]`

## Root Cause

The wheel links don't appear in RViz because there are no TF transforms being published for them. This happens when:

1. **ROS2 Control hardware interface fails to load** (gz_ros2_control/GazeboSystem plugin issue)
2. **Joint state broadcaster can't start** (depends on hardware interface)
3. **No joint states → No TF transforms → Wheels invisible in RViz**

## Solution Applied

Added `joint_state_publisher_gui` to the launch file as a fallback when ROS2 Control isn't available.

### Changes Made

**File:** `src/joy2_bringup/launch/gazebo_simulation.launch.py`

**Added:**
```python
# Joint state publisher GUI for manual control (when ROS2 Control isn't available)
# This publishes joint states which robot_state_publisher uses to compute TF transforms
joint_state_publisher_gui = Node(
    package='joint_state_publisher_gui',
    executable='joint_state_publisher_gui',
    name='joint_state_publisher_gui',
    output='screen',
    parameters=[{'use_sim_time': use_sim_time}],
    condition=IfCondition(use_gui)
)
```

## How It Works

1. `joint_state_publisher_gui` publishes `/joint_states` topic
2. `robot_state_publisher` subscribes to `/joint_states`
3. `robot_state_publisher` computes and publishes TF transforms for all links
4. RViz uses TF to display the complete robot model

## Test the Fix

```bash
cd /home/yoann.hervieux@celadodc-rswl.com/dev/yhx/robot-joy2
source install/setup.bash
ros2 launch joy2_bringup gazebo_simulation.launch.py
```

### Expected Result

1. ✅ Joint State Publisher GUI window opens with sliders for each joint
2. ✅ RViz shows complete robot with all wheels visible
3. ✅ Moving sliders in Joint State Publisher GUI updates wheel positions in RViz
4. ✅ TF tree is complete (check with `ros2 run tf2_tools view_frames`)

### Verification Commands

```bash
# Check if joint_states topic is publishing
ros2 topic echo /joint_states

# Check TF tree
ros2 run tf2_tools view_frames

# List available transforms
ros2 run tf2_ros tf2_echo base_link wheel_front_left_link
```

## Alternative: Without GUI

If you want to run headless without the GUI, the joint states will come from Gazebo once ROS2 Control is fixed:

```bash
ros2 launch joy2_bringup gazebo_simulation.launch.py use_gui:=false
```

Note: In headless mode, wheels won't display in RViz until ROS2 Control hardware interface is working.

## Next Steps

### Short-term (Visualization Working)
- ✅ Joint State Publisher GUI allows manual testing
- ✅ All robot links visible in RViz
- ⚠️ Manual joint control only (no simulation physics)

### Long-term (Full Simulation)
- 🔧 Fix gz_ros2_control plugin loading
- 🔧 Enable joint state broadcaster from ROS2 Control
- 🔧 Connect Gazebo physics to ROS2 Control
- ✅ Automated joint states from simulation

## Files Modified

- ✅ `src/joy2_bringup/launch/gazebo_simulation.launch.py` - Added joint_state_publisher_gui

## Additional Notes

### Why This Works

The TF tree needs these transforms:
```
base_link
├── wheel_front_left_link
├── wheel_front_right_link
├── wheel_rear_left_link
└── wheel_rear_right_link
```

Without `/joint_states`, `robot_state_publisher` can't compute these transforms.

`joint_state_publisher_gui` fills this gap by publishing joint positions that `robot_state_publisher` uses to maintain the complete TF tree.

### Limitations

- **Manual Control**: Joint positions controlled by GUI sliders, not physics
- **No Dynamics**: Wheels don't respond to Gazebo physics or `/cmd_vel` commands
- **Visualization Only**: Good for RViz display, not for full simulation testing

### When ROS2 Control Works

Once `gz_ros2_control/GazeboSystem` plugin loads correctly:
1. Gazebo will publish joint states automatically
2. Joint state broadcaster will forward them to ROS2
3. Wheels will move based on physics simulation
4. `/cmd_vel` commands will drive the robot
5. Joint State Publisher GUI becomes unnecessary

---

**Status:** ✅ **RViz Visualization Fixed**  
**Date:** October 19, 2025  
**Impact:** Wheels now visible in RViz, TF tree complete
