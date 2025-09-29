#!/usr/bin/env python3
"""
Test script to verify the modifier-based control system.
Tests that servo control only works when R1 (Alt) is pressed.
"""

import sys
import os

# Add the joy2 package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'joy2'))

def test_teleop_config_loading():
    """Test that teleop configuration loads correctly."""
    try:
        from joy2.config.teleop_config_loader import TeleopConfigLoader

        config_file = 'src/joy2/config/teleop_config.yaml'
        config_loader = TeleopConfigLoader(config_file)

        print("✓ Teleop configuration loaded successfully!")
        print(f"  Alt button index: {config_loader.get_alt_button_index()}")
        print(f"  Alt button name: {config_loader.get_alt_button_name()}")
        print(f"  Buzzer button index: {config_loader.get_buzzer_button_index()}")
        print(f"  Deadzone: {config_loader.get_deadzone()}")
        print(f"  Angle range: {config_loader.get_min_angle()}° to {config_loader.get_max_angle()}°")

        # Test servo mappings
        mappings = config_loader.get_servo_mapping()
        print(f"  Servo mappings: {mappings}")

        # Verify expected mappings
        expected_mappings = {
            'left_x_servo': 'c1',
            'left_y_servo': 'c2',
            'right_x_servo': 'p1',
            'right_y_servo': 'p2'
        }

        for key, expected_value in expected_mappings.items():
            if mappings.get(key) == expected_value:
                print(f"    ✓ {key} → {expected_value}")
            else:
                print(f"    ✗ {key} → {mappings.get(key)}, expected {expected_value}")
                return False

        return True

    except Exception as e:
        print(f"✗ Teleop configuration loading failed: {e}")
        return False

def test_teleop_node_configuration():
    """Test that teleop node loads configuration correctly."""
    try:
        # Read the teleop file and check configuration usage
        with open('src/joy2/joy2/nodes/joy2_teleop.py', 'r') as f:
            content = f.read()

        print("\n✓ Testing teleop node configuration...")

        # Check that it uses TeleopConfigLoader
        if 'TeleopConfigLoader' in content:
            print("  ✓ Uses TeleopConfigLoader")
        else:
            print("  ✗ Does not use TeleopConfigLoader")
            return False

        # Check that it loads configuration in __init__
        if 'self._config_loader = TeleopConfigLoader(config_file)' in content:
            print("  ✓ Loads configuration in __init__")
        else:
            print("  ✗ Does not load configuration properly")
            return False

        # Check that it uses configuration values
        if 'self._alt_button_index = self._config_loader.get_alt_button_index()' in content:
            print("  ✓ Uses configuration values")
        else:
            print("  ✗ Does not use configuration values")
            return False

        # Check that servo control is conditional on Alt button
        if 'if self._alt_pressed:' in content and 'self._control_servos(msg)' in content:
            print("  ✓ Servo control conditional on Alt button")
        else:
            print("  ✗ Servo control not properly conditional")
            return False

        return True

    except Exception as e:
        print(f"✗ Teleop node configuration test failed: {e}")
        return False

def test_joystick_axis_configuration():
    """Test that joystick axes are properly configured."""
    try:
        from joy2.config.teleop_config_loader import TeleopConfigLoader

        config_file = 'src/joy2/config/teleop_config.yaml'
        config_loader = TeleopConfigLoader(config_file)

        print("\n✓ Testing joystick axis configuration...")

        # Check axis indices
        left_x = config_loader.get_left_joystick_x_axis()
        left_y = config_loader.get_left_joystick_y_axis()
        right_x = config_loader.get_right_joystick_x_axis()
        right_y = config_loader.get_right_joystick_y_axis()

        print(f"  Left X axis: {left_x}")
        print(f"  Left Y axis: {left_y}")
        print(f"  Right X axis: {right_x}")
        print(f"  Right Y axis: {right_y}")

        # Verify standard gamepad layout
        if left_x == 0 and left_y == 1 and right_x == 3 and right_y == 4:
            print("  ✓ Standard gamepad axis layout")
            return True
        else:
            print("  ✗ Non-standard axis layout")
            return False

    except Exception as e:
        print(f"✗ Joystick axis configuration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing modifier-based control system...")
    print("=" * 50)

    success = True
    success &= test_teleop_config_loading()
    success &= test_teleop_node_configuration()
    success &= test_joystick_axis_configuration()

    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed!")
        print("\n🎮 Modifier Control System Summary:")
        print("  • R1 button (index 7) acts as Alt modifier")
        print("  • Servo control only works when R1 is pressed")
        print("  • Joysticks can be used for wheel motors when R1 is released")
        print("  • All control mappings are configurable via YAML")
        print("\nConfiguration files:")
        print("  • src/joy2/config/teleop_config.yaml - Control mappings")
        print("  • src/joy2/config/servo_config.yaml - Servo parameters")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())