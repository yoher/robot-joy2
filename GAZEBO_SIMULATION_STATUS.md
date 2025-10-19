# Gazebo Simulation Status Report

**Date:** October 19, 2025  
**Repository:** robot-joy2  
**Branch:** master

## ✅ Completed Fixes

### 1. **Controller Configuration Files** ✅ **FIXED**
- **Problem:** Missing `mecanum_controller.yaml` and `diff_controller.yaml` 
- **Solution:** Created ROS2 Control configuration files
- **Files Created:**
  - `src/joy2_control/config/mecanum_controller.yaml`
  - `src/joy2_control/config/diff_controller.yaml`
- **Result:** Configuration errors resolved$$

### 2. **Dependencies Installed** ✅ **COMPLETE**
- ✅ `ros-jazzy-controller-manager`
- ✅ `ros-jazzy-ros2-controllers`
- ✅ `ros-jazzy-gz-ros2-control`
- ✅ `ros-jazzy-gz-ros2-control-demos`
- ✅ `ros-jazzy-ros-gz-bridge`
- ✅ `ros-jazzy-ros-gz-sim`

### 3. **Launch File Improvements** ✅ **UPDATED**
- **File:** `src/joy2_bringup/launch/gazebo_simulation.launch.py`
- **Changes:**
  - Conditional GUI/headless mode support
  - Improved robot spawning using `ros_gz_sim` create node
  - Adjusted timing delays for better startup reliability
  - Better error handling

### 4. **Alternative Launch File Created** ✅ **NEW**
- **File:** `src/joy2_bringup/launch/simple_gazebo.launch.py`
- **Purpose:** Simplified Gazebo launch for testing without full control system

## ⚠️ Known Issues

### 1. **Snap Library Conflicts** ⚠️ **BLOCKING GUI**
**Error:**
```
gz sim gui: symbol lookup error: /snap/core20/current/lib/x86_64-linux-gnu/libpthread.so.0: 
undefined symbol: __libc_pthread_init, version GLIBC_PRIVATE
```

**Affected:**
- ❌ Gazebo GUI
- ❌ RViz2 GUI

**Workaround:**
- Use headless mode: `use_gui:=false`

**Permanent Fix Options:**
1. Remove snap packages interfering with system libraries
2. Set `LD_PRELOAD` to use system libraries
3. Install Gazebo from apt instead of snap
4. Use Docker for consistent environment

### 2. **Gazebo Service Communication** ⚠️ **NON-CRITICAL**
**Symptoms:**
- `Error setting socket option (IP_ADD_MEMBERSHIP)`
- `Invalid partition name` errors
- Some Gazebo services timeout

**Impact:** 
- Network warnings (cosmetic)
- Does not prevent simulation from running

**Status:** Known Gazebo Garden issue, does not affect core functionality

### 3. **ROS2 Control Hardware Interface** ⚠️ **NEEDS VERIFICATION**
**Error:**
```
[ERROR] [controller_manager:load_hardware]: Caught exception of type : N9pluginlib20LibraryLoadExceptionE 
while loading hardware: According to the loaded plugin descriptions the class gz_ros2_control/GazeboSystem 
with base class type hardware_interface::SystemInterface does not exist.
```

**Status:** Package installed but plugin not loading properly

**Next Steps:**
1. Verify plugin registration: `ros2 pkg list | grep gz_ros2_control`
2. Check plugin path: `echo $GAZEBO_PLUGIN_PATH`
3. May need to rebuild workspace or source environment again

## 🎯 Current Simulation Status

### ✅ **Working Components**
- ✅ Gazebo Server (headless mode)
- ✅ Robot Description (URDF/xacro)
- ✅ Robot State Publisher
- ✅ Joint State Publisher
- ✅ ROS-Gazebo Bridge (parameter_bridge)
- ✅ Robot Spawning (via ros_gz_sim create)
- ✅ Clock synchronization
- ✅ Topic bridges (cmd_vel, imu, joint_states)

### ⚠️ **Partially Working**
- ⚠️ ROS2 Control (plugin not loading)
- ⚠️ Controller Spawners (waiting for hardware interface)

### ❌ **Not Working**
- ❌ Gazebo GUI (snap conflicts)
- ❌ RViz GUI (snap conflicts)
- ❌ Gazebo services (network/permissions issues)

