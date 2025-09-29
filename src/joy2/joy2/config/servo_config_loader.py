import yaml
import os
from typing import Dict, Any, Optional


class ServoConfigLoader:
    """
    Loads and manages servo configuration from YAML file.
    Supports both continuous and positional servos with string IDs.
    """

    def __init__(self, config_path: str):
        """
        Initialize the servo configuration loader.

        Args:
            config_path: Path to the servo configuration YAML file
        """
        self.config_path = config_path
        self._config = None
        self._servos = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as file:
                self._config = yaml.safe_load(file)

            if self._config is None:
                raise ValueError("Configuration file is empty or invalid")

            # Validate required structure
            if 'ros__parameters' not in self._config:
                raise ValueError("Configuration must contain 'ros__parameters' section")

            ros_params = self._config['ros__parameters']

            # Validate required parameters
            if 'pca_address' not in ros_params:
                raise ValueError("Configuration must specify 'pca_address'")
            if 'servo_frequency' not in ros_params:
                raise ValueError("Configuration must specify 'servo_frequency'")
            if 'servos' not in ros_params:
                raise ValueError("Configuration must contain 'servos' section")

            # Build servo lookup dictionary
            self._build_servo_lookup()

        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration: {e}")

    def _build_servo_lookup(self) -> None:
        """Build lookup dictionary for all servos."""
        servos_config = self._config['ros__parameters']['servos']

        for servo_type in ['continuous', 'positional']:
            if servo_type in servos_config:
                for servo_id, servo_config in servos_config[servo_type].items():
                    if not isinstance(servo_config, dict):
                        raise ValueError(f"Invalid configuration for {servo_type} servo '{servo_id}'")

                    # Validate required fields based on servo type
                    if servo_type == 'continuous':
                        required_fields = ['channel', 'min_us', 'max_us', 'center_us', 'deadzone']
                    else:  # positional
                        required_fields = ['channel', 'min_angle', 'max_angle', 'default_angle',
                                         'min_us', 'max_us', 'center_us', 'deadzone']

                    for field in required_fields:
                        if field not in servo_config:
                            raise ValueError(f"Missing required field '{field}' for {servo_type} servo '{servo_id}'")

                    # Store servo config with type information
                    self._servos[servo_id] = {
                        'type': servo_type,
                        'config': servo_config
                    }

    def get_servo_config(self, servo_id: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific servo.

        Args:
            servo_id: String ID of the servo (e.g., 'c1', 'p1')

        Returns:
            Dictionary containing servo configuration, or None if not found
        """
        return self._servos.get(servo_id)

    def get_all_servo_ids(self) -> list:
        """Get list of all configured servo IDs."""
        return list(self._servos.keys())

    def get_continuous_servo_ids(self) -> list:
        """Get list of continuous servo IDs."""
        return [sid for sid, config in self._servos.items() if config['type'] == 'continuous']

    def get_positional_servo_ids(self) -> list:
        """Get list of positional servo IDs."""
        return [sid for sid, config in self._servos.items() if config['type'] == 'positional']

    def get_pca_address(self) -> int:
        """Get PCA9685 I2C address."""
        return int(self._config['ros__parameters']['pca_address'])

    def get_servo_frequency(self) -> float:
        """Get PWM frequency for servos."""
        return float(self._config['ros__parameters']['servo_frequency'])

    def is_continuous_servo(self, servo_id: str) -> bool:
        """Check if servo is continuous rotation type."""
        servo_config = self.get_servo_config(servo_id)
        return servo_config is not None and servo_config['type'] == 'continuous'

    def is_positional_servo(self, servo_id: str) -> bool:
        """Check if servo is positional type."""
        servo_config = self.get_servo_config(servo_id)
        return servo_config is not None and servo_config['type'] == 'positional'

    def validate_servo_id(self, servo_id: str) -> bool:
        """Check if servo ID is configured."""
        return servo_id in self._servos