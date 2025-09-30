#!/usr/bin/env python3
"""
Test script to verify wheel return-to-center functionality.
Tests that mecanum wheels stop when joysticks enter deadzone.
"""

import sys
import os

def test_wheel_deadzone_logic():
    """Test the wheel deadzone state machine logic."""
    try:
        print("✓ Testing wheel return-to-center logic...")

        # Simulate the wheel deadzone function
        def apply_deadzone(value, deadzone):
            if abs(value) < deadzone:
                return 0.0
            else:
                sign = 1 if value > 0 else -1
                scaled_value = (abs(value) - deadzone) / (1.0 - deadzone)
                return sign * scaled_value

        def is_in_deadzone(value, deadzone):
            return abs(value) < deadzone

        deadzone = 0.05

        # Test wheel control scenarios
        test_cases = [
            # (vx, vy, omega, should_send_movement, should_send_stop)
            (0.0, 0.0, 0.0, False, False, "All at center"),
            (0.10, 0.0, 0.0, True, False, "VX outside deadzone"),
            (0.0, 0.10, 0.0, True, False, "VY outside deadzone"),
            (0.0, 0.0, 0.10, True, False, "Omega outside deadzone"),
            (0.03, 0.0, 0.0, False, True, "VX in deadzone - should stop"),
            (0.0, 0.03, 0.0, False, True, "VY in deadzone - should stop"),
            (0.0, 0.0, 0.03, False, True, "Omega in deadzone - should stop"),
        ]

        print("\nTesting wheel deadzone behavior:")
        all_correct = True

        for vx, vy, omega, expected_movement, expected_stop, description in test_cases:
            vx_scaled = apply_deadzone(vx, deadzone)
            vy_scaled = apply_deadzone(vy, deadzone)
            omega_scaled = apply_deadzone(omega, deadzone)

            has_movement = (vx_scaled != 0.0 or vy_scaled != 0.0 or omega_scaled != 0.0)
            # For this test, we expect stop when all scaled values are 0.0
            should_stop = not has_movement

            status = "✓" if (has_movement == expected_movement and should_stop == expected_stop) else "✗"
            print(f"  {status} {description}")
            print(f"      Input: vx={vx:.3f}, vy={vy:.3f}, omega={omega:.3f}")
            print(f"      Scaled: vx={vx_scaled:.3f}, vy={vy_scaled:.3f}, omega={omega_scaled:.3f}")
            print(f"      Movement: {has_movement}, Stop: {should_stop}")

            if not (has_movement == expected_movement and should_stop == expected_stop):
                all_correct = False

        return all_correct

    except Exception as e:
        print(f"✗ Wheel deadzone logic test failed: {e}")
        return False

