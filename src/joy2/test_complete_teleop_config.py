#!/usr/bin/env python3
"""
Test script to verify complete teleop configuration with all four servos.
"""

import sys
import os

def test_teleop_configuration():
    """Test that teleop node has correct configuration for all servos."""
    try:
        # Read the teleop file and check all servo IDs
        with open('src/joy2/joy2/nodes/joy2_teleop.py', 'r') as f:
            content = f.read()

        print("Testing teleop configuration...")

        # Check servo ID assignments
        expected_assignments = [
            ('SERVO_1_ID = "c1"', "Left X axis → c1 (continuous, channel 8)"),
            ('SERVO_2_ID = "c2"', "Left Y axis → c2 (continuous, channel 9)"),
            ('SERVO_3_ID = "p1"', "Right X axis → p1 (positional, channel 10)"),
            ('SERVO_4_ID = "p2"', "Right Y axis → p2 (positional, channel 11)"),
        ]

        all_correct = True
        for assignment, description in expected_assignments:
            if assignment in content:
                print(f"✓ {description}")
            else:
                print(f"✗ Missing: {description}")
                all_correct = False

        # Check joystick axes
        if 'RIGHT_JOYSTICK_X = 3' in content and 'RIGHT_JOYSTICK_Y = 4' in content:
            print("✓ Right joystick axes configured correctly")
        else:
            print("✗ Right joystick axes not configured correctly")
            all_correct = False

        # Check that speed field is not used
        if 'msg.speed' not in content:
            print("✓ Speed field properly removed")
        else:
            print("✗ Speed field still present")
            all_correct = False

        return all_correct

    except Exception as e:
        print(f"✗ Teleop configuration test failed: {e}")
        return False

def test_servo_configuration():
    """Test that servo configuration matches teleop expectations."""
    try:
        with open('src/joy2/config/servo_config.yaml', 'r') as f:
            content = f.read()

        print("\nTesting servo configuration...")

        # Check that all expected servos are configured
        expected_servos = ['c1:', 'c2:', 'p1:', 'p2:']
        for servo in expected_servos:
            if servo in content:
                print(f"✓ Servo {servo.replace(':', '')} is configured")
            else:
                print(f"✗ Servo {servo.replace(':', '')} is missing from configuration")
                return False

        # Check channels match expectations
        if 'c1:' in content and 'channel: 8' in content and 'c2:' in content and 'channel: 9' in content:
            print("✓ Continuous servo channels correct (8, 9)")
        else:
            print("✗ Continuous servo channels incorrect")
            return False

        if 'p1:' in content and 'channel: 10' in content and 'p2:' in content and 'channel: 11' in content:
            print("✓ Positional servo channels correct (10, 11)")
        else:
            print("✗ Positional servo channels incorrect")
            return False

        return True

    except Exception as e:
        print(f"✗ Servo configuration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing complete teleop configuration with all four servos...")
    print("=" * 65)

    success = True
    success &= test_teleop_configuration()
    success &= test_servo_configuration()

    print("\n" + "=" * 65)
    if success:
        print("✓ All tests passed!")
        print("\n🎮 Teleop Configuration Summary:")
        print("  Left Joystick:")
        print("    X-axis → c1 (continuous servo, channel 8)")
        print("    Y-axis → c2 (continuous servo, channel 9)")
        print("  Right Joystick:")
        print("    X-axis → p1 (positional servo, channel 10)")
        print("    Y-axis → p2 (positional servo, channel 11)")
        print("\nAll servos are now controllable via joystick!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())