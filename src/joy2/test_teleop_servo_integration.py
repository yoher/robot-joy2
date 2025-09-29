#!/usr/bin/env python3
"""
Test script to verify teleop node works with the new servo system.
"""

import sys
import os

# Add the joy2 package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'joy2'))

def test_teleop_servo_mapping():
    """Test that teleop node uses correct string servo IDs."""
    try:
        # Import and check the teleop node configuration
        sys.path.insert(0, 'src/joy2/joy2')

        # Read the teleop file and check servo IDs
        with open('src/joy2/joy2/nodes/joy2_teleop.py', 'r') as f:
            content = f.read()

        # Check that it uses string IDs
        if 'SERVO_1_ID = "c1"' in content and 'SERVO_2_ID = "c2"' in content:
            print("✓ Teleop node uses correct string servo IDs")
            print("  SERVO_1_ID = 'c1' (Left X axis)")
            print("  SERVO_2_ID = 'c2' (Left Y axis)")
        else:
            print("✗ Teleop node servo IDs not updated correctly")
            return False

        # Check that speed field is removed
        if 'msg.speed' not in content:
            print("✓ Speed field removed from ServoCommand")
        else:
            print("✗ Speed field still present in teleop node")
            return False

        return True

    except Exception as e:
        print(f"✗ Teleop servo mapping test failed: {e}")
        return False

def test_servo_command_message():
    """Test that ServoCommand message structure is correct."""
    try:
        from joy2_interfaces.msg import ServoCommand

        # Create a test message
        msg = ServoCommand()
        msg.servo_id = "c1"
        msg.angle = 90.0

        print("✓ ServoCommand message structure is correct")
        print(f"  servo_id: {msg.servo_id}")
        print(f"  angle: {msg.angle}")

        # Check that speed attribute doesn't exist
        if not hasattr(msg, 'speed'):
            print("✓ Speed field successfully removed from message")
        else:
            print("✗ Speed field still exists in message")
            return False

        return True

    except Exception as e:
        print(f"✗ ServoCommand message test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing teleop to servo system integration...")
    print("=" * 55)

    success = True
    success &= test_teleop_servo_mapping()
    success &= test_servo_command_message()

    print("\n" + "=" * 55)
    if success:
        print("✓ All integration tests passed!")
        print("\nThe teleop node should now work correctly with the new servo system:")
        print("- Joystick movements will control servos 'c1' and 'c2'")
        print("- Servo commands will use string IDs instead of negative numbers")
        print("- The servo node will accept these commands and control the servos")
        return 0
    else:
        print("✗ Some integration tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())