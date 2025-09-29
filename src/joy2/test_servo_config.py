#!/usr/bin/env python3
"""
Test script to verify servo configuration loading and servo node functionality.
"""

import sys
import os

# Add the joy2 package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'joy2'))

def test_config_loading():
    """Test loading the servo configuration."""
    try:
        from joy2.config.servo_config_loader import ServoConfigLoader

        config_file = 'src/joy2/config/servo_config.yaml'
        config_loader = ServoConfigLoader(config_file)

        print("✓ Configuration loaded successfully!")
        print(f"  PCA Address: 0x{config_loader.get_pca_address():02X}")
        print(f"  Servo Frequency: {config_loader.get_servo_frequency()} Hz")
        print(f"  All servo IDs: {config_loader.get_all_servo_ids()}")
        print(f"  Continuous servos: {config_loader.get_continuous_servo_ids()}")
        print(f"  Positional servos: {config_loader.get_positional_servo_ids()}")

        # Test individual servo configurations
        for servo_id in config_loader.get_all_servo_ids():
            config = config_loader.get_servo_config(servo_id)
            servo_type = config['type']
            servo_config = config['config']

            print(f"\n  Servo {servo_id} ({servo_type}):")
            print(f"    Channel: {servo_config['channel']}")

            if servo_type == 'continuous':
                print(f"    Min US: {servo_config['min_us']}")
                print(f"    Max US: {servo_config['max_us']}")
                print(f"    Center US: {servo_config['center_us']}")
                print(f"    Deadzone: {servo_config['deadzone']}")
            else:  # positional
                print(f"    Min Angle: {servo_config['min_angle']}")
                print(f"    Max Angle: {servo_config['max_angle']}")
                print(f"    Default Angle: {servo_config['default_angle']}")
                print(f"    Min US: {servo_config['min_us']}")
                print(f"    Max US: {servo_config['max_us']}")
                print(f"    Center US: {servo_config['center_us']}")
                print(f"    Deadzone: {servo_config['deadzone']}")

        return True

    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False

def test_servo_creation():
    """Test creating servo instances from configuration."""
    try:
        from joy2.config.servo_config_loader import ServoConfigLoader
        from joy2.hardware.pca9685 import PCA9685

        config_file = 'src/joy2/config/servo_config.yaml'
        config_loader = ServoConfigLoader(config_file)

        # Mock PCA9685 (without I2C) for testing
        class MockPCA:
            def set_pwm_frequency(self, freq):
                print(f"    Mock PCA: Set frequency to {freq} Hz")

        pca = MockPCA()

        print("\n✓ Testing servo creation from configuration:")

        for servo_id in config_loader.get_all_servo_ids():
            config = config_loader.get_servo_config(servo_id)
            servo_type = config['type']

            try:
                if servo_type == 'continuous':
                    from joy2.hardware.servo import ContinuousServo
                    servo = ContinuousServo.from_config(pca, servo_id, config['config'])
                    print(f"  ✓ Created continuous servo {servo_id}")
                else:  # positional
                    from joy2.hardware.servo import Servo
                    servo = Servo.from_config(pca, servo_id, config['config'])
                    print(f"  ✓ Created positional servo {servo_id}")

            except Exception as e:
                print(f"  ✗ Failed to create servo {servo_id}: {e}")
                return False

        return True

    except Exception as e:
        print(f"✗ Servo creation test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing servo configuration system...")
    print("=" * 50)

    success = True
    success &= test_config_loading()
    success &= test_servo_creation()

    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())