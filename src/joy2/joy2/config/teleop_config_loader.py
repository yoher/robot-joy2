import yaml
import os
from typing import Dict, Any, Optional


class TeleopConfigLoader:
    """
    Loads and manages teleop control configuration from YAML file.
    Handles joystick mappings, button assignments, and modifier keys.
    """

    def __init__(self, config_path: str):
        """
        Initialize the teleop configuration loader.

        Args:
            config_path: Path to the teleop configuration YAML file
        """
        self.config_path = config_path
        self._config = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as file:
                self._config = yaml.safe_load(file)

            if self._config is None:
                raise ValueError("Configuration file is empty or invalid")

            # Validate required structure
            if 'teleop' not in self._config:
                raise ValueError("Configuration must contain 'teleop' section")

            teleop_config = self._config['teleop']

            if 'ros__parameters' not in teleop_config:
                raise ValueError("Configuration must contain 'ros__parameters' section")

        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration: {e}")

    def get_alt_button_index(self) -> int:
        """Get the Alt modifier button index (R1 = 7)."""
        return int(self._config['teleop']['ros__parameters']['alt_button_index'])

    def get_alt_button_name(self) -> str:
        """Get the Alt modifier button name."""
        return str(self._config['teleop']['ros__parameters']['alt_button_name'])

    def get_left_joystick_x_axis(self) -> int:
        """Get left joystick X axis index."""
        return int(self._config['teleop']['ros__parameters']['left_joystick']['x_axis'])

    def get_left_joystick_y_axis(self) -> int:
        """Get left joystick Y axis index."""
        return int(self._config['teleop']['ros__parameters']['left_joystick']['y_axis'])

    def get_right_joystick_x_axis(self) -> int:
        """Get right joystick X axis index."""
        return int(self._config['teleop']['ros__parameters']['right_joystick']['x_axis'])

    def get_right_joystick_y_axis(self) -> int:
        """Get right joystick Y axis index."""
        return int(self._config['teleop']['ros__parameters']['right_joystick']['y_axis'])

    def get_servo_mapping(self) -> Dict[str, str]:
        """Get servo control mappings."""
        return dict(self._config['teleop']['ros__parameters']['servo_controls'])

    def get_deadzone(self) -> float:
        """Get joystick deadzone value."""
        return float(self._config['teleop']['ros__parameters']['deadzone'])

    def get_angle_range(self) -> Dict[str, float]:
        """Get angle range for joystick conversion."""
        return dict(self._config['teleop']['ros__parameters']['angle_range'])

    def get_buzzer_button_index(self) -> int:
        """Get buzzer button index."""
        return int(self._config['teleop']['ros__parameters']['buzzer_button_index'])

    def get_buzzer_frequency(self) -> int:
        """Get buzzer frequency."""
        return int(self._config['teleop']['ros__parameters']['buzzer_frequency'])

    def get_buzzer_duration(self) -> int:
        """Get buzzer duration."""
        return int(self._config['teleop']['ros__parameters']['buzzer_duration'])

    def get_min_angle(self) -> float:
        """Get minimum angle for joystick conversion."""
        return float(self._config['teleop']['ros__parameters']['angle_range']['min'])

    def get_max_angle(self) -> float:
        """Get maximum angle for joystick conversion."""
        return float(self._config['teleop']['ros__parameters']['angle_range']['max'])