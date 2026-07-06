import os
import sys
import time
from typing import Any, Optional, Tuple, Dict
from abc import ABC, abstractmethod

import clr
import System
from System import Decimal

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KINESIS_PATH = os.path.join(BASE_DIR, "dlls", "Kinesis")

# Make sure Windows will search this folder for native DLLs
os.environ["PATH"] = KINESIS_PATH + os.pathsep + os.environ.get("PATH", "")
try:
    os.add_dll_directory(KINESIS_PATH)
except (AttributeError, FileNotFoundError) as e:
    raise e

sys.path.append(KINESIS_PATH)

clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
clr.AddReference("Thorlabs.MotionControl.TCube.DCServoCLI")
clr.AddReference("Thorlabs.MotionControl.KCube.DCServoCLI")
clr.AddReference("Thorlabs.MotionControl.Benchtop.StepperMotorCLI")

from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
from Thorlabs.MotionControl.TCube.DCServoCLI import TCubeDCServo
from Thorlabs.MotionControl.KCube.DCServoCLI import KCubeDCServo
from Thorlabs.MotionControl.Benchtop.StepperMotorCLI import BenchtopStepperMotor

DeviceManagerCLI.BuildDeviceList()
time.sleep(1)
print("Kinessis successfully imported.")


DEFAULT_POLLING_MS = 100
DEFAULT_TIMEOUT_MS = 60000
DEFAULT_LOG = True


class KinesisDevice(ABC):

    def __init__(self, serial):
        self.serial = str(serial)
        self.device = None
        self.is_connected = False

        self.home_pos: float = 0.0
        self.limits: Optional[Tuple[float, float]] = None  # (min_abs, max_abs)

    def _log(self, msg: str, log=DEFAULT_LOG):
        if log:
            print(f"[{self.serial}] {msg}")


    @abstractmethod
    def connect(self, polling_interval_ms=DEFAULT_POLLING_MS, log=DEFAULT_LOG):
        pass

    def disconnect(self, log=DEFAULT_LOG):
        if self.device and self.is_connected:
            self._log("Disconnecting...", log)
            self.device.StopPolling()
            self.device.Disconnect(True)
            self.is_connected = False
            self._log("Disconnected.", log)


    def set_home_position(self, home_pos: float, log=DEFAULT_LOG):
        self.home_pos = float(home_pos)
        self._log(f"Home offset set to {self.home_pos}", log)

    def set_limits(self, limits: Optional[Tuple[float, float]], log=DEFAULT_LOG):
        self.limits = limits
        self._log(f"Limits set to {self.limits}", log)

    def set_velocity(self, max_velocity: float, log=DEFAULT_LOG):
        if not self.is_connected:
            raise Exception("Not Connected")
        vel_params = self.device.GetVelocityParams()
        vel_params.MaxVelocity = Decimal(max_velocity)
        self.device.SetVelocityParams(vel_params)
        self._log(f"Velocity set to {max_velocity}", log)

    def set_acceleration(self, acceleration: float, log=DEFAULT_LOG):
        if not self.is_connected:
            raise Exception("Not Connected")
        vel_params = self.device.GetVelocityParams()
        vel_params.Acceleration = Decimal(acceleration)
        self.device.SetVelocityParams(vel_params)
        self._log(f"Acceleration set to {acceleration}", log)


    def get_position(self, absolute: bool=False) -> Optional[float]:
        if not self.is_connected:
            return None
        pos = float(System.Convert.ToDouble(self.device.DevicePosition))

        if absolute:
            return pos
 
        return pos - self.home_pos

    def is_busy(self) -> bool:
        if not self.is_connected:
            raise Exception("Not Connected")
        return self.device.IsDeviceBusy


    def move_to(self, pos: float, is_absolute: bool = False, timeout_ms=DEFAULT_TIMEOUT_MS, log=DEFAULT_LOG):
        if not self.is_connected:
            raise Exception("Not Connected")
        
        if pos is None: return

        absolute_pos = pos if is_absolute else self.home_pos + pos

        if self.limits is not None:
            mn, mx = self.limits
            if absolute_pos < mn or absolute_pos > mx:
                raise ValueError(f"[{self.serial}] Target {pos} (absolute {absolute_pos}) outside limits ({mn}, {mx})")

        self._log(f"Moving to {pos}...", log)
        self.device.MoveTo(Decimal(absolute_pos), timeout_ms)
        self._log(f"Move finished. Current Pos: {self.get_position(is_absolute)}", log)

    def home(self, absolute: bool = False, timeout_ms=DEFAULT_TIMEOUT_MS, log=DEFAULT_LOG):
        if not self.is_connected:
            raise Exception("Not Connected")

        self._log("Homing...", log)

        self.device.Home(timeout_ms)
        if (not absolute) and self.home_pos:
            self.device.MoveTo(Decimal(self.home_pos), timeout_ms)

        self._log("Homing finished.", log)


