import time
from typing import Optional, Dict, Any


class Servo:
    def __init__(self, pca, channel: int):
        """
        Standard positional servo on a PCA9685 channel.

        Angle mapping assumes:
        - 0 deg  -> ~500 us
        - 180 deg-> ~2500 us
        - 50 Hz PWM period = 20000 us; 12-bit = 4096 ticks
        """
        if channel < 0 or channel > 15:
            raise ValueError("Channel must be between 0 and 15 inclusive")
        self.pca = pca
        self.channel = channel
        self.current_angle: int = 90  # neutral
        self.servo_id: Optional[str] = None  # For tracking servo ID

    @classmethod
    def from_config(cls, pca, servo_id: str, servo_config: Dict[str, Any]) -> 'Servo':
        """
        Create a positional servo from configuration.

        Args:
            pca: PCA9685 instance
            servo_id: String ID of the servo (e.g., 'p1')
            servo_config: Configuration dictionary for the servo

        Returns:
            Configured Servo instance
        """
        channel = servo_config['channel']

        # Create servo instance
        servo = cls(pca, channel)
        servo.servo_id = servo_id

        # Set initial angle from config
        default_angle = servo_config.get('default_angle', 90.0)
        servo.set_angle(int(default_angle))

        return servo

    def set_angle(self, angle: int) -> None:
        if angle < 0:
            angle = 0
        if angle > 180:
            angle = 180
        # 0..180 -> 500..2500 us
        microseconds = (angle * 11) + 500  # 0->500, 180->247... ~2500
        ticks = int(4096.0 * (microseconds / 20000.0))
        if ticks < 0:
            ticks = 0
        if ticks > 4095:
            ticks = 4095
        print(f"Servo ch={self.channel} angle={angle}deg -> {ticks} ticks")
        try:
            self.pca.set_pwm(self.channel, 0, ticks)
            self.current_angle = angle
        except Exception as e:
            print(f"Servo: error setting channel {self.channel}: {e}")


class ContinuousServo:
    def __init__(
        self,
        pca,
        channel: int,
        min_us: float = 1000.0,
        max_us: float = 2000.0,
        center_us: float = 1570.0,
        deadzone: float = 0.05,
    ):
        """
        Continuous-rotation (360°) servo control via PWM pulse width.

        Speed in [-1.0, 1.0]:
          - 0.0 ~ stop (pulse ~ center_us)
          - +1.0 ~ max_us
          - -1.0 ~ min_us
        """
        if channel < 0 or channel > 15:
            raise ValueError("Channel must be between 0 and 15 inclusive")
        if not (min_us < center_us < max_us):
            raise ValueError("Require min_us < center_us < max_us")
        self.pca = pca
        self.channel = channel
        self.min_us = float(min_us)
        self.max_us = float(max_us)
        self.center_us = float(center_us)
        self.deadzone = float(deadzone)
        self.last_speed: float = 0.0
        self.servo_id: Optional[str] = None  # For tracking servo ID
        self.stop()

    @classmethod
    def from_config(cls, pca, servo_id: str, servo_config: Dict[str, Any]) -> 'ContinuousServo':
        """
        Create a continuous servo from configuration.

        Args:
            pca: PCA9685 instance
            servo_id: String ID of the servo (e.g., 'c1')
            servo_config: Configuration dictionary for the servo

        Returns:
            Configured ContinuousServo instance
        """
        # Extract configuration parameters
        channel = servo_config['channel']
        min_us = servo_config['min_us']
        max_us = servo_config['max_us']
        center_us = servo_config['center_us']
        deadzone = servo_config['deadzone']

        # Create servo instance with config parameters
        servo = cls(pca, channel, min_us, max_us, center_us, deadzone)
        servo.servo_id = servo_id

        return servo

    def _us_to_ticks(self, microseconds: float) -> int:
        # 50Hz => 20ms period => 20000us; 12-bit => 4096 ticks
        ticks = int(4096.0 * (microseconds / 20000.0))
        # Clamp 0..4095
        if ticks < 0:
            return 0
        if ticks > 4095:
            return 4095
        return ticks

    def set_speed(self, speed: Optional[float]) -> None:
        if speed is None:
            speed = 0.0
        s = float(speed)
        if s > 1.0:
            s = 1.0
        if s < -1.0:
            s = -1.0
        if abs(s) < self.deadzone:
            s = 0.0

        half_span = (self.max_us - self.min_us) / 2.0
        microseconds = self.center_us + (s * half_span)
        ticks = self._us_to_ticks(microseconds)
        # print(
        #     f"ContServo ch={self.channel} speed={s:+.2f} -> {microseconds:.0f}us ({ticks} ticks)"
        # )
        try:
            self.pca.set_pwm(self.channel, 0, ticks)
            self.last_speed = s
        except Exception as e:
            print(f"ContServo: error setting channel {self.channel}: {e}")

    def stop(self) -> None:
        self.set_speed(0.0)

    def set_center(self, center_us: float) -> None:
        self.center_us = float(center_us)