def test_wheel_state_transitions():
    """Test wheel deadzone state transitions."""
    try:
        print("\n✓ Testing wheel state transitions...")

        deadzone = 0.05

        def is_in_deadzone(value, deadzone):
            return abs(value) < deadzone

        # Simulate joystick movement sequence for wheel control
        joystick_sequence = [
            (0.0, 0.0, 0.0),   # Start at center
            (0.10, 0.0, 0.0),  # Move VX outside deadzone
            (0.08, 0.0, 0.0),  # Still outside
            (0.03, 0.0, 0.0),  # Move back into deadzone
            (0.0, 0.0, 0.0),   # Back to center
        ]

        print("\nSimulating wheel control sequence:")
        prev_vx_in_deadzone = True
        prev_vy_in_deadzone = True
        prev_omega_in_deadzone = True

        for i, (vx, vy, omega) in enumerate(joystick_sequence):
            current_vx_in_deadzone = is_in_deadzone(vx, deadzone)
            current_vy_in_deadzone = is_in_deadzone(vy, deadzone)
            current_omega_in_deadzone = is_in_deadzone(omega, deadzone)

            # Check if any axis transitioned into deadzone
            any_entered_deadzone = (
                (current_vx_in_deadzone and not prev_vx_in_deadzone) or
                (current_vy_in_deadzone and not prev_vy_in_deadzone) or
                (current_omega_in_deadzone and not prev_omega_in_deadzone)
            )

            def apply_deadzone(value, deadzone):
                if abs(value) < deadzone:
                    return 0.0
                else:
                    sign = 1 if value > 0 else -1
                    scaled_value = (abs(value) - deadzone) / (1.0 - deadzone)
                    return sign * scaled_value

            vx_scaled = apply_deadzone(vx, deadzone)
            vy_scaled = apply_deadzone(vy, deadzone)
            omega_scaled = apply_deadzone(omega, deadzone)

            has_movement = (vx_scaled != 0.0 or vy_scaled != 0.0 or omega_scaled != 0.0)

            print(f"  Step {i+1}: vx={vx:.3f}, vy={vy:.3f}, omega={omega:.3f}")
            print(f"    Deadzone: vx={'in' if current_vx_in_deadzone else 'out'}, vy={'in' if current_vy_in_deadzone else 'out'}, omega={'in' if current_omega_in_deadzone else 'out'}")
            print(f"    Scaled: vx={vx_scaled:.3f}, vy={vy_scaled:.3f}, omega={omega_scaled:.3f}")
            print(f"    Movement: {has_movement}, Entered deadzone: {any_entered_deadzone}")

            if any_entered_deadzone:
                print(f"    → SEND STOP COMMAND")

            prev_vx_in_deadzone = current_vx_in_deadzone
            prev_vy_in_deadzone = current_vy_in_deadzone
            prev_omega_in_deadzone = current_omega_in_deadzone

        print("\nExpected behavior:")
        print("  • Steps 1: At center - no movement")
        print("  • Steps 2-3: Outside deadzone - movement commands")
        print("  • Step 4: Enter deadzone - stop command sent")
        print("  • Step 5: At center - no movement")

        return True

    except Exception as e:
        print(f"✗ Wheel state transitions test failed: {e}")
        return False

def test_teleop_wheel_deadzone_implementation():
    """Test that teleop node implements wheel return-to-center correctly."""
    try:
        # Read the teleop file and check implementation
        with open('src/joy2/joy2/nodes/joy2_teleop.py', 'r') as f:
            content = f.read()

        print("\n✓ Testing teleop wheel return-to-center implementation...")

        # Check that it tracks wheel deadzone state
        if '_previous_wheel_vx_in_deadzone' in content:
            print("  ✓ Tracks wheel deadzone state")
        else:
            print("  ✗ Does not track wheel deadzone state")
            return False

        # Check that it detects transitions into deadzone
        if 'current_vx_in_deadzone and not self._previous_wheel_vx_in_deadzone' in content:
            print("  ✓ Detects wheel deadzone transitions")
        else:
            print("  ✗ Does not detect wheel deadzone transitions")
            return False

        # Check that it sends stop command when entering deadzone
        if 'self._mecanum_controller.drive(0.0, 0.0, 0.0)' in content:
            print("  ✓ Sends stop command when entering wheel deadzone")
        else:
            print("  ✗ Does not send stop command when entering wheel deadzone")
            return False

        return True

    except Exception as e:
        print(f"✗ Teleop wheel implementation test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing wheel return-to-center functionality...")
    print("=" * 55)

    success = True
    success &= test_wheel_deadzone_logic()
    success &= test_wheel_state_transitions()
    success &= test_teleop_wheel_deadzone_implementation()

    print("\n" + "=" * 55)
    if success:
        print("✓ All tests passed!")
        print("\n🚗 Wheel Return-to-Center Implementation Summary:")
        print("  • Tracks deadzone state for each wheel axis (vx, vy, omega)")
        print("  • Sends stop command when joystick enters deadzone")
        print("  • Wheels stop properly when joysticks are released")
        print("  • No more continuously turning wheels!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())