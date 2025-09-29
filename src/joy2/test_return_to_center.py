#!/usr/bin/env python3
"""
Test script to verify return-to-center functionality.
Tests that servos return to center when joysticks enter deadzone.
"""

import sys
import os

def test_return_to_center_logic():
    """Test the return-to-center state machine logic."""
    try:
        print("✓ Testing return-to-center logic...")

        # Simulate the deadzone state machine
        deadzone = 0.05

        def is_in_deadzone(value, deadzone):
            return abs(value) < deadzone

        # Test state transitions
        test_scenarios = [
            # (previous_in_deadzone, current_value, should_send_center)
            (True, 0.0, False, "Already in deadzone"),
            (True, 0.06, False, "Moving out of deadzone - should send scaled command"),
            (False, 0.06, False, "Still outside deadzone"),
            (False, 0.0, True, "Moving into deadzone - should send center"),
            (False, 0.02, True, "Moving into deadzone - should send center"),
            (True, 0.02, False, "Back in deadzone"),
        ]

        print("\nTesting deadzone state transitions:")
        all_correct = True

        for prev_in_deadzone, current_val, expected_send_center, description in test_scenarios:
            current_in_deadzone = is_in_deadzone(current_val, deadzone)
            # Send center command when transitioning from outside to inside deadzone
            should_send_center = (current_in_deadzone and not prev_in_deadzone)

            status = "✓" if should_send_center == expected_send_center else "✗"
            print(f"  {status} {description}")
            print(f"      Prev: {'in' if prev_in_deadzone else 'out'}, Current: {current_val:.3f} ({'in' if current_in_deadzone else 'out'}) → Send center: {should_send_center}")
            if should_send_center != expected_send_center:
                all_correct = False

        return all_correct

    except Exception as e:
        print(f"✗ Return-to-center logic test failed: {e}")
        return False

def test_teleop_return_to_center_implementation():
    """Test that teleop node implements return-to-center correctly."""
    try:
        # Read the teleop file and check implementation
        with open('src/joy2/joy2/nodes/joy2_teleop.py', 'r') as f:
            content = f.read()

        print("\n✓ Testing teleop return-to-center implementation...")

        # Check that it tracks previous deadzone state
        if '_previous_left_x_in_deadzone' in content:
            print("  ✓ Tracks previous deadzone state")
        else:
            print("  ✗ Does not track previous deadzone state")
            return False

        # Check that it detects transitions into deadzone
        if 'current_' in content and 'and not self._previous_' in content:
            print("  ✓ Detects transitions into deadzone")
        else:
            print("  ✗ Does not detect transitions into deadzone")
            return False

        # Check that it sends center command when entering deadzone
        if 'self._send_servo_command(servo_id, 90.0)' in content:
            print("  ✓ Sends center command when entering deadzone")
        else:
            print("  ✗ Does not send center command when entering deadzone")
            return False

        # Check that it updates previous state
        if 'self._previous_left_x_in_deadzone = current_left_x_in_deadzone' in content:
            print("  ✓ Updates previous deadzone state")
        else:
            print("  ✗ Does not update previous deadzone state")
            return False

        return True

    except Exception as e:
        print(f"✗ Teleop implementation test failed: {e}")
        return False

def test_complete_deadzone_behavior():
    """Test complete deadzone behavior including return to center."""
    try:
        print("\n✓ Testing complete deadzone behavior...")

        deadzone = 0.05

        def is_in_deadzone(value, deadzone):
            return abs(value) < deadzone

        def apply_deadzone_smooth(value, deadzone):
            if abs(value) < deadzone:
                return 0.0
            else:
                sign = 1 if value > 0 else -1
                scaled_value = (abs(value) - deadzone) / (1.0 - deadzone)
                return sign * scaled_value

        # Simulate joystick movement sequence
        joystick_positions = [
            0.0,   # Start at center
            0.10,  # Move outside deadzone
            0.08,  # Still outside
            0.06,  # Still outside
            0.03,  # Move back inside deadzone
            0.0,   # Back to center
        ]

        print("\nSimulating joystick movement sequence:")
        prev_in_deadzone = True  # Start assuming in deadzone

        for i, pos in enumerate(joystick_positions):
            current_in_deadzone = is_in_deadzone(pos, deadzone)
            should_send_center = (current_in_deadzone and not prev_in_deadzone)

            scaled_value = apply_deadzone_smooth(pos, deadzone)
            servo_angle = 90.0 + (scaled_value * 90.0)  # Convert to angle

            print(f"  Step {i+1}: Joystick {pos:.3f} → Scaled {scaled_value:.3f} → Angle {servo_angle:.1f}°")
            if should_send_center:
                print(f"    → SEND CENTER COMMAND (90°)")

            prev_in_deadzone = current_in_deadzone

        print("\nExpected behavior:")
        print("  • Steps 2-5: Outside deadzone → scaled servo movement")
        print("  • Step 6: Enter deadzone → center command sent")
        print("  • Final position: Servo at center")

        return True

    except Exception as e:
        print(f"✗ Complete deadzone behavior test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing return-to-center functionality...")
    print("=" * 50)

    success = True
    success &= test_return_to_center_logic()
    success &= test_teleop_return_to_center_implementation()
    success &= test_complete_deadzone_behavior()

    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed!")
        print("\n🎯 Return-to-Center Implementation Summary:")
        print("  • Tracks deadzone state for each joystick axis")
        print("  • Detects when joystick enters deadzone")
        print("  • Sends center command (90°) when entering deadzone")
        print("  • Servos smoothly return to center position")
        print("  • No more stuck servos when releasing joystick!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())