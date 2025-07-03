#!/usr/bin/env python3
# -*- coding:utf-8 -*-
################################################################
# Copyright 2025 Jecjune. All rights reserved.
# Author: Jecjune jecjune@qq.com
# Date  : 2025-3-20
################################################################
from .generated.public_api_types_pb2 import RobotType, LinearLiftStatus
from .utils import log_warn, log_info, log_err, log_common
from typing import Type, Optional
import threading
from copy import deepcopy

class Lift:

    def __init__(self, lift_type, pulse_per_meter: int, max_speed: int):

        # chassis type
        self.lift_type = lift_type
        self.pulse_per_meter = pulse_per_meter  # pulse / m
        self.__max_speed = max_speed

        if lift_type == RobotType.RtLotaLinearLift:
            log_info("Lift type is RtLotaLinearLift.")
        else:
            raise ValueError(f"Unsupported lift type: {lift_type}")

        self.__data_lock = threading.Lock()
        self.__has_new = False
        # Lift data read from websocket
        self.__lift_status = None
        # lift data
        self.__max_pos = 0.0  # m
        self.__current_max_speed = 0.0
        self.__current_pos = 0.0  # m
        self._calibrated = False  # m
        self.__err = None
        self.__custom_button_pressed = False

        # if you want to change or read the target, you need to lock the command_lock
        self.__command_lock = threading.Lock()

        # target position for lift
        self.__target_pos = None  # m
        self._target_max_speed = None
        self._target_brake = False
        self._init_flag = False

    def _update_lift_data(self, lift_status: LinearLiftStatus):
        with self.__data_lock:
            self.__has_new = True
            self._calibrated = lift_status.calibrated
            self.__lift_status = lift_status.state
            self.__max_pos = lift_status.max_pos / self.pulse_per_meter
            self.__current_pos = lift_status.current_pos / self.pulse_per_meter
            self.__current_max_speed = lift_status.speed
            self.__err = lift_status.parking_stop_detail
            self.__custom_button_pressed = lift_status.custom_button_pressed

    ########## Command setters ##########
    def set_target_pos(self, target: float):
        '''
        set target position.
        target           unit: m  (range is [0, max_pos] or [max_pos, 0])
        '''
        if self.lift_type == RobotType.RtLotaLinearLift:
            if self.__max_pos < 0.0:
                if target > 0.0 or target < self.__max_pos:
                    raise ValueError("set_target_pos: target out of range")
            else:
                if target < 0.0 or target > self.__max_pos:
                    raise ValueError("set_target_pos: target out of range")
            with self.__command_lock:
                self.__target_pos = deepcopy(target)

    def set_max_speed(self, max_speed: int):
        """
        Use simple control mode to set Lift speed.
        max_speed: default is 75000, unit is pulse/s
        """
        if max_speed < 0:
            raise ValueError("set_max_speed: max_speed must be greater than 0")
        if self.lift_type == RobotType.RtLotaLinearLift:
            if max_speed > self.__max_speed:
                max_speed = self.__max_speed
            with self.__command_lock:
                self._target_max_speed = max_speed
        else:
            raise NotImplementedError(
                "set_max_speed not implemented for lift_type: ",
                self.lift_type)

    def set_brake(self):
        """
        Set brake, it will brake motor at once.
        You can exit LsBrake mode by sending target_pos command or calibrate command.
        You don't have to keep sending brake command, but it is recommended to do so.
        """
        if self.lift_type == RobotType.RtLotaLinearLift:
            with self.__command_lock:
                self._target_brake = True

    def init_lift(self):
        """
        Set init flag, it will activate motor calibrate at once.
        """
        with self.__command_lock:
            self._init_flag = True

    ########## Command getters ##########
    def get_target_pos(self) -> Optional[float]:
        '''
        get target position, unit is m.
        '''
        with self.__command_lock:
            if self.__target_pos is not None and self.__target_pos != self.__current_pos:
                return deepcopy(self.__target_pos)
            else:
                return None
    
    def get_target_max_speed(self) -> Optional[int]:
        """ get target max speed """
        with self.__command_lock:
            # Have new target max speed and it is not none.
            if self._target_max_speed != self.__current_max_speed and self._target_max_speed is not None:
                return deepcopy(self._target_max_speed)
            else:
                return None

    def get_init_flag(self) -> bool:
        """
        Get init flag, it will activate motor init at once.
        """
        with self.__command_lock:
            if self._init_flag:
                self._init_flag = False
                return True
            else:
                return False
            
    def get_brake_status(self) -> bool:
        '''
        Get brake status
        '''
        with self.__command_lock:
            return self._target_brake

    ########## Data getters ##########
    def get_lift_status(self) -> LinearLiftStatus:
        '''
        Get current lift status.
        '''
        with self.__data_lock:
            self.__has_new = False
            return deepcopy(self.__lift_status)

    def get_calibrated(self) -> bool:
        """ get calibrated """
        with self.__data_lock:
            return deepcopy(self._calibrated)

    def get_max_target_speed(self) -> Optional[int]:
        """ get max speed """
        with self.__data_lock:
            return deepcopy(self._target_max_speed)

    def get_max_pos(self) -> float:
        """ get lift max position, unit is m, range is [0, max_pos] or [max_pos, 0] """
        with self.__data_lock:
            return deepcopy(self.__max_pos)

    def get_current_pos(self) -> float:
        """ get lift current position, unit is m """
        with self.__data_lock:
            self.__has_new = False
            return deepcopy(self.__current_pos)

    def get_current_max_speed(self) -> float:
        """ get lift max speed setting, unit is pulse/s """
        with self.__data_lock:
            self.__has_new = False
            return deepcopy(self.__current_max_speed)

    def get_error(self):
        '''
        Get lift error code.
        '''
        with self.__data_lock:
            return deepcopy(self.__err)

    def get_custom_button_pressed(self) -> Optional[bool]:
        """ get custom button pressed status """
        with self.__data_lock:
            return deepcopy(self.__custom_button_pressed)

    def has_new_data(self) -> bool:
        '''
        Check if there is any new data.
        '''
        with self.__data_lock:
            return self.__has_new
