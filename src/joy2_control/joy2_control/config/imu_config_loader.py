"""
IMU configuration loader for BNO080 sensor.

This module provides utilities to load and validate IMU configuration
from YAML files for the BNO080 sensor.
"""

import yaml
from typing import Dict, Any, List


class IMUConfigLoader:
    """
    Loader and validator for IMU configuration.
    
    Handles loading configuration from YAML files and provides
    type-safe access to configuration values with validation.
    """
    
    VALID_SENSOR_MODES = ['game_rv', 'rotation_vector', 'gyro_rv']
    VALID_I2C_ADDRESSES = [0x4A, 0x4B]
    MIN_UPDATE_RATE = 1.0
    MAX_UPDATE_RATE = 1000.0
    
    def __init__(self, config_file: str):
        """
        Initialize configuration loader.
        
        Args:
            config_file: Path to YAML configuration file
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid
        """
        self.config_file = config_file
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Returns:
            Configuration dictionary
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is malformed
        """
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Extract IMU configuration
            if 'imu' not in config or 'ros__parameters' not in config['imu']:
                raise ValueError("Config must have 'imu' -> 'ros__parameters' structure")
            
            return config['imu']['ros__parameters']
        
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
    
    def _validate_config(self):
        """
        Validate configuration values.
        
        Raises:
            ValueError: If any configuration value is invalid
        """
        # Validate I2C settings
        i2c_address = self.get_i2c_address()
        if i2c_address not in self.VALID_I2C_ADDRESSES:
            raise ValueError(f"Invalid I2C address: 0x{i2c_address:02X}. "
                           f"Must be one of {[hex(a) for a in self.VALID_I2C_ADDRESSES]}")
        
        i2c_bus = self.get_i2c_bus()
        if i2c_bus < 0 or i2c_bus > 10:
            raise ValueError(f"Invalid I2C bus: {i2c_bus}. Must be 0-10")
        
        # Validate sensor mode
        sensor_mode = self.get_sensor_mode()
        if sensor_mode not in self.VALID_SENSOR_MODES:
            raise ValueError(f"Invalid sensor mode: {sensor_mode}. "
                           f"Must be one of {self.VALID_SENSOR_MODES}")
        
        # Validate update rate
        update_rate = self.get_update_rate()
        if update_rate < self.MIN_UPDATE_RATE or update_rate > self.MAX_UPDATE_RATE:
            raise ValueError(f"Invalid update rate: {update_rate} Hz. "
                           f"Must be between {self.MIN_UPDATE_RATE} and {self.MAX_UPDATE_RATE}")
        
        # Validate covariance matrices
        for matrix_name in ['orientation_covariance', 'angular_velocity_covariance', 
                           'linear_acceleration_covariance']:
            matrix = self.config.get(matrix_name, [])
            if len(matrix) != 9:
                raise ValueError(f"{matrix_name} must have exactly 9 elements (3x3 matrix)")
    
    def get_i2c_address(self) -> int:
        """Get I2C address (default 0x4B)."""
        return self.config.get('i2c_address', 0x4B)
    
    def get_i2c_bus(self) -> int:
        """Get I2C bus number (default 1)."""
        return self.config.get('i2c_bus', 1)
    
    def get_sensor_mode(self) -> str:
        """Get sensor mode (default 'game_rv')."""
        return self.config.get('sensor_mode', 'game_rv')
    
    def get_update_rate(self) -> float:
        """Get update rate in Hz (default 30.0)."""
        return float(self.config.get('update_rate_hz', 30.0))
    
    def get_frame_id(self) -> str:
        """Get TF frame ID (default 'imu_link')."""
        return self.config.get('frame_id', 'imu_link')
    
    def get_timeout_ms(self) -> int:
        """Get read timeout in milliseconds (default 100)."""
        return int(self.config.get('timeout_ms', 100))
    
    def is_debug_enabled(self) -> bool:
        """Check if debug logging is enabled (default False)."""
        return bool(self.config.get('debug', False))
    
    def get_calibration_config(self) -> Dict[str, bool]:
        """
        Get calibration configuration.
        
        Returns:
            Dictionary with calibration settings
        """
        calib = self.config.get('calibration', {})
        return {
            'auto_calibrate': calib.get('auto_calibrate', True),
            'accel_calibration': calib.get('accel_calibration', True),
            'gyro_calibration': calib.get('gyro_calibration', True),
            'mag_calibration': calib.get('mag_calibration', True),
            'save_calibration': calib.get('save_calibration', False),
        }
    
    def should_publish_raw_data(self) -> bool:
        """Check if raw sensor data should be published (default False)."""
        return bool(self.config.get('publish_raw_data', False))
    
    def should_publish_gravity(self) -> bool:
        """Check if gravity vector should be published separately (default False)."""
        return bool(self.config.get('publish_gravity', False))
    
    def should_publish_mag(self) -> bool:
        """Check if magnetometer data should be published (default False)."""
        return bool(self.config.get('publish_mag', False))
    
    def get_orientation_covariance(self) -> List[float]:
        """Get orientation covariance matrix (3x3 in row-major order)."""
        default = [0.01, 0.0, 0.0,
                   0.0, 0.01, 0.0,
                   0.0, 0.0, 0.01]
        return self.config.get('orientation_covariance', default)
    
    def get_angular_velocity_covariance(self) -> List[float]:
        """Get angular velocity covariance matrix (3x3 in row-major order)."""
        default = [0.001, 0.0, 0.0,
                   0.0, 0.001, 0.0,
                   0.0, 0.0, 0.001]
        return self.config.get('angular_velocity_covariance', default)
    
    def get_linear_acceleration_covariance(self) -> List[float]:
        """Get linear acceleration covariance matrix (3x3 in row-major order)."""
        default = [0.01, 0.0, 0.0,
                   0.0, 0.01, 0.0,
                   0.0, 0.0, 0.01]
        return self.config.get('linear_acceleration_covariance', default)
    
    def get_covariance_scale(self) -> Dict[str, float]:
        """
        Get covariance scaling factors based on accuracy status.
        
        Returns:
            Dictionary mapping accuracy level to scale factor
        """
        scale = self.config.get('covariance_scale', {})
        return {
            'unreliable': float(scale.get('unreliable', 10.0)),
            'low': float(scale.get('low', 5.0)),
            'medium': float(scale.get('medium', 2.0)),
            'high': float(scale.get('high', 1.0)),
        }
    
    def use_magnetometer(self) -> bool:
        """
        Determine if magnetometer should be used based on sensor mode.
        
        Returns:
            True if sensor_mode is 'rotation_vector', False for 'game_rv' or 'gyro_rv'
        """
        return self.get_sensor_mode() == 'rotation_vector'
    
    def get_all_config(self) -> Dict[str, Any]:
        """
        Get the complete configuration dictionary.
        
        Returns:
            Complete configuration
        """
        return self.config.copy()