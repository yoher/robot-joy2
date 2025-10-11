"""
BNO080 9-axis IMU sensor driver.

This module provides a high-level interface to the BNO080 IMU sensor,
handling sensor initialization, configuration, data reading, and calibration.

The BNO080 integrates a triaxial accelerometer, gyroscope, and magnetometer
with sensor fusion algorithms to provide orientation data.

Reference: BNO080 Datasheet v1.3
"""

import struct
import time
import math
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass
from enum import IntEnum

from .shtp import SHTPProtocol, SHTPChannel


class ReportID(IntEnum):
    """BNO080 sensor report IDs."""
    ACCELEROMETER = 0x01
    GYROSCOPE_CALIBRATED = 0x02
    MAGNETIC_FIELD_CALIBRATED = 0x03
    LINEAR_ACCELERATION = 0x04
    ROTATION_VECTOR = 0x05
    GRAVITY = 0x08
    GAME_ROTATION_VECTOR = 0x08
    GYROSCOPE_UNCALIBRATED = 0x07
    GEOMAGNETIC_ROTATION_VECTOR = 0x09
    GYRO_INTEGRATED_RV = 0x2A
    
    # Control reports
    COMMAND_RESPONSE = 0xF1
    GET_FEATURE_RESPONSE = 0xFC
    PRODUCT_ID_RESPONSE = 0xF8
    TIMEBASE_REFERENCE = 0xFB


class CommandID(IntEnum):
    """BNO080 command IDs."""
    REPORT_ERRORS = 0x01
    COUNTER_COMMANDS = 0x02
    TARE = 0x03
    INITIALIZE = 0x04
    DCD = 0x06
    ME_CALIBRATE = 0x07
    DCD_PERIOD_SAVE = 0x09
    OSCILLATOR = 0x0A
    CLEAR_DCD = 0x0B


@dataclass
class IMUData:
    """Container for IMU sensor data."""
    # Orientation (quaternion)
    quat_w: float = 0.0
    quat_x: float = 0.0
    quat_y: float = 0.0
    quat_z: float = 0.0
    quat_accuracy: float = 0.0  # Accuracy estimate (rad)
    
    # Angular velocity (rad/s)
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0
    
    # Linear acceleration (m/s²)
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 0.0
    
    # Gravity vector (m/s²)
    gravity_x: float = 0.0
    gravity_y: float = 0.0
    gravity_z: float = 0.0
    
    # Status
    status: int = 0  # Bits 1:0 = accuracy (0=unreliable, 1=low, 2=med, 3=high)
    timestamp: float = 0.0  # Timestamp in seconds
    delay_us: int = 0  # Delay from sensor interrupt in microseconds