class TDC001Controller(KinesisDevice):
    def connect(self, polling_interval_ms=DEFAULT_POLLING_MS, log=DEFAULT_LOG):
        self._log("Connecting TDC001 ...", log)
        
        self.device = TCubeDCServo.CreateTCubeDCServo(self.serial)
        self.device.Connect(self.serial)
        
        if not self.device.IsSettingsInitialized():
            self.device.WaitForSettingsInitialized(5000)

        # Load configuration so units are mm/degrees, not encoder counts
        self.device.LoadMotorConfiguration(self.serial)
        

        self.device.StartPolling(polling_interval_ms)
        self.device.EnableDevice()
    
        self.is_connected = True
        self._log("Connected.", log)


class KDC101Controller(KinesisDevice):
    def connect(self, polling_interval_ms=DEFAULT_POLLING_MS, log=DEFAULT_LOG):
        self._log("Connecting KDC101 ...", log)

        self.device = KCubeDCServo.CreateKCubeDCServo(self.serial)
        self.device.Connect(self.serial)
        
        if not self.device.IsSettingsInitialized():
            self.device.WaitForSettingsInitialized(5000)
            
        self.device.LoadMotorConfiguration(self.serial)
        self.device.StartPolling(polling_interval_ms)
        self.device.EnableDevice()

        self.is_connected = True
        self._log("Connected.", log)


class SCC201Controller(KinesisDevice):
    def __init__(self, channel_device, parent_serial, channel_index):
        super().__init__(f"{parent_serial}-CH{channel_index}")
        self.device = channel_device
        self.parent_serial = str(parent_serial)
        self.channel_index = channel_index

    def _log(self, msg: str, log=DEFAULT_LOG):
        if log:
            print(f"> [channel {self.channel_index}] {msg}")


    def connect(self, polling_interval_ms=DEFAULT_POLLING_MS, log=DEFAULT_LOG):
        self._log("Connecting SCC201...", log)

        if not self.device.IsSettingsInitialized():
            self.device.WaitForSettingsInitialized(5000)

        self.device.StartPolling(polling_interval_ms)
        self.device.EnableDevice()
        self.device.LoadMotorConfiguration(self.device.DeviceID)

        self.is_connected = True
        self._log("Connected.", log)

    def disconnect(self, log=DEFAULT_LOG):
        self._log("Disconnecting...", log)
        super().disconnect(False)
        self._log("Disconnected.", log)


