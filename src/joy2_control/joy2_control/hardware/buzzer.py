import pigpio
import time


class Buzzer:
    """
    Low-level buzzer driver using pigpio PWM.
    Provides simple tone on/off control; patterns are handled by a higher-level controller.
    """

    def __init__(self, gpio_pin: int = 27):
        self.pin = int(gpio_pin)
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Buzzer: pigpio not connected. Ensure 'sudo pigpiod' is running.")
        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.stop()

    def set_tone(self, frequency_hz: int, duty_cycle: int = 128):
        """
        Start a tone at 'frequency_hz' with duty cycle [0..255] (128 ~ 50%).
        """
        if frequency_hz <= 0:
            self.stop()
            return
        if duty_cycle < 0:
            duty_cycle = 0
        if duty_cycle > 255:
            duty_cycle = 255
        try:
            self.pi.set_PWM_frequency(self.pin, int(frequency_hz))
            self.pi.set_PWM_dutycycle(self.pin, int(duty_cycle))
        except Exception as e:
            print(f"Buzzer: error setting tone {frequency_hz}Hz: {e}")

    def high(self):
        """Set GPIO high for buzzer click."""
        try:
            self.pi.write(self.pin, 1)
        except Exception as e:
            print(f"Buzzer: high failed: {e}")

    def low(self):
        """Set GPIO low to silence buzzer."""
        try:
            self.pi.write(self.pin, 0)
        except Exception as e:
            print(f"Buzzer: low failed: {e}")

    def stop(self):
        try:
            self.pi.set_PWM_dutycycle(self.pin, 0)
            self.low()  # Ensure low for PWM mode too
        except Exception:
            pass

    def close(self):
        try:
            self.stop()
            if self.pi and self.pi.connected:
                self.pi.stop()
        except Exception:
            pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass