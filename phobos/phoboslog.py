#!/usr/bin/python
# coding=utf-8

"""
.. module:: phobos.phoboslog
    :platform: Unix, Windows, Mac
    :synopsis: TODO: This module offers a simple way to log messages from phobos and uses blender integrated tools
    to display them.

.. moduleauthor:: Ole Schwiegert, Kai von Szadkowski, Simon Reichel

Copyright 2014, University of Bremen & DFKI GmbH Robotics Innovation Center

This file is part of Phobos, a Blender Add-On to edit robot models.

Phobos is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License
as published by the Free Software Foundation, either version 3
of the License, or (at your option) any later version.

Phobos is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with Phobos.  If not, see <http://www.gnu.org/licenses/>.

File phoboslog.py

Created on 05 Dec 2014

"""

import inspect
import bpy
from datetime import datetime

# levels of detail for logging
loglevels = ('NONE', 'ERROR', 'WARNING', 'INFO', 'DEBUG')


class col:
    """
    Provides the color ids for different terminal messages.
    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    DEBUG = '\033[35m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    DIM = '\033[2m'


def decorate(level):
    """
    Provides a simple wrapper to color the log level according to the colors
    from class col.

    :param level: the loging level as described by loglevels.
    :type level: str.
    :return: str - decorated string of level
    """
    if level == "INFO":
        return col.BOLD+col.OKGREEN+level+col.ENDC
    if level == "WARNING":
        return col.BOLD+col.WARNING+level+col.ENDC
    if level == "ERROR":
        return col.BOLD+col.FAIL+level+col.ENDC
    if level == "DEBUG":
        return col.BOLD+col.DEBUG+level+col.ENDC
    else:
        return level


def log(message, level="INFO", origin=None, prefix=""):
    """
    Logs a given message to the blender console and logging file if present
    and if log level is low enough. The origin can be defined as string.
    The message is logged by the operator depending on the loglevel
    settings.

    :param message: The message to log.
    :type message: str.
    :param level: Valid log level for the message as defined by 'loglevels'.
    :type level: str.
    :param origin: If set the message is prefixed with the origin.
    :type origin: str. or obj.
    :param prefix: Any string that should be printed before message (e.g. "\n")
    :type prefix: str.
    :return: None.
    """
    # TODO delete me?
    # Generate name of origin
    #if origin is None:
    #    originname='phoboslog'
    #elif type(origin) is not str:
    #    originname = origin.bl_idname
    #else:
    #    originname = origin
    #originname = inspect.stack()[1][1].split('addons/')[-1] + ' - ' + inspect.stack()[1][3]
    callerframerecord = inspect.stack()[1]
    frame = callerframerecord[0]
    info = inspect.getframeinfo(frame)
    originname = info.filename.split('addons/')[-1] + ' - ' + info.function + '(' + str(info.lineno) + ')'

    # Display only messages up to preferred log level
    prefs = bpy.context.user_preferences.addons["phobos"].preferences
    if loglevels.index(level) <= loglevels.index(prefs.loglevel):
        date = datetime.now().strftime("%Y%m%d_%H:%M")
        msg = "[" + date + "] " + level + " " + message + " (" + originname + ")"
        terminalmsg = prefix + "[" + date + "] " + decorate(level) + " " + message +\
                      col.DIM + " (" + originname + ")" + col.ENDC

        # log to file if activated
        if prefs.logtofile:
            try:
                with open(prefs.logfile, "a") as lf:
                    lf.write(date + "  " + msg + "\n")
            except IOError:
                # FIXME Infinite loop can occur when harddrive has an error!
                # Thus, logging the IOError should be handled differently...
                log("Cannot write to log file! Resetting it: " + __name__ + ".log", "ERROR")

        # log to terminal or Blender
        if prefs.logtoterminal:
            print(terminalmsg)
        else:
            # log in GUI depending on loglevel
            import sys
            # start from this function
            frame = sys._getframe(1)
            f_name = frame.f_code.co_name
            # go back until operator (using execute)
            while f_name != 'execute' and frame is not None:
                frame = frame.f_back
                f_name = frame.f_code.co_name

            # use operator to show message in Blender
            if 'self' in frame.f_locals:
                origin = frame.f_locals['self']

            # show message in Blender status bar.
            if origin is not None and type(origin) is not str:
                # CHECK are the messages in status bar working?
                # format report message to remove loging level and originname
                msg = msg.split(level)[1][1:]
                msg = msg.split(originname)[0][:-2]
                origin.report({level}, msg)