class BNO080:
    """
    BNO080 9-axis IMU sensor driver.
    
    Provides high-level interface for:
    - Sensor initialization and configuration
    - Reading orientation (rotation vectors)
    - Reading calibrated sensor data
    - Managing calibration
    """
    
    # Sensor report sizes (bytes after report ID)
    REPORT_SIZES = {
        ReportID.ACCELEROMETER: 9,
        ReportID.GYROSCOPE_CALIBRATED: 9,
        ReportID.MAGNETIC_FIELD_CALIBRATED: 9,
        ReportID.LINEAR_ACCELERATION: 9,
        ReportID.ROTATION_VECTOR: 13,
        ReportID.GAME_ROTATION_VECTOR: 11,
        ReportID.GRAVITY: 9,
        ReportID.GYRO_INTEGRATED_RV: 13,
    }
    
    def __init__(self, i2c_address: int = 0x4B, i2c_bus: int = 1, debug: bool = False):
        """
        Initialize BNO080 driver.
        
        Args:
            i2c_address: I2C address (0x4A or 0x4B, default 0x4B)
            i2c_bus: I2C bus number (default 1)
            debug: Enable debug logging
        """
        self.debug = debug
        self.shtp = SHTPProtocol(i2c_address, i2c_bus, debug)
        
        # Current sensor data
        self.imu_data = IMUData()
        
        # Calibration status per sensor
        self.calibration_status = {
            'accel': 0,
            'gyro': 0,
            'mag': 0,
        }
        
        # Product ID info
        self.product_id = {}
        
        self._log("BNO080 driver initialized")
    
    def _log(self, message: str):
        """Log debug message if debug is enabled."""
        if self.debug:
            print(f"[BNO080] {message}")
    
    def initialize(self) -> bool:
        """
        Initialize the BNO080 sensor.
        
        Performs:
        1. Wait for initial SHTP advertisements and reset messages
        2. Request and verify product ID
        
        Returns:
            True if initialization successful, False otherwise
        """
        self._log("Initializing BNO080...")
        
        # Wait for sensor to be ready after power-on/reset
        # BNO080 sends advertisement packets automatically
        time.sleep(0.5)
        
        # Clear all pending packets (advertisements, reset messages, etc.)
        # We don't need to parse them - just consume them
        self._log("Consuming initial packets...")
        packets_read = 0
        reset_seen = False
        
        for i in range(100):  # Read up to 100 packets during init
            packet = self.shtp.read_packet(timeout_ms=10)
            if packet is not None:
                channel, data = packet
                packets_read += 1
                
                # Check for executable reset complete (channel 1, report 0x01)
                if channel == SHTPChannel.EXECUTABLE and len(data) > 0 and data[0] == 0x01:
                    self._log("Received executable reset complete")
                    reset_seen = True
                    break
            else:
                # No more packets available
                if packets_read > 0:
                    break
        
        self._log(f"Consumed {packets_read} initialization packets")
        
        # Wait a bit for sensor to stabilize
        time.sleep(0.2)
        
        # Now request product ID
        self._log("Requesting product ID...")
        if not self._request_product_id():
            self._log("Failed to get product ID")
            return False
        
        self._log(f"BNO080 initialized: SW v{self.product_id.get('sw_major', 0)}."
                 f"{self.product_id.get('sw_minor', 0)}")
        
        return True
    
    def _request_product_id(self) -> bool:
        """
        Request product ID from BNO080.
        
        Returns:
            True if successful, False otherwise
        """
        # Build product ID request: Report ID 0xF9 + reserved byte
        payload = bytes([0xF9, 0x00])  # Product ID Request
        
        # Send on control channel
        self._log("Sending product ID request...")
        if not self.shtp.write_packet(SHTPChannel.CONTROL, payload):
            self._log("Failed to send product ID request")
            return False
        
        # Give device time to process command
        time.sleep(0.05)
        
        # Wait for response on control channel
        self._log("Waiting for product ID response...")
        for attempt in range(10):
            packet = self.shtp.read_packet(timeout_ms=100)
            if packet is not None:
                channel, data = packet
                self._log(f"Received packet: ch={channel}, len={len(data)}, "
                         f"report_id=0x{data[0]:02X if len(data) > 0 else 0}")
                
                # Check for product ID response on control channel
                if channel == SHTPChannel.CONTROL and len(data) >= 16 and data[0] == ReportID.PRODUCT_ID_RESPONSE:
                    # Parse product ID response
                    self.product_id = {
                        'reset_cause': data[1],
                        'sw_major': data[2],
                        'sw_minor': data[3],
                        'sw_part_number': struct.unpack('<I', data[4:8])[0],
                        'sw_build_number': struct.unpack('<I', data[8:12])[0],
                        'sw_version_patch': struct.unpack('<H', data[12:14])[0],
                    }
                    self._log("Successfully received product ID")
                    return True
            
            time.sleep(0.05)
        
        self._log("Timeout waiting for product ID response")
        return False
    
    def enable_rotation_vector(self, rate_hz: float = 30.0, 
                              use_magnetometer: bool = False) -> bool:
        """
        Enable rotation vector reporting.
        
        Args:
            rate_hz: Desired update rate in Hz (10-400 Hz)
            use_magnetometer: True for full 9-axis (Rotation Vector),
                            False for 6-axis (Game Rotation Vector)
        
        Returns:
            True if successful
        """
        if use_magnetometer:
            report_id = ReportID.ROTATION_VECTOR
            self._log(f"Enabling Rotation Vector (9-axis) at {rate_hz} Hz")
        else:
            report_id = ReportID.GAME_ROTATION_VECTOR
            self._log(f"Enabling Game Rotation Vector (6-axis) at {rate_hz} Hz")
        
        return self._set_feature(report_id, rate_hz)
    
    def enable_gyroscope(self, rate_hz: float = 100.0) -> bool:
        """Enable calibrated gyroscope reporting."""
        self._log(f"Enabling calibrated gyroscope at {rate_hz} Hz")
        return self._set_feature(ReportID.GYROSCOPE_CALIBRATED, rate_hz)
    
    def enable_accelerometer(self, rate_hz: float = 100.0) -> bool:
        """Enable calibrated accelerometer reporting."""
        self._log(f"Enabling calibrated accelerometer at {rate_hz} Hz")
        return self._set_feature(ReportID.ACCELEROMETER, rate_hz)
    
    def enable_linear_acceleration(self, rate_hz: float = 100.0) -> bool:
        """Enable linear acceleration (gravity removed) reporting."""
        self._log(f"Enabling linear acceleration at {rate_hz} Hz")
        return self._set_feature(ReportID.LINEAR_ACCELERATION, rate_hz)
    
    def enable_gravity(self, rate_hz: float = 100.0) -> bool:
        """Enable gravity vector reporting."""
        self._log(f"Enabling gravity vector at {rate_hz} Hz")
        return self._set_feature(ReportID.GRAVITY, rate_hz)
    
    def _set_feature(self, report_id: int, rate_hz: float, 
                    change_sensitivity: int = 0, batch_interval_us: int = 0) -> bool:
        """
        Send Set Feature command to enable a sensor.
        
        Args:
            report_id: Report ID of sensor to enable
            rate_hz: Desired report rate in Hz
            change_sensitivity: Change sensitivity (0 = always report)
            batch_interval_us: Batching interval in microseconds (0 = no batching)
        
        Returns:
            True if successful
        """
        # Convert rate to microseconds
        report_interval_us = int(1000000.0 / rate_hz)
        
        # Build Set Feature command (Report ID 0xFD)
        payload = bytearray([
            0xFD,  # Set Feature command
            report_id,  # Feature Report ID
            0x00,  # Feature flags (0 = defaults)
            struct.pack('<H', change_sensitivity)[0],  # Change sensitivity LSB
            struct.pack('<H', change_sensitivity)[1],  # Change sensitivity MSB
            struct.pack('<I', report_interval_us)[0],  # Report interval LSB
            struct.pack('<I', report_interval_us)[1],
            struct.pack('<I', report_interval_us)[2],
            struct.pack('<I', report_interval_us)[3],  # Report interval MSB
            struct.pack('<I', batch_interval_us)[0],  # Batch interval LSB
            struct.pack('<I', batch_interval_us)[1],
            struct.pack('<I', batch_interval_us)[2],
            struct.pack('<I', batch_interval_us)[3],  # Batch interval MSB
            0x00, 0x00, 0x00, 0x00,  # Sensor-specific config (unused)
        ])
        
        # Send on control channel
        return self.shtp.write_packet(SHTPChannel.CONTROL, bytes(payload))
    
    def calibrate(self, accel: bool = True, gyro: bool = True, mag: bool = True) -> bool:
        """
        Configure dynamic calibration for sensors.
        
        Args:
            accel: Enable accelerometer calibration
            gyro: Enable gyroscope calibration
            mag: Enable magnetometer calibration
        
        Returns:
            True if successful
        """
        # Build ME Calibrate command (Command ID 0x07)
        # Subcommand: 0 = Configure, 1 = Get Status
        sensors = 0
        if accel:
            sensors |= 0x01
        if gyro:
            sensors |= 0x02
        if mag:
            sensors |= 0x04
        
        payload = bytearray([
            0xF2,  # Command Request
            0x00,  # Sequence number
            CommandID.ME_CALIBRATE,  # ME Calibrate command
            0x00,  # Subcommand: Configure
            sensors,  # Which sensors to calibrate
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Padding
        ])
        
        self._log(f"Configuring calibration: accel={accel}, gyro={gyro}, mag={mag}")
        return self.shtp.write_packet(SHTPChannel.CONTROL, bytes(payload))
    
    def read_sensor_data(self, timeout_ms: int = 100) -> Optional[IMUData]:
        """
        Read sensor data from BNO080.
        
        This method reads available sensor reports and updates the internal
        IMU data structure.
        
        Args:
            timeout_ms: Maximum time to wait for data
        
        Returns:
            IMUData object if new data available, None otherwise
        """
        # Read packet from input reports channel
        packet = self.shtp.wait_for_packet(SHTPChannel.INPUT_REPORTS, timeout_ms=timeout_ms)
        
        if packet is None:
            return None
        
        channel, data = packet
        
        if len(data) < 1:
            return None
        
        # Parse sensor reports in the packet
        offset = 0
        data_updated = False
        
        while offset < len(data):
            report_id = data[offset]
            
            # Timebase reference
            if report_id == ReportID.TIMEBASE_REFERENCE:
                if len(data) - offset >= 5:
                    # Parse timebase reference
                    base_delta = struct.unpack('<i', data[offset+1:offset+5])[0]
                    # Store for timestamp calculation (100 μs ticks)
                    self.imu_data.delay_us = base_delta * 100
                    offset += 5
                else:
                    break
            
            # Rotation Vector (9-axis)
            elif report_id == ReportID.ROTATION_VECTOR:
                if len(data) - offset >= 14:
                    self._parse_rotation_vector(data[offset:offset+14])
                    data_updated = True
                    offset += 14
                else:
                    break
            
            # Game Rotation Vector (6-axis)
            elif report_id == ReportID.GAME_ROTATION_VECTOR:
                if len(data) - offset >= 12:
                    self._parse_game_rotation_vector(data[offset:offset+12])
                    data_updated = True
                    offset += 12
                else:
                    break
            
            # Calibrated Gyroscope
            elif report_id == ReportID.GYROSCOPE_CALIBRATED:
                if len(data) - offset >= 10:
                    self._parse_gyroscope(data[offset:offset+10])
                    data_updated = True
                    offset += 10
                else:
                    break
            
            # Linear Acceleration
            elif report_id == ReportID.LINEAR_ACCELERATION:
                if len(data) - offset >= 10:
                    self._parse_linear_acceleration(data[offset:offset+10])
                    data_updated = True
                    offset += 10
                else:
                    break
            
            # Gravity
            elif report_id == ReportID.GRAVITY:
                if len(data) - offset >= 10:
                    self._parse_gravity(data[offset:offset+10])
                    data_updated = True
                    offset += 10
                else:
                    break
            
            else:
                # Unknown report, try to skip
                self._log(f"Unknown report ID: 0x{report_id:02X}")
                break
        
        if data_updated:
            return self.imu_data
        else:
            return None
    
    def _parse_rotation_vector(self, data: bytes):
        """Parse Rotation Vector report (9-axis with magnetometer)."""
        # [0]: Report ID
        # [1]: Sequence number
        # [2]: Status
        # [3]: Delay
        # [4-5]: i (Q14)
        # [6-7]: j (Q14)
        # [8-9]: k (Q14)
        # [10-11]: real (Q14)
        # [12-13]: Accuracy estimate (Q12)
        
        sequence = data[1]
        self.imu_data.status = data[2]
        delay = (data[2] >> 2) | (data[3] << 6)  # 14-bit delay field
        
        # Parse quaternion (Q14 format: divide by 16384.0)
        i = struct.unpack('<h', data[4:6])[0] / 16384.0
        j = struct.unpack('<h', data[6:8])[0] / 16384.0
        k = struct.unpack('<h', data[8:10])[0] / 16384.0
        real = struct.unpack('<h', data[10:12])[0] / 16384.0
        
        # Accuracy estimate (Q12 format: divide by 4096.0)
        accuracy = struct.unpack('<h', data[12:14])[0] / 4096.0
        
        self.imu_data.quat_w = real
        self.imu_data.quat_x = i
        self.imu_data.quat_y = j
        self.imu_data.quat_z = k
        self.imu_data.quat_accuracy = accuracy
        self.imu_data.delay_us = delay * 100
    
    def _parse_game_rotation_vector(self, data: bytes):
        """Parse Game Rotation Vector report (6-axis without magnetometer)."""
        # Similar to rotation vector but no accuracy estimate
        sequence = data[1]
        self.imu_data.status = data[2]
        delay = (data[2] >> 2) | (data[3] << 6)
        
        # Parse quaternion (Q14)
        i = struct.unpack('<h', data[4:6])[0] / 16384.0
        j = struct.unpack('<h', data[6:8])[0] / 16384.0
        k = struct.unpack('<h', data[8:10])[0] / 16384.0
        real = struct.unpack('<h', data[10:12])[0] / 16384.0
        
        self.imu_data.quat_w = real
        self.imu_data.quat_x = i
        self.imu_data.quat_y = j
        self.imu_data.quat_z = k
        self.imu_data.delay_us = delay * 100
    
    def _parse_gyroscope(self, data: bytes):
        """Parse calibrated gyroscope report."""
        # [4-5]: X (Q9 rad/s)
        # [6-7]: Y (Q9)
        # [8-9]: Z (Q9)
        
        x = struct.unpack('<h', data[4:6])[0] / 512.0  # Q9
        y = struct.unpack('<h', data[6:8])[0] / 512.0
        z = struct.unpack('<h', data[8:10])[0] / 512.0
        
        self.imu_data.gyro_x = x
        self.imu_data.gyro_y = y
        self.imu_data.gyro_z = z
    
    def _parse_linear_acceleration(self, data: bytes):
        """Parse linear acceleration report (gravity removed)."""
        # [4-5]: X (Q8 m/s²)
        # [6-7]: Y (Q8)
        # [8-9]: Z (Q8)
        
        x = struct.unpack('<h', data[4:6])[0] / 256.0  # Q8
        y = struct.unpack('<h', data[6:8])[0] / 256.0
        z = struct.unpack('<h', data[8:10])[0] / 256.0
        
        self.imu_data.accel_x = x
        self.imu_data.accel_y = y
        self.imu_data.accel_z = z
    
    def _parse_gravity(self, data: bytes):
        """Parse gravity vector report."""
        # [4-5]: X (Q8 m/s²)
        # [6-7]: Y (Q8)
        # [8-9]: Z (Q8)
        
        x = struct.unpack('<h', data[4:6])[0] / 256.0  # Q8
        y = struct.unpack('<h', data[6:8])[0] / 256.0
        z = struct.unpack('<h', data[8:10])[0] / 256.0
        
        self.imu_data.gravity_x = x
        self.imu_data.gravity_y = y
        self.imu_data.gravity_z = z
    
    def get_accuracy(self) -> Tuple[str, int]:
        """
        Get current calibration accuracy status.
        
        Returns:
            Tuple of (status_string, status_code)
            Status code: 0=unreliable, 1=low, 2=medium, 3=high
        """
        status_code = self.imu_data.status & 0x03
        status_map = {
            0: "Unreliable",
            1: "Low",
            2: "Medium",
            3: "High"
        }
        return (status_map.get(status_code, "Unknown"), status_code)
    
    def close(self):
        """Close connection to BNO080."""
        self._log("Closing BNO080 connection")
        self.shtp.close()