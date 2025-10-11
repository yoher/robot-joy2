from typing import Dict

# DC motor control using PCA9685 channels (compatible with Emakefun mapping)
# Mapping (matches Emakefun_MotorHAT Emakefun_DCMotor pin map):
#   Motor 1: IN1=0, IN2=1
#   Motor 2: IN1=3, IN2=2
#   Motor 3: IN1=4, IN2=5
#   Motor 4: IN1=7, IN2=6
#
# Control scheme (same as Emakefun reference):
# - FORWARD:  IN2 fully OFF, IN1 PWM (speed*16)
# - BACKWARD: IN1 fully OFF, IN2 PWM (speed*16)
# - RELEASE:  IN1 fully OFF, IN2 fully OFF


FORWARD = 1
BACKWARD = 2
RELEASE = 4

_MOTOR_PIN_MAP: Dict[int, tuple[int, int]] = {
    1: (0, 1),  # (IN1, IN2)
    2: (3, 2),
    3: (4, 5),
    4: (7, 6),
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class DCMotor:
    def __init__(self, pca, motor_index: int, verbose: bool = True):
        if motor_index not in _MOTOR_PIN_MAP:
            raise ValueError("Motor index must be in 1..4")
        self.pca = pca
        self.motor_index = motor_index
        self.in1_pin, self.in2_pin = _MOTOR_PIN_MAP[motor_index]
        self._speed_255 = 0
        self._direction = RELEASE
        self._verbose = verbose
        # Ensure released initially
        self.run(RELEASE)

    def _pin_off(self, pin: int):
        # Fully OFF -> (on=0, off=4096)
        self.pca.set_pwm(pin, 0, 4096)

    def _pin_pwm(self, pin: int, value_4095: int):
        # Duty cycle: (on=0, off=value)
        self.pca.set_pwm(pin, 0, _clamp(int(value_4095), 0, 4095))

    def setSpeed(self, speed_255: int):
        # Clamp 0..255
        s = int(speed_255)
        if s < 0:
            s = 0
        if s > 255:
            s = 255
        self._speed_255 = s
        # Apply with current direction
        if self._direction == FORWARD:
            self._pin_off(self.in2_pin)
            self._pin_pwm(self.in1_pin, s * 16)
        elif self._direction == BACKWARD:
            self._pin_off(self.in1_pin)
            self._pin_pwm(self.in2_pin, s * 16)
        else:
            # RELEASE
            self._pin_off(self.in1_pin)
            self._pin_off(self.in2_pin)

    def run(self, command: int):
        self._direction = command
        self.setSpeed(self._speed_255)

    # Convenience helpers

    def set_speed_float(self, speed: float):
        """
        speed in [-1.0, 1.0]:
         - sign controls direction
         - magnitude controls speed
        """
        speed = _clamp(float(speed), -1.0, 1.0)
        if abs(speed) < 1e-6:
            if self._verbose:
                print(f"[Motor {self.motor_index}] speed={speed:.2f} -> RELEASE")
            self.run(RELEASE)
            return
        if speed > 0:
            pwm = int(speed * 255.0)
            if self._verbose:
                print(f"[Motor {self.motor_index}] speed={speed:.2f} -> FORWARD pwm={pwm}")
            self.run(FORWARD)
            self.setSpeed(pwm)
        else:
            pwm = int(abs(speed) * 255.0)
            if self._verbose:
                print(f"[Motor {self.motor_index}] speed={speed:.2f} -> BACKWARD pwm={pwm}")
            self.run(BACKWARD)
            self.setSpeed(pwm)

    def release(self):
        self.run(RELEASE)


class DCMotorDriver:
    def __init__(self, pca, verbose: bool = True):
        self.pca = pca
        self._motors = {i: DCMotor(self.pca, i, verbose=verbose) for i in (1, 2, 3, 4)}

    def get_motor(self, num: int) -> DCMotor:
        return self._motors[num]

    def release_all(self):
        for m in self._motors.values():
            m.release()