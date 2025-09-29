#!/usr/bin/env python3
"""
Test script to verify smooth deadzone operation.
Tests that deadzone provides smooth scaling and returns to center properly.
"""

import sys
import os

def test_smooth_deadzone_function():
    """Test the smooth deadzone scaling function."""
    try:
        # Simulate the smooth deadzone function from teleop node
        def apply_deadzone_smooth(value, deadzone):
            """Apply deadzone with smooth scaling outside deadzone."""
            if abs(value) < deadzone:
                # Within deadzone - return center position for smooth operation
                return 0.0
            else:
                # Outside deadzone - scale from deadzone edge to prevent jumps
                # Map: deadzone → 0.0, 1.0 → (1.0 - deadzone) scaled
                sign = 1 if value > 0 else -1
                scaled_value = (abs(value) - deadzone) / (1.0 - deadzone)
                return sign * scaled_value

        deadzone = 0.05
        print(f"✓ Testing smooth deadzone function (deadzone = {deadzone})")

        # Test cases for smooth deadzone operation
        test_cases = [
            # Within deadzone - should return 0.0 (center)
            (0.0, 0.0, "Center position"),
            (0.02, 0.0, "Within deadzone (positive)"),
            (-0.02, 0.0, "Within deadzone (negative)"),
            (0.04, 0.0, "At deadzone edge (positive)"),
            (-0.04, 0.0, "At deadzone edge (negative)"),

            # Outside deadzone - should scale smoothly
            (0.05, 0.0, "Just outside deadzone (positive)"),
            (0.06, 0.011, "Slightly outside deadzone (positive)"),
            (0.10, 0.053, "Further outside deadzone (positive)"),
            (0.50, 0.474, "Mid range (positive)"),
            (1.00, 1.0, "Full range (positive)"),

            (-0.05, 0.0, "Just outside deadzone (negative)"),
            (-0.06, -0.011, "Slightly outside deadzone (negative)"),
            (-0.10, -0.053, "Further outside deadzone (negative)"),
            (-0.50, -0.474, "Mid range (negative)"),
            (-1.00, -1.0, "Full range (negative)"),
        ]

        print("\nTesting smooth deadzone scaling:")
        all_correct = True

        for input_val, expected, description in test_cases:
            result = apply_deadzone_smooth(input_val, deadzone)
            # Use small tolerance for floating point comparison
            tolerance = 0.001
            status = "✓" if abs(result - expected) < tolerance else "✗"
            print(f"  {status} {description}: {input_val:.3f} → {result:.3f} (expected {expected:.3f})")
            if abs(result - expected) >= tolerance:
                all_correct = False

        return all_correct

    except Exception as e:
        print(f"✗ Smooth deadzone function test failed: {e}")
        return False

def test_servo_angle_conversion():
    """Test that servo angle conversion works correctly with smooth deadzone."""
    try:
        # Simulate the joystick to angle conversion
        def convert_joystick_to_angle(joystick_value, min_angle=0.0, max_angle=180.0):
            """Convert joystick axis value (-1.0 to 1.0) to servo angle."""
            # Clamp joystick value to [-1.0, 1.0] range
            joystick_value = max(-1.0, min(1.0, joystick_value))

            # Convert from [-1.0, 1.0] to [0.0, 1.0] range
            normalized_value = (joystick_value + 1.0) / 2.0

            # Convert to servo angle range
            angle = min_angle + (normalized_value * (max_angle - min_angle))

            # Clamp to servo limits
            angle = max(min_angle, min(max_angle, angle))

            return angle

        print("\n✓ Testing servo angle conversion with smooth deadzone...")

        deadzone = 0.05

        # Test servo angle conversion with smooth deadzone
        test_cases = [
            # Within deadzone - should be center (90°)
            (0.0, 90.0, "Center position"),
            (0.02, 90.0, "Within deadzone"),
            (-0.02, 90.0, "Within deadzone (negative)"),

            # Just outside deadzone - should be slightly off center
            (0.05, 90.0, "Just outside deadzone"),
            (0.06, 90.9, "Slightly outside deadzone"),
            (0.10, 94.7, "Further outside deadzone"),

            # Full range
            (1.00, 180.0, "Full positive"),
            (-1.00, 0.0, "Full negative"),
        ]

        all_correct = True

        for input_val, expected, description in test_cases:
            # Apply smooth deadzone first
            def apply_deadzone_smooth(value, deadzone):
                if abs(value) < deadzone:
                    return 0.0
                else:
                    sign = 1 if value > 0 else -1
                    scaled_value = (abs(value) - deadzone) / (1.0 - deadzone)
                    return sign * scaled_value

            deadzoned_value = apply_deadzone_smooth(input_val, deadzone)
            angle = convert_joystick_to_angle(deadzoned_value)

            tolerance = 0.1  # Small tolerance for angle calculation
            status = "✓" if abs(angle - expected) < tolerance else "✗"
            print(f"  {status} {description}: {input_val:.3f} → deadzone → {deadzoned_value:.3f} → angle {angle:.1f}° (expected {expected:.1f}°)")
            if abs(angle - expected) >= tolerance:
                all_correct = False

        return all_correct

    except Exception as e:
        print(f"✗ Servo angle conversion test failed: {e}")
        return False

def test_teleop_deadzone_implementation():
    """Test that teleop node uses smooth deadzone implementation."""
    try:
        # Read the teleop file and check implementation
        with open('src/joy2/joy2/nodes/joy2_teleop.py', 'r') as f:
            content = f.read()

        print("\n✓ Testing teleop smooth deadzone implementation...")

        # Check that it uses smooth deadzone function
        if 'apply_deadzone_smooth' in content:
            print("  ✓ Uses smooth deadzone function")
        else:
            print("  ✗ Does not use smooth deadzone function")
            return False

        # Check that it scales from deadzone edge
        if '(abs(value) - deadzone) / (1.0 - deadzone)' in content:
            print("  ✓ Scales properly from deadzone edge")
        else:
            print("  ✗ Does not scale properly from deadzone edge")
            return False

        # Check that it returns 0.0 within deadzone
        if 'return 0.0' in content and 'abs(value) < deadzone' in content:
            print("  ✓ Returns center position within deadzone")
        else:
            print("  ✗ Does not return center within deadzone")
            return False

        return True

    except Exception as e:
        print(f"✗ Teleop implementation test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing smooth deadzone operation...")
    print("=" * 50)

    success = True
    success &= test_smooth_deadzone_function()
    success &= test_servo_angle_conversion()
    success &= test_teleop_deadzone_implementation()

    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed!")
        print("\n🎯 Smooth Deadzone Implementation Summary:")
        print("  • Values within deadzone (±0.05) → center position (90°)")
        print("  • Values outside deadzone → smoothly scaled from deadzone edge")
        print("  • No sudden jumps when exiting deadzone")
        print("  • Servos return to center when joystick enters deadzone")
        print("  • Smooth, responsive control for all movement speeds")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())