## 📋 How to Launch

### **Recommended: Headless Mode**
```bash
cd /home/yoann.hervieux@celadodc-rswl.com/dev/yhx/robot-joy2
source install/setup.bash
ros2 launch joy2_bringup gazebo_simulation.launch.py use_gui:=false
```

### **With GUI (if snap issues resolved)**
```bash
ros2 launch joy2_bringup gazebo_simulation.launch.py use_gui:=true
```

### **Simple Test Launch**
```bash
ros2 launch joy2_bringup simple_gazebo.launch.py
```

### **Available Launch Arguments**
- `drive_type`: `mecanum` (default) or `diff`
- `use_sim_time`: `true` (default) or `false`
- `use_gui`: `true` (default) or `false`

## 🔍 Verification Commands

### Check Running Nodes
```bash
ros2 node list
```

### Check Topics
```bash
ros2 topic list
```

### Monitor Robot Description
```bash
ros2 topic echo /robot_description
```

### Test Velocity Commands
```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.1}}'
```

### Check Joint States
```bash
ros2 topic echo /joint_states
```

### List Controllers
```bash
ros2 control list_controllers
```

## 🛠️ Troubleshooting

### If Gazebo Doesn't Start
```bash
# Kill any existing Gazebo instances
pkill -f "gz sim"

# Check Gazebo version
gz sim --version

# Try launching manually
gz sim -v 4
```

### If ROS2 Control Plugin Not Found
```bash
# Check installed packages
ros2 pkg list | grep gz_ros2_control

# Rebuild workspace
cd ~/dev/yhx/robot-joy2
colcon build --packages-select joy2_description joy2_control joy2_bringup
source install/setup.bash
```

### If Controllers Won't Load
```bash
# Check controller manager status
ros2 control list_hardware_interfaces

# View controller manager logs
ros2 run controller_manager ros2_control_node --ros-args --log-level debug
```

## 📊 Test Results

### Last Test: October 19, 2025 22:30
- ✅ Gazebo starts successfully (headless)
- ✅ Robot description publishes
- ✅ Robot spawns in simulation
- ✅ ROS-Gazebo bridges active
- ✅ Topics available
- ⚠️ Controller hardware interface not loading
- ❌ GUI not working (snap conflicts)

## 🎯 Next Steps

### High Priority
1. **Resolve ROS2 Control Hardware Interface**
   - Verify plugin path
   - Check pluginlib registration
   - May need environment variable configuration

2. **Fix Snap Conflicts for GUI**
   - Test with `LD_PRELOAD` workaround
   - Consider reinstalling Gazebo from apt
   - Or accept headless-only operation

### Medium Priority
3. **Test Controller Functionality**
   - Once hardware interface loads
   - Verify mecanum controller responds
   - Test velocity commands

4. **Add World/Environment**
   - Current simulation uses empty world
   - Add ground plane, obstacles
   - Configure physics parameters

### Low Priority
5. **Documentation**
   - Update README with simulation instructions
   - Add troubleshooting guide
   - Create example launch configurations

## 📝 Files Modified/Created

### Modified
- `src/joy2_bringup/launch/gazebo_simulation.launch.py`

### Created
- `src/joy2_control/config/mecanum_controller.yaml`
- `src/joy2_control/config/diff_controller.yaml`
- `src/joy2_bringup/launch/simple_gazebo.launch.py`
- `GAZEBO_SIMULATION_STATUS.md` (this file)

## 🎓 Lessons Learned

1. **Snap Packages**: Can interfere with native system libraries - be careful with mixed snap/apt installations
2. **ROS2 Control**: Requires proper plugin registration and hardware interface configuration
3. **Timing**: Gazebo needs adequate startup time before other nodes launch
4. **Headless Mode**: Often more reliable for development/testing than full GUI

## 📞 Support Resources

- [ROS2 Control Documentation](https://control.ros.org/master/index.html)
- [Gazebo Garden Docs](https://gazebosim.org/docs/garden)
- [ros_gz Integration](https://github.com/gazebosim/ros_gz)
- [Snap Issues](https://github.com/snapcore/snapd/issues)

---

**Status:** 🟡 **Partially Functional** - Core simulation works, controllers need debugging  
**Last Updated:** October 19, 2025 22:31  
**Updated By:** GitHub Copilot
