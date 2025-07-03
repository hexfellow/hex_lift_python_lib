#!/usr/bin/env python3
# -*- coding:utf-8 -*-
################################################################
# Copyright 2025 Jecjune. All rights reserved.
# Author: Jecjune jecjune@qq.com
# Date  : 2025-3-20
################################################################

from .generated import public_api_down_pb2, public_api_up_pb2, public_api_types_pb2
from .error_type import WsError, ProtocolError
from .utils import is_valid_ws_url, InvalidWSURLException, delay
from .lift import Lift
from .utils import log_warn, log_info, log_err, log_common

from math import pi as PI
import asyncio
import threading
import time

import websockets
from typing import Optional, Tuple
from websockets.exceptions import ConnectionClosed

MAX_CYCLES = 1000
RAW_DATA_LEN = 30
TIME_OUT = 1.0

class PublicAPI:

    def __init__(self, ws_url: str, control_hz: int):
        '''
        @brief: Initialize the PublicAPI class.
        @param ws_url: The WebSocket URL to connect to.
        @param control_hz: The control frequency in Hz.
        '''
        self.__websocket = None
        try:
            self.__ws_url: str = is_valid_ws_url(ws_url)
        except InvalidWSURLException as e:
            log_err("Invalid WebSocket URL: " + str(e))

        if control_hz > MAX_CYCLES:
            log_warn(f"control_cycle is limit to {MAX_CYCLES}")
            control_hz = MAX_CYCLES
        self.__control_hz = control_hz

        self.lift = None
        self.__last_data_frame_time = None
        self.__last_warning_time = time.perf_counter()

        # init api
        self.__shutdown_event = None  # Will be created in the correct loop
        self.__loop_thread = threading.Thread(target=self.__loop_start,
                                              daemon=True)
        self.__api_data = []
        self.__loop_thread.start()
        # wait for lift to be initialized
        self.wait_init()

    ########## Command Constructors ##########
    def construct_pos_control_message(
            self, data: int) -> public_api_down_pb2.APIDown:
        """
        @brief: For constructing a simple control message.
        """
        if self.lift.lift_type == public_api_types_pb2.RobotType.RtLotaLinearLift:
            msg = public_api_down_pb2.APIDown()
            lift_command = public_api_types_pb2.LinearLiftCommand()
            lift_command.target_pos = data
            msg.linear_lift_command.CopyFrom(lift_command)
            return msg
        else:
            raise ValueError(
                "construct_simple_control_message: lift_type error")

    def construct_init_message(self) -> public_api_down_pb2.APIDown:
        """
        @brief: For constructing a init message.
        """
        if self.lift.lift_type == public_api_types_pb2.RobotType.RtLotaLinearLift:
            msg = public_api_down_pb2.APIDown()
            lift_command = public_api_types_pb2.LinearLiftCommand()
            lift_command.calibrate = True
            msg.linear_lift_command.CopyFrom(lift_command)
            print("msg: ", msg)
            return msg
        else:
            raise ValueError("construct_init_message: lift_type error")

    def construct_brake_message(self, brake: bool) -> public_api_down_pb2.APIDown:
        """
        @brief: For constructing a brake message.
        """
        if self.lift.lift_type == public_api_types_pb2.RobotType.RtLotaLinearLift:
            msg = public_api_down_pb2.APIDown()
            lift_command = public_api_types_pb2.LinearLiftCommand()
            lift_command.brake = brake
            msg.linear_lift_command.CopyFrom(lift_command)
            return msg
        else:
            raise ValueError("construct_init_message: lift_type error")

    def construct_set_max_speed_message(
            self, data: int) -> public_api_down_pb2.APIDown:
        """
        @brief: For constructing a set max speed message.
        """
        if self.lift.lift_type == public_api_types_pb2.RobotType.RtLotaLinearLift:
            msg = public_api_down_pb2.APIDown()
            lift_command = public_api_types_pb2.LinearLiftCommand()
            lift_command.set_speed = data
            msg.linear_lift_command.CopyFrom(lift_command)
            return msg
        else:
            raise ValueError("construct_set_max_speed_message: lift_type error")

    ########## Command Senders ##########
    async def send_down_message(self, data: public_api_down_pb2.APIDown):
        msg = data.SerializeToString()
        if self.__websocket is None:
            raise AttributeError("send_down_message: websocket tx is None")
        else:
            await self.__websocket.send(msg)

    ########## WebSocket ##########
    async def __connect_ws(self):
        """
        @brief: Connect to the WebSocket server, used by "initialize" function.
        """
        try:
            self.__websocket = await websockets.connect(self.__ws_url,
                                                        ping_interval=20,
                                                        ping_timeout=60,
                                                        close_timeout=5)
        except Exception as e:
            log_err(f"Failed to open WebSocket connection: {e}")
            log_common(
                "Public API haved exited, please check your network connection and restart the server again."
            )
            exit(1)

    async def __reconnect(self):
        retry_count = 0
        max_retries = 5
        base_delay = 1

        while retry_count < max_retries:
            try:
                if self.__websocket:
                    await self.__websocket.close()
                self.__websocket = await websockets.connect(self.__ws_url,
                                                            ping_interval=20,
                                                            ping_timeout=60,
                                                            close_timeout=5)
                return
            except Exception as e:
                delay = base_delay * (2**retry_count)
                log_warn(
                    f"Reconnect failed (attempt {retry_count+1}): {e}, retrying in {delay}s"
                )
                await asyncio.sleep(delay)
                retry_count += 1
        raise ConnectionError("Maximum reconnect retries exceeded")

    async def __capture_data_frame(self) -> Optional[public_api_up_pb2.APIUp]:
        """
        @brief: Continuously monitor WebSocket connections until:
        1. Received a valid binary Protobuf message
        2. Protocol error occurred
        3. Connection closed
        4. No data due to timeout
        
        @params:
            websocket: Established WebSocket connection object
            
        @return:
            base_backend.APIUp object or None
        """
        while True:
            try:
                # Check if websocket is connected
                if self.__websocket is None:
                    log_err("WebSocket is not connected")
                    await asyncio.sleep(1)
                    continue

                # Timeout
                message = await asyncio.wait_for(self.__websocket.recv(),
                                                 timeout=3.0)
                # Only process binary messages
                if isinstance(message, bytes):
                    try:
                        # Protobuf parse
                        api_up = public_api_up_pb2.APIUp()
                        api_up.ParseFromString(message)

                        if not api_up.IsInitialized():
                            raise ProtocolError("Incomplete message")
                        # Filter other type message
                        elif api_up.linear_lift_status.IsInitialized():
                            return api_up

                    except Exception as e:
                        log_err(f"Protobuf encode fail: {e}")
                        raise ProtocolError("Invalid message format") from e

                elif isinstance(message, str):
                    log_common(f"ignore string message: {message[:50]}...")
                    continue

            except asyncio.TimeoutError:
                log_err("No data received for 3 seconds")
                continue

            except ConnectionClosed as e:
                log_err(
                    f"Connection closed (code: {e.code}, reason: {e.reason})")
                try:
                    await self.__reconnect()
                    continue
                except ConnectionError as e:
                    log_err(f"Reconnect failed: {e}")
                    self.close()

            except Exception as e:
                log_err(f"Unknown error: {str(e)}")
                raise WsError("Unexpected error") from e

    ########## Main Functions ##########
    async def __capture_first_frame(self):
        # init parameter
        api_up = public_api_up_pb2.APIUp()
        api_up.robot_type = public_api_types_pb2.RobotType.RtUnknown
        # wait for robot type
        while api_up.robot_type == public_api_types_pb2.RobotType.RtUnknown:
            api_up = await self.__capture_data_frame()
        # try to init lift
        try:
            if api_up.robot_type == public_api_types_pb2.RobotType.RtLotaLinearLift:
                self.lift = Lift(api_up.robot_type,
                                 api_up.linear_lift_status.pulse_per_rotation,
                                 api_up.linear_lift_status.max_speed)
                log_info("**Lift is ready to use**")
        except Exception as e:
            log_err(f"Failed to initialize lift: {e}")
            self.close()

    def __loop_start(self):
        self.__loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__loop)
        self.__loop.run_until_complete(self.__main_loop())

    def close(self):
        if self.__loop and self.__loop.is_running():
            log_warn("HexLift API is closing...")
            asyncio.run_coroutine_threadsafe(self.__async_close(), self.__loop)

    async def __async_close(self):
        if self.__websocket:
            await self.__websocket.close()
        if self.__shutdown_event:
            self.__shutdown_event.set()

    async def __main_loop(self):
        # Create shutdown event in the correct event loop
        self.__shutdown_event = asyncio.Event()
        
        log_common("HexLift Api started.")
        await self.__connect_ws()
        await self.__capture_first_frame()
        task1 = asyncio.create_task(self.__periodic_state_checker())
        task2 = asyncio.create_task(self.__periodic_data_parser())
        self.__tasks = [task1, task2]
        await self.__shutdown_event.wait()
        for task in self.__tasks:
            task.cancel()
        await asyncio.gather(*self.__tasks, return_exceptions=True)
        log_err("HexLift api main_loop exited.")

    async def __periodic_data_parser(self):
        """
        Capture and parse data from WebSocket connection.
        """
        while True:
            try:
                api_up = await self.__capture_data_frame()
                # record raw data to buffer
                if len(self.__api_data) >= RAW_DATA_LEN:
                    self.__api_data.pop(0)
                self.__api_data.append(api_up)

                # parse lift data
                if self.lift is not None:
                    self.lift._update_lift_data(api_up.linear_lift_status)
                    self.__last_data_frame_time = time.perf_counter()
            except Exception as e:
                log_err(f"parse data error: {e}")
                continue

    async def __periodic_state_checker(self):
        cycle_time = 1000.0 / self.__control_hz
        start_time = time.perf_counter()
        self.__last_warning_time = start_time
        while True:
            await delay(start_time, cycle_time)
            start_time = time.perf_counter()

            # if have not data received, we should not do anything
            if self.__last_data_frame_time is None:
                continue

            # Check if lift is initialized
            if self.lift is None:
                continue

            # check if have parking stop
            if self.lift.get_error() != public_api_types_pb2.ParkingStopDetail():
                if start_time - self.__last_warning_time > 1.0:
                    log_err(f"emergency stop: {self.lift.get_error()}.")
                    log_err(
                        "You must reinitialize the lift to clear the error.")
                    self.__last_warning_time = start_time

            # check if timeout
            if start_time - self.__last_data_frame_time > TIME_OUT:
                if start_time - self.__last_warning_time > 1.0:
                    log_err("No data received for 1 second, lift may be dead.")
                    self.__last_warning_time = start_time
                continue

            # check if lift is calibrated
            if self.lift.get_init_flag():
                msg = self.construct_init_message()
                await self.send_down_message(msg)
                await asyncio.sleep(0.1)

            if self.lift._calibrated == False:
                if start_time - self.__last_warning_time > 1.0:
                    log_err(
                        "Lift is not calibrated, please calibrate the lift.")
                    self.__last_warning_time = start_time
                continue

            # check if brake
            # if it is false, sending pos target will auto unlock, so just deal true
            target_brake = self.lift.get_brake_status()
            if target_brake is True:
                msg = self.construct_brake_message(bool(target_brake))
                await self.send_down_message(msg)
            
            else:
                target_pos = self.lift.get_target_pos()
                if target_pos is not None:
                    msg = self.construct_pos_control_message(
                        int(target_pos * self.lift.pulse_per_meter))
                    await self.send_down_message(msg)

                target_max_speed = self.lift.get_target_max_speed()
                if target_max_speed is not None:
                    msg = self.construct_set_max_speed_message(
                        int(target_max_speed))
                    await self.send_down_message(msg)

    def is_api_exit(self) -> bool:
        return self.__loop.is_closed()

    def wait_init(self):
        try:
            while True:
                if self.lift is not None:
                    break
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.close()
            exit(1)

    def _get_raw_data(self) -> Tuple[public_api_up_pb2.APIUp, int]:
        """
        Retrieve the oldest raw data in the buffer. 
        The maximum length of this buffer is RAW-DATA_LEN.
        You can use '_parse_wheel_data' to parse the raw data.
        """
        if len(self.__api_data) == 0:
            return (None, 0)
        return (self.__api_data.pop(0), len(self.__api_data))
