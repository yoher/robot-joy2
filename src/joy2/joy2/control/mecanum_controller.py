from typing import Dict, Optional

from joy2.hardware.motor import DCMotorDriver


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class MecanumDriveController:
    """
    Mecanum kinematics mixer for 4 wheels using the motor order:
      M1 = Front-Left (FL)
      M2 = Front-Right (FR)
      M3 = Rear-Left (RL)
      M4 = Rear-Right (RR)

    Inputs (ROS REP 103 convention):
      vx: forward (+) / backward (-) [surge]
      vy: strafe left (+) / right (-) [sway]
      omega: positive CCW rotation

    Mixing (pre-normalization):
      FL (M1) = vx + vy + omega
      FR (M2) = vx - vy - omega
      RL (M3) = vx - vy + omega
      RR (M4) = vx + vy - omega
    """

    def __init__(
        self,
        motor_drv: DCMotorDriver,
        translation_scale: float = 0.6,
        rotation_scale: float = 0.6,
        eps: float = 0.02,
        invert_omega: bool = False,
        verbose: bool = True,
    ):
        self.motor_drv = motor_drv
        self.translation_scale = float(translation_scale)
        self.rotation_scale = float(rotation_scale)
        self.eps = float(eps)
        self.invert_omega = bool(invert_omega)
        self.verbose = verbose

        # Cache motors
        self.m1 = self.motor_drv.get_motor(1)  # FL
        self.m2 = self.motor_drv.get_motor(2)  # FR
        self.m3 = self.motor_drv.get_motor(3)  # RL
        self.m4 = self.motor_drv.get_motor(4)  # RR

        # Last applied speeds to reduce bus spam
        self._last = {"m1": 0.0, "m2": 0.0, "m3": 0.0, "m4": 0.0}

    def set_scales(self, translation: Optional[float] = None, rotation: Optional[float] = None):
        if translation is not None:
            self.translation_scale = float(translation)
        if rotation is not None:
            self.rotation_scale = float(rotation)

    def stop(self):
        self._apply(0.0, 0.0, 0.0, force=True)

    def drive(self, vx: float, vy: float, omega: float):
        """
        Apply scaled and normalized mecanum mix to motors.
        """
        self._apply(vx, vy, omega, force=False)

    # ----- internals -----

    def _apply(self, vx: float, vy: float, omega: float, force: bool):
        # Scale components
        vx_s = _clamp(vx * self.translation_scale, -1.0, 1.0)
        vy_s = _clamp(vy * self.translation_scale, -1.0, 1.0)
        om = -omega if self.invert_omega else omega
        om_s = _clamp(om * self.rotation_scale, -1.0, 1.0)

        # Raw mix (ROS REP 103 convention)
        w1 = vx_s + vy_s + om_s  # FL -> M1
        w2 = vx_s - vy_s - om_s  # FR -> M2
        w3 = vx_s - vy_s + om_s  # RL -> M3
        w4 = vx_s + vy_s - om_s  # RR -> M4

        # Normalize if any magnitude > 1
        max_mag = max(abs(w1), abs(w2), abs(w3), abs(w4), 1.0)
        if max_mag > 1.0:
            w1 /= max_mag
            w2 /= max_mag
            w3 /= max_mag
            w4 /= max_mag

        # Apply only if changed beyond epsilon or force
        self._set_motor_if_changed("m1", self.m1, w1, force)
        self._set_motor_if_changed("m2", self.m2, w2, force)
        self._set_motor_if_changed("m3", self.m3, w3, force)
        self._set_motor_if_changed("m4", self.m4, w4, force)

        if self.verbose:
            # Compact printf with clamped/normalized values
            print(
                f"MIX vx={vx:+.2f} vy={vy:+.2f} om={omega:+.2f} "
                f" -> M1={w1:+.2f} M2={w2:+.2f} M3={w3:+.2f} M4={w4:+.2f}"
            )

    def _set_motor_if_changed(self, key: str, motor, target: float, force: bool):
        last = self._last[key]
        if force or abs(target - last) > self.eps:
            motor.set_speed_float(target)
            self._last[key] = target