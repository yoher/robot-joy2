#!/bin/bash
# Test script to move the robot in Gazebo

echo "🤖 Testing Robot Movement"
echo "========================="
echo ""

# Source the workspace
source install/setup.bash

# Wait for controllers to be ready
# echo "Waiting for simulation to initialize..."
# sleep 25

# Check available controllers
echo ""
echo "📋 Available controllers:"
ros2 control list_controllers

echo ""
echo "📊 Available topics:"
ros2 topic list | grep -E "cmd_vel|joint"

echo ""
echo "🚀 Sending forward velocity command for 3 seconds..."
timeout 3 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --rate 10

echo ""
echo "⏸️  Stopping robot..."
timeout 1 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --rate 10

echo ""
echo "🔄 Sending rotation command for 3 seconds..."
timeout 3 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}" --rate 10

echo ""
echo "⏸️  Stopping robot..."
timeout 1 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --rate 10

echo ""
echo "✅ Movement test complete! Check Gazebo window to see the robot movement."