class BSC203Controller(KinesisDevice):
    def __init__(self, serial):
        super().__init__(serial)

        # Properties for the 3 Motors
        self.channels: Dict[int, Optional[SCC201Controller]] = {1: None, 2: None, 3: None}

        self.home_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.limits: Optional[Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]] = None
        # limits are ABS limits per axis: ((xmin,xmax),(ymin,ymax),(zmin,zmax))

    def connect(self, polling_interval_ms=DEFAULT_POLLING_MS, log=DEFAULT_LOG):
        self._log("Connecting BSC203 main unit...", log)

        self.device = BenchtopStepperMotor.CreateBenchtopStepperMotor(self.serial)
        self.device.Connect(self.serial)

        self._log("Initializing SCC201 channels...", log)

        # for channel_index in [1, 2, 3]:   # For now. channel 1 isn't working
        for channel_index in [2, 3]:
            channel_device = self.device.GetChannel(channel_index)
            channel = SCC201Controller(channel_device, self.serial, channel_index)
            channel.connect(polling_interval_ms, log)
            self.channels[channel_index] = channel

        self.is_connected = True
        self._log("Connect finished.", log)

    def disconnect(self, log=DEFAULT_LOG):
        if self.device and self.is_connected:
            self._log("Disconnecting...", log)

            for _, device in self.channels.items():
                if device and device.is_connected:
                    device.disconnect(log)

            self.device.Disconnect(True)
            self.is_connected = False
            self._log("Disconnected.", log)


    def set_home_position(self, home_pos: Tuple[float, float, float], log=DEFAULT_LOG):
        self.home_pos = home_pos
        for channel, pos in zip(self.channels.items(), home_pos):
            if channel and (pos is not None):
                channel.set_home_position(pos, False)
        self._log(f"Home offset set to {self.home_pos}", log)

    def set_limits(self, limits: Optional[Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]], log=DEFAULT_LOG):
        self.limits = limits
        for channel, lim in zip(self.channels.items(), limits):
            if channel and lim:
                channel.set_limit(lim, False)
        self._log(f"Limits set to {self.limits}", log)

    def set_velocity(self, max_velocity: Tuple[float, float, float], log=DEFAULT_LOG):
        for channel, vel in zip(self.channels.items(), max_velocity):
            if channel and (vel is not None):
                channel.set_velocity(vel, False)
        self._log(f"Home offset set to {max_velocity}", log)

    def set_acceleration(self, acceleration: Tuple[float, float, float], log=DEFAULT_LOG):
        for channel, acc in zip(self.channels.items(), acceleration):
            if channel and (acc is not None):
                channel.set_acceleration(acc, False)
        self._log(f"Home offset set to {self.home_pos}", log)


    def get_position(self, absolute: bool = False):
        pos = [(channel.get_position(absolute) if channel else None) for channel in self.channels.values()]
        return tuple(pos)

    def is_busy(self) -> bool:
        if not self.is_connected:
            raise Exception("Not Connected")
        return any(channel.is_busy() for channel in self.channels.values() if channel)


    def move_to(self, pos: Tuple[float, float, float], is_absolute : bool = True, timeout_ms=DEFAULT_TIMEOUT_MS, log=DEFAULT_LOG):
        # Check device connection
        if not self.is_connected: raise Exception("Not Connected")
        
        # Check if there is any movement
        if any([p is not None for p in pos]): return

        # Start moving
        self._log(f"Moving to {pos}...", log)
        for c, p in zip(self.channels.items(), pos):
            c.move_to(p, is_absolute, 0, log)

        if timeout_ms == 0: return

        # Wait for device to be busy
        t0 = time.time()
        while True:
            if self.is_busy(): 
                break
            if (time.time() - t0) * 1000 > timeout_ms:
                raise TimeoutError("Move operation timed out.")
            time.sleep(0.05)

        # Blocking
        while True:
            if not self.is_busy():
                break
            if (time.time() - t0) * 1000 > timeout_ms:
                raise TimeoutError("Move operation timed out.")
            time.sleep(0.05)

        self._log(f"Move finished. Current Pos: {self.get_position()}", log)

    def home(self, timeout_ms=DEFAULT_TIMEOUT_MS, log=DEFAULT_LOG):
        if not self.is_connected:
            raise Exception("Not Connected")

        self._log("Homing...", log)

        for channel in self.channels.values():
            if channel:
                channel.home(0, log=False)

        t0 = time.time()
        while True:
            if not self.is_busy():
                break
            if (time.time() - t0) * 1000 > timeout_ms:
                raise TimeoutError("Homing operation timed out.")
            time.sleep(0.05)

        self._log("Homing finished.", log)
