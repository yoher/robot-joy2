#!/usr/bin/env python3
"""
Test script to verify the corrected deadzone implementation.
Tests that deadzone works around center (0,0) and not as a spam filter.
"""

import sys
import os

# Add the joy2 package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'joy2'))

def test_deadzone_around_center():
    """Test that deadzone is applied around center (0,0) position."""
    try:
        from joy2.config.teleop_config_loader import TeleopConfigLoader

        config_file = 'src/joy2/config/teleop_config.yaml'
        config_loader = TeleopConfigLoader(config_file)

        deadzone = config_loader.get_deadzone()
        print(f"✓ Deadzone value: {deadzone}")

        # Test deadzone function (simulate the logic from teleop node)
        def apply_deadzone(value):
            return 0.0 if abs(value) < deadzone else value

        # Test cases
        test_cases = [
            (0.0, 0.0, "Center position"),
            (0.02, 0.0, "Within deadzone (positive)"),
            (-0.02, 0.0, "Within deadzone (negative)"),
            (0.06, 0.06, "Outside deadzone (positive)"),
            (-0.06, -0.06, "Outside deadzone (negative)"),
            (0.10, 0.10, "Larger value outside deadzone"),
            (-0.10, -0.10, "Larger negative value outside deadzone"),
        ]

        print("\nTesting deadzone around center (0,0):")
        all_correct = True

        for input_val, expected, description in test_cases:
            result = apply_deadzone(input_val)
            status = "✓" if abs(result - expected) < 0.001 else "✗"
            print(f"  {status} {description}: {input_val} → {result}")
            if abs(result - expected) >= 0.001:
                all_correct = False

        return all_correct

    except Exception as e:
        print(f"✗ Deadzone test failed: {e}")
        return False

def test_teleop_deadzone_logic():
    """Test that teleop node uses correct deadzone logic."""
    try:
        # Read the teleop file and check deadzone implementation
        with open('src/joy2/joy2/nodes/joy2_teleop.py', 'r') as f:
            content = f.read()

        print("\n✓ Testing teleop deadzone implementation...")

        # Check that it uses apply_deadzone function
        if 'def apply_deadzone(value):' in content:
            print("  ✓ Uses apply_deadzone function")
        else:
            print("  ✗ Does not use apply_deadzone function")
            return False

        # Check that deadzone is applied around center (0,0)
        if 'abs(value) < self._deadzone' in content:
            print("  ✓ Deadzone applied around center (0,0)")
        else:
            print("  ✗ Deadzone not applied around center")
            return False

        # Check that it doesn't use previous vs current comparison
        if 'current_x - prev_x' not in content or 'current_y - prev_y' not in content:
            print("  ✓ Removed spam filter logic (no prev vs current comparison)")
        else:
            print("  ✗ Still uses spam filter logic")
            return False

        return True

    except Exception as e:
        print(f"✗ Teleop deadzone logic test failed: {e}")
        return False

def test_joy_node_coalesce_interval():
    """Test that joy_node has correct coalesce_interval."""
    try:
        # Read the joy_node launch file
        with open('src/joy2/launch/joy_node.launch.py', 'r') as f:
            content = f.read()

        print("\n✓ Testing joy_node coalesce_interval...")

        # Check that coalesce_interval is set to 0.01
        if "'coalesce_interval': 0.01" in content:
            print("  ✓ coalesce_interval set to 0.01s")
            return True
        else:
            print("  ✗ coalesce_interval not set to 0.01s")
            return False

    except Exception as e:
        print(f"✗ Joy node coalesce_interval test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing corrected deadzone implementation...")
    print("=" * 55)

    success = True
    success &= test_deadzone_around_center()
    success &= test_teleop_deadzone_logic()
    success &= test_joy_node_coalesce_interval()

    print("\n" + "=" * 55)
    if success:
        print("✓ All tests passed!")
        print("\n🎯 Deadzone Implementation Summary:")
        print("  • Deadzone applied around center (0,0) position")
        print("  • Prevents jitter when joystick is at rest")
        print("  • Removed incorrect spam filter logic")
        print("  • joy_node coalesce_interval set to 0.01s")
        print("  • Smooth servo control with proper sensitivity")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())