#!/usr/bin/env python3
# -*- coding:utf-8 -*-
################################################################
# Copyright 2025 Jecjune. All rights reserved.
# Author: Jecjune jecjune@qq.com
# Date  : 2025-3-20
################################################################
from enum import Enum

class WsError(Exception):
    pass

class ProtocolError(WsError):
    pass

class ConnectionClosedError(WsError):
    pass