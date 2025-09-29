import smbus2 as smbus
import time
import math


class PCA9685:
    __SUBADR1 = 0x02
    __SUBADR2 = 0x03
    __SUBADR3 = 0x04
    __MODE1 = 0x00
    __MODE2 = 0x01
    __PRESCALE = 0xFE
    __LED0_ON_L = 0x06
    __LED0_ON_H = 0x07
    __LED0_OFF_L = 0x08
    __LED0_OFF_H = 0x09
    __ALLLED_ON_L = 0xFA
    __ALLLED_ON_H = 0xFB
    __ALLLED_OFF_L = 0xFC
    __ALLLED_OFF_H = 0xFD

    # Values for the MODE1 register
    __RESTART = 0x80
    __SLEEP = 0x10
    __ALLCALL = 0x01
    __INVRT = 0x10
    __OUTDRV = 0x04

    def __init__(self, i2c_address: int = 0x60, debug: bool = False):
        """
        Minimal PCA9685 driver (12-bit PWM, I2C).
        Initializes device, sets all channels off, and configures 50Hz by default.
        """
        self._i2c_address = i2c_address
        self._debug = debug
        self._bus = smbus.SMBus(1)  # I2C bus 1 on Raspberry Pi

        # Reset and configure device: ALLCALL, totem-pole outputs, auto-increment
        self._write_byte_data(self.__MODE1, self.__ALLCALL)  # Respond to ALLCALL
        time.sleep(0.005)
        self._write_byte_data(self.__MODE2, self.__OUTDRV)  # Totem pole (push-pull)

        # Wake up (clear SLEEP), enable Auto-Increment (AI)
        oldmode = self._bus.read_byte_data(self._i2c_address, self.__MODE1)
        newmode = (oldmode & ~self.__SLEEP) | 0x20  # Clear sleep, set AI bit
        self._write_byte_data(self.__MODE1, newmode)
        time.sleep(0.005)

        # Ensure all channels are off initially
        self.set_all_pwm(0, 0)

        # Default to 50Hz for servos
        self.set_pwm_frequency(50)

    def _write_byte_data(self, reg, value):
        try:
            self._bus.write_byte_data(self._i2c_address, reg, value)
        except IOError:
            if self._debug:
                print(f"PCA9685: Failed to write to I2C address {self._i2c_address:#04x}")

    def set_pwm_frequency(self, frequency: int):
        """
        Set the PWM frequency for the PCA9685.
        Allowed range: 24..1526 Hz (per datasheet).
        """
        if frequency < 24 or frequency > 1526:
            raise ValueError("Frequency must be between 24Hz and 1526Hz")
        prescaleval = 25000000.0  # 25MHz
        prescaleval /= 4096.0  # 12-bit
        prescaleval /= float(frequency)
        prescaleval -= 1.0
        prescale = int(math.floor(prescaleval + 0.5))

        oldmode = self._bus.read_byte_data(self._i2c_address, self.__MODE1)
        newmode = (oldmode & 0x7F) | self.__SLEEP  # enter sleep to set prescale
        self._write_byte_data(self.__MODE1, newmode)
        self._write_byte_data(self.__PRESCALE, prescale)  # set the prescaler

        # Restore MODE1, ensure AI bit set for auto-increment
        restored = (oldmode | 0x20) & ~self.__SLEEP
        self._write_byte_data(self.__MODE1, restored)
        time.sleep(0.005)
        # Restart
        self._write_byte_data(self.__MODE1, restored | self.__RESTART)

    def set_pwm(self, channel: int, on: int = 0, off: int = 4096):
        """
        Sets a PWM value on a channel.
        on/off are 12-bit counters (0..4095). Off=4096 means fully OFF.
        """
        if channel < 0 or channel > 15:
            raise ValueError("Channel must be between 0 and 15 inclusive")
        on_l = on & 0xFF
        on_h = (on >> 8) & 0x0F
        off_l = off & 0xFF
        off_h = (off >> 8) & 0x0F
        base = self.__LED0_ON_L + 4 * channel
        try:
            self._bus.write_byte_data(self._i2c_address, base + 0, on_l)
            self._bus.write_byte_data(self._i2c_address, base + 1, on_h)
            self._bus.write_byte_data(self._i2c_address, base + 2, off_l)
            self._bus.write_byte_data(self._i2c_address, base + 3, off_h)
        except Exception as e:
            print(f"PCA9685: Error setting PWM on channel {channel}: {e}")

    def set_all_pwm(self, on: int = 0, off: int = 4096):
        """
        Sets all PWM channels to the same values.
        """
        on_l = on & 0xFF
        on_h = (on >> 8) & 0x0F
        off_l = off & 0xFF
        off_h = (off >> 8) & 0x0F
        try:
            self._bus.write_byte_data(self._i2c_address, self.__ALLLED_ON_L, on_l)
            self._bus.write_byte_data(self._i2c_address, self.__ALLLED_ON_H, on_h)
            self._bus.write_byte_data(self._i2c_address, self.__ALLLED_OFF_L, off_l)
            self._bus.write_byte_data(self._i2c_address, self.__ALLLED_OFF_H, off_h)
        except Exception as e:
            if self._debug:
                print(f"PCA9685: Failed to set all PWM: {e}")