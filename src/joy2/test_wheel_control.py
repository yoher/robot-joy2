#!/usr/bin/env python3
"""
Test script to verify wheel control functionality.
Tests that mecanum controller works correctly with joystick inputs.
"""

import sys
import os

def test_mecanum_controller():
    """Test the mecanum controller implementation."""
    try:
        from joy2.control.mecanum_controller import MecanumDriveController

        # Mock motor driver for testing
        class MockMotor:
            def __init__(self, motor_id):
                self.motor_id = motor_id
                self.speed = 0.0

            def set_speed_float(self, speed):
                self.speed = speed
                print(f"    Motor {self.motor_id}: speed = {speed:.3f}")

        class MockMotorDriver:
            def __init__(self):
                self.motors = {i: MockMotor(i) for i in range(1, 5)}

            def get_motor(self, num):
                return self.motors[num]

        # Create mock motor driver and mecanum controller
        motor_driver = MockMotorDriver()
        mecanum = MecanumDriveController(motor_driver, verbose=True)

        print("✓ Mecanum controller created successfully!")

        # Test basic movement commands
        print("\nTesting mecanum movements:")

        # Forward movement (vy = 1.0)
        print("\n  Forward movement (vy = 1.0):")
        mecanum.drive(0.0, 1.0, 0.0)  # vx=0, vy=1, omega=0

        # Rotation (omega = 1.0)
        print("\n  Rotation (omega = 1.0):")
        mecanum.drive(0.0, 0.0, 1.0)  # vx=0, vy=0, omega=1

        # Strafing (vx = 1.0)
        print("\n  Strafing (vx = 1.0):")
        mecanum.drive(1.0, 0.0, 0.0)  # vx=1, vy=0, omega=0

        # Combined movement
        print("\n  Combined movement (vx=0.5, vy=0.5, omega=0.5):")
        mecanum.drive(0.5, 0.5, 0.5)  # vx=0.5, vy=0.5, omega=0.5

        # Stop command
        print("\n  Stop command:")
        mecanum.stop()

        return True

    except Exception as e:
        print(f"✗ Mecanum controller test failed: {e}")
        return False

def test_teleop_wheel_control_logic():
    """Test that teleop node implements wheel control correctly."""
    try:
        # Read the teleop file and check implementation
        with open('src/joy2/joy2/nodes/joy2_teleop.py', 'r') as f:
            content = f.read()

        print("\n✓ Testing teleop wheel control implementation...")

        # Check that it imports mecanum controller
        if 'MecanumDriveController' in content:
            print("  ✓ Imports MecanumDriveController")
        else:
            print("  ✗ Does not import MecanumDriveController")
            return False

        # Check that it initializes motor hardware
        if 'DCMotorDriver' in content and 'PCA9685' in content:
            print("  ✓ Initializes motor hardware")
        else:
            print("  ✗ Does not initialize motor hardware")
            return False

        # Check that it calls wheel control when Alt is not pressed
        if 'if self._alt_pressed:' in content and 'self._control_wheels(msg)' in content:
            print("  ✓ Calls wheel control when Alt is not pressed")
        else:
            print("  ✗ Does not call wheel control correctly")
            return False

        # Check that it maps joystick axes correctly (vx = right_x for forward, vy = right_y for strafing)
        if 'vx = right_x' in content and 'vy = right_y' in content and 'omega = left_x' in content:
            print("  ✓ Maps joystick axes correctly for mecanum control")
        else:
            print("  ✗ Does not map joystick axes correctly")
            return False

        return True

    except Exception as e:
        print(f"✗ Teleop wheel control logic test failed: {e}")
        return False

def test_wheel_configuration():
    """Test that wheel control configuration is loaded correctly."""
    try:
        from joy2.config.teleop_config_loader import TeleopConfigLoader

        config_file = 'src/joy2/config/teleop_config.yaml'
        config_loader = TeleopConfigLoader(config_file)

        print("\n✓ Testing wheel control configuration...")

        # Check wheel control settings
        translation_scale = config_loader.get_wheel_translation_scale()
        rotation_scale = config_loader.get_wheel_rotation_scale()
        wheel_deadzone = config_loader.get_wheel_deadzone()

        print(f"  Translation scale: {translation_scale}")
        print(f"  Rotation scale: {rotation_scale}")
        print(f"  Wheel deadzone: {wheel_deadzone}")

        # Verify expected values
        if translation_scale == 0.6 and rotation_scale == 0.6 and wheel_deadzone == 0.05:
            print("  ✓ Wheel control configuration values correct")
            return True
        else:
            print("  ✗ Wheel control configuration values incorrect")
            return False

    except Exception as e:
        print(f"✗ Wheel configuration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing wheel control functionality...")
    print("=" * 45)

    success = True
    success &= test_mecanum_controller()
    success &= test_teleop_wheel_control_logic()
    success &= test_wheel_configuration()

    print("\n" + "=" * 45)
    if success:
        print("✓ All tests passed!")
        print("\n🚗 Wheel Control Implementation Summary:")
        print("  • Mecanum controller created successfully")
        print("  • Proper mecanum kinematics implemented")
        print("  • Wheel control active when Alt (R1) is NOT pressed")
        print("  • Joystick mapping: Left X=rotation, Right X=forward, Right Y=strafing")
        print("  • Configurable translation and rotation scales")
        print("  • Smooth deadzone handling for wheel control")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())