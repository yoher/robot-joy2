"""
Sensor Hub Transport Protocol (SHTP) implementation for BNO080.

This module implements the SHTP protocol used by the BNO080 IMU sensor
for communication over I2C. SHTP provides a packetized communication
layer with support for multiple channels and packet fragmentation.

Reference: BNO080 Datasheet section 1.4.1 (SHTP)
"""

import smbus2 as smbus
import struct
import time
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class SHTPHeader:
    """SHTP packet header (4 bytes)."""
    length: int          # Bits 14:0 - Total packet length including header
    continuation: bool   # Bit 15 - Continuation of previous packet
    channel: int         # Channel number (0-5)
    sequence: int        # Sequence number


class SHTPChannel:
    """SHTP channel numbers."""
    COMMAND = 0          # SHTP command channel
    EXECUTABLE = 1       # Executable commands (reset, sleep, on)
    CONTROL = 2          # Sensor hub control channel
    INPUT_REPORTS = 3    # Input sensor reports (non-wake)
    WAKE_REPORTS = 4     # Wake input sensor reports
    GYRO_ROTATION = 5    # Gyro rotation vector


class SHTPProtocol:
    """
    SHTP (Sensor Hub Transport Protocol) handler for BNO080.
    
    Manages low-level I2C communication with proper SHTP framing,
    header parsing, and channel routing.
    """
    
    # SHTP constants
    MAX_PACKET_SIZE = 32768  # Maximum cargo size (15-bit length field)
    HEADER_SIZE = 4          # SHTP header is always 4 bytes
    
    def __init__(self, i2c_address: int = 0x4B, i2c_bus: int = 1, debug: bool = False):
        """
        Initialize SHTP protocol handler.
        
        Args:
            i2c_address: I2C address of BNO080 (0x4A or 0x4B)
            i2c_bus: I2C bus number (default 1 for Raspberry Pi)
            debug: Enable debug logging
        """
        self.i2c_address = i2c_address
        self.i2c_bus = i2c_bus
        self.debug = debug
        
        # Initialize I2C bus
        try:
            self.bus = smbus.SMBus(i2c_bus)
            if self.debug:
                print(f"[SHTP] Initialized I2C bus {i2c_bus} at address 0x{i2c_address:02X}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize I2C bus {i2c_bus}: {e}")
        
        # Sequence numbers per channel (transmit direction)
        self.tx_sequence = [0] * 6
        
        # Receive buffer for fragmented packets
        self.rx_buffer = bytearray()
        self.rx_expected_length = 0
    
    def _log(self, message: str):
        """Log debug message if debug is enabled."""
        if self.debug:
            print(f"[SHTP] {message}")
    
    def _parse_header(self, header_bytes: bytes) -> SHTPHeader:
        """
        Parse SHTP header from 4 bytes.
        
        Args:
            header_bytes: 4-byte header
            
        Returns:
            Parsed SHTPHeader object
        """
        if len(header_bytes) != 4:
            raise ValueError(f"Header must be 4 bytes, got {len(header_bytes)}")
        
        # Parse header: [length_lsb, length_msb, channel, sequence]
        length_raw = struct.unpack('<H', header_bytes[0:2])[0]
        
        # Bit 15 is continuation flag
        continuation = bool(length_raw & 0x8000)
        # Bits 14:0 are length
        length = length_raw & 0x7FFF
        
        channel = header_bytes[2]
        sequence = header_bytes[3]
        
        return SHTPHeader(length, continuation, channel, sequence)
    
    def _build_header(self, channel: int, payload_length: int, continuation: bool = False) -> bytes:
        """
        Build SHTP header bytes.
        
        Args:
            channel: Channel number (0-5)
            payload_length: Length of payload (will add header size)
            continuation: True if this is a continuation packet
            
        Returns:
            4-byte header
        """
        # Total length includes header (4 bytes) + payload
        total_length = self.HEADER_SIZE + payload_length
        
        if total_length > self.MAX_PACKET_SIZE:
            raise ValueError(f"Packet too large: {total_length} > {self.MAX_PACKET_SIZE}")
        
        # Set continuation bit if needed
        length_field = total_length
        if continuation:
            length_field |= 0x8000
        
        # Get and increment sequence number for this channel
        sequence = self.tx_sequence[channel]
        self.tx_sequence[channel] = (sequence + 1) & 0xFF
        
        # Pack header: [length_lsb, length_msb, channel, sequence]
        header = struct.pack('<HBB', length_field, channel, sequence)
        
        return header
    
    def read_packet(self, timeout_ms: int = 100) -> Optional[Tuple[int, bytes]]:
        """
        Read an SHTP packet from the BNO080.
        
        The BNO080 sends header + payload in ONE I2C transaction.
        We must read the complete packet length indicated in the header.
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Tuple of (channel, payload_bytes) or None if no data available
        """
        try:
            from smbus2 import i2c_msg
            
            # Strategy: Read entire packet in one transaction based on length from header
            # First peek at header (4 bytes) to get packet length
            header_peek = i2c_msg.read(self.i2c_address, 4)
            try:
                self.bus.i2c_rdwr(header_peek)
            except OSError:
                # No data available
                return None
            
            header_bytes = bytes(header_peek)
            header = self._parse_header(header_bytes)
            
            # If length is 0 or 0xFFFF, no data available
            if header.length == 0 or header.length == 0xFFFF:
                return None
            
            self._log(f"Received header: len={header.length}, ch={header.channel}, "
                     f"seq={header.sequence}, cont={header.continuation}")
            
            # Now read the full packet (we already read 4 bytes, need to read the rest)
            payload_length = header.length - self.HEADER_SIZE
            
            if payload_length < 0:
                return None
            
            # Read the payload
            if payload_length > 0:
                payload_msg = i2c_msg.read(self.i2c_address, payload_length)
                try:
                    self.bus.i2c_rdwr(payload_msg)
                    payload = bytes(payload_msg)
                except OSError:
                    self._log("Failed to read payload")
                    return None
            else:
                payload = bytes()
            
            # Skip continuation packets - they're part of fragmented advertisement
            # We're mainly interested in complete packets for sensor data
            if header.continuation:
                # Skip continuation packets during initialization
                return None
            
            # Return complete packet
            return (header.channel, payload)
                    
        except OSError:
            # I2C error - normal when no data available
            return None
        except Exception as e:
            self._log(f"Error reading packet: {e}")
            return None
                    
        except OSError as e:
            # I2C read error (device not ready, etc.)
            # This is normal when no data is available
            return None
        except Exception as e:
            self._log(f"Error reading packet: {e}")
            return None
    
    def write_packet(self, channel: int, payload: bytes) -> bool:
        """
        Write an SHTP packet to the BNO080.
        
        Args:
            channel: SHTP channel number (0-5)
            payload: Payload bytes to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from smbus2 import i2c_msg
            
            # Build header
            header = self._build_header(channel, len(payload))
            
            # Combine header and payload
            packet = header + payload
            
            self._log(f"Sending packet: ch={channel}, len={len(packet)} bytes")
            
            # Use i2c_msg for proper I2C write without register addressing
            write_msg = i2c_msg.write(self.i2c_address, list(packet))
            self.bus.i2c_rdwr(write_msg)
            
            return True
            
        except OSError as e:
            self._log(f"I2C write error: {e}")
            return False
        except Exception as e:
            self._log(f"Error writing packet: {e}")
            raise
    
    def wait_for_packet(self, channel: Optional[int] = None, 
                       timeout_ms: int = 1000) -> Optional[Tuple[int, bytes]]:
        """
        Wait for a packet on a specific channel (or any channel).
        
        Args:
            channel: Expected channel number, or None for any channel
            timeout_ms: Maximum time to wait in milliseconds
            
        Returns:
            Tuple of (channel, payload_bytes) or None if timeout
        """
        start_time = time.time()
        timeout_sec = timeout_ms / 1000.0
        
        while (time.time() - start_time) < timeout_sec:
            packet = self.read_packet()
            
            if packet is not None:
                recv_channel, payload = packet
                
                # Check if it's the channel we're waiting for
                if channel is None or recv_channel == channel:
                    return packet
            
            # Small delay to avoid busy-waiting
            time.sleep(0.001)
        
        return None
    
    def flush_input(self):
        """Flush any pending input packets."""
        while self.read_packet(timeout_ms=10) is not None:
            pass
    
    def close(self):
        """Close the I2C bus connection."""
        try:
            if hasattr(self, 'bus') and self.bus is not None:
                self.bus.close()
                self._log("I2C bus closed")
        except Exception as e:
            self._log(f"Error closing I2C bus: {e}")