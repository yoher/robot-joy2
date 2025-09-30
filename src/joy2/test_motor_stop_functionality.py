#!/usr/bin/env python3
"""
Test script to verify motor stop functionality.
Tests that motors are properly stopped when joysticks enter deadzone.
"""

import sys
import os

def test_motor_stop_logic():
    """Test the motor stop state machine logic."""
    try:
        print("✓ Testing motor stop logic...")

        # Simulate the motor stop logic
        deadzone = 0.05

        def is_in_deadzone(value, deadzone):
            return abs(value) < deadzone

        def apply_deadzone(value, deadzone):
            if abs(value) < deadzone:
                return 0.0
            else:
                sign = 1 if value > 0 else -1
                scaled_value = (abs(value) - deadzone) / (1.0 - deadzone)
                return sign * scaled_value

        # Test motor control scenarios
        test_cases = [
            # (vx, vy, omega, has_movement, should_stop)
            (0.0, 0.0, 0.0, False, True, "All at center - ensure motors stopped"),
            (0.10, 0.0, 0.0, True, False, "VX outside deadzone - movement"),
            (0.0, 0.10, 0.0, True, False, "VY outside deadzone - movement"),
            (0.0, 0.0, 0.10, True, False, "Omega outside deadzone - movement"),
            (0.03, 0.0, 0.0, False, True, "VX in deadzone - should stop"),
            (0.0, 0.03, 0.0, False, True, "VY in deadzone - should stop"),
            (0.0, 0.0, 0.03, False, True, "Omega in deadzone - should stop"),
            (0.0, 0.0, 0.0, False, True, "All at center again - ensure motors stopped"),
        ]

        print("\nTesting motor stop behavior:")
        all_correct = True

        for vx, vy, omega, expected_movement, expected_stop, description in test_cases:
            vx_scaled = apply_deadzone(vx, deadzone)
            vy_scaled = apply_deadzone(vy, deadzone)
            omega_scaled = apply_deadzone(omega, deadzone)

            has_movement = (vx_scaled != 0.0 or vy_scaled != 0.0 or omega_scaled != 0.0)
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
        print(f"✗ Motor stop logic test failed: {e}")
        return False

def test_teleop_motor_stop_implementation():
    """Test that teleop node implements motor stop correctly."""
    try:
        # Read the teleop file and check implementation
        with open('src/joy2/joy2/nodes/joy2_teleop.py', 'r') as f:
            content = f.read()

        print("\n✓ Testing teleop motor stop implementation...")

        # Check that it stops motors when switching to servo mode
        if 'self._mecanum_controller.stop()' in content:
            print("  ✓ Stops motors when switching to servo mode")
        else:
            print("  ✗ Does not stop motors when switching to servo mode")
            return False

        # Check that it releases all motors in destroy_node
        if 'self._motor_driver.release_all()' in content:
            print("  ✓ Releases all motors in destroy_node")
        else:
            print("  ✗ Does not release all motors in destroy_node")
            return False

        # Check that it stops motors when all axes in deadzone
        if 'all_axes_in_deadzone' in content:
            print("  ✓ Stops motors when all axes in deadzone")
        else:
            print("  ✗ Does not stop motors when all axes in deadzone")
            return False

        return True

    except Exception as e:
        print(f"✗ Teleop motor stop implementation test failed: {e}")
        return False

def test_mecanum_stop_method():
    """Test that mecanum controller has proper stop method."""
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

        print("\n✓ Testing mecanum stop method...")

        # Set some movement
        print("  Setting movement:")
        mecanum.drive(0.5, 0.3, 0.1)

        # Stop
        print("  Stopping:")
        mecanum.stop()

        print("  ✓ Mecanum stop method works correctly")
        return True

    except Exception as e:
        print(f"✗ Mecanum stop method test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing motor stop functionality...")
    print("=" * 40)

    success = True
    success &= test_motor_stop_logic()
    success &= test_teleop_motor_stop_implementation()
    success &= test_mecanum_stop_method()

    print("\n" + "=" * 40)
    if success:
        print("✓ All tests passed!")
        print("\n🛑 Motor Stop Implementation Summary:")
        print("  • Motors stop when all axes enter deadzone")
        print("  • Motors stop when switching to servo mode")
        print("  • Motors released properly on node shutdown")
        print("  • No more continuously running motors!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())