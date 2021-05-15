#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:set ts=4 sw=4 et:
#
# Copyright 2014,2015,2021 Vladimir Ermakov.
#
# This file is part of the mavros package and subject to the license terms
# in the top-level LICENSE file of the mavros repository.
# https://github.com/mavlink/mavros/tree/master/LICENSE.md
"""
mav cmd command
"""

import sys
import threading

import click
from sensor_msgs.msg import NavSatFix

from mavros_msgs.srv import (CommandBool, CommandHome, CommandInt, CommandLong,
                             CommandTOL, CommandTriggerControl,
                             CommandTriggerInterval)

from . import cli, pass_client


@cli.group()
@click.option("--wait",
              default=False,
              help="Wait for establishing FCU connection")
def cmd():
    """
    Tool to send commands to MAVLink device.
    """


def _check_ret(ctx, ret, verbose: bool = True):
    if not ret.success:
        click.echo(f"Request failed. Check mavros logs. ACK: {ret.result}")
        ctx.exit(1)

    if verbose:
        click.echo(f"Command ACK: {ret.result}")


@cmd.command()
@click.option("-c",
              "--confirmation",
              default=False,
              help="Require confirmation")
@click.option("-b", "--broadcast", default=False, help="Broadcast command")
@click.argument('command', type=int)
@click.argument('param1', type=float)
@click.argument('param2', type=float)
@click.argument('param3', type=float)
@click.argument('param4', type=float)
@click.argument('param5', type=float)
@click.argument('param6', type=float)
@click.argument('param7', type=float)
@pass_client
@click.pass_context
def long(ctx, client, confirmation, broadcast, command, param1, param2, param3,
         param4, param5, param6, param7):

    req = CommandLong.Request(
        broadcast=broadcast,
        command=command,
        confirmation=int(confirmation),
        param1=param1,
        param2=param2,
        param3=param3,
        param4=param4,
        param5=param5,
        param6=param6,
        param7=param7,
    )

    ret = client.command.long.call(req)
    _check_ret(ctx, ret, client.verbose)


def do_int(args):
    try:
        ret = command.int(frame=args.frame,
                          command=args.command,
                          current=int(args.current),
                          autocontinue=int(args.autocontinue),
                          param1=args.param1,
                          param2=args.param2,
                          param3=args.param3,
                          param4=args.param4,
                          x=args.x,
                          y=args.y,
                          z=args.z)
    except rospy.ServiceException as ex:
        fault(ex)

    if not ret.success:
        fault("Request failed. Check mavros logs.")

    print_if(args.verbose, "Request done.")


def do_set_home(args):
    try:
        ret = command.set_home(current_gps=args.current_gps,
                               latitude=args.latitude,
                               longitude=args.longitude,
                               altitude=args.altitude)
    except rospy.ServiceException as ex:
        fault(ex)

    _check_ret(args, ret)


def do_takeoff(args):
    try:
        ret = command.takeoff(min_pitch=args.min_pitch,
                              yaw=args.yaw,
                              latitude=args.latitude,
                              longitude=args.longitude,
                              altitude=args.altitude)
    except rospy.ServiceException as ex:
        fault(ex)

    _check_ret(args, ret)


def do_land(args):
    try:
        ret = command.land(min_pitch=0.0,
                           yaw=args.yaw,
                           latitude=args.latitude,
                           longitude=args.longitude,
                           altitude=args.altitude)
    except rospy.ServiceException as ex:
        fault(ex)

    _check_ret(args, ret)


def _find_gps_topic(args, op_name):
    # XXX: since 0.13 global position always exists. need redo that.
    global_fix = mavros.get_topic('global_position', 'global')
    gps_fix = mavros.get_topic('global_position', 'raw', 'fix')

    topics = rospy.get_published_topics()
    # need find more elegant way
    if len([topic for topic, type_ in topics if topic == global_fix]):
        return global_fix
    elif len([topic for topic, type_ in topics if topic == gps_fix]):
        print_if(args.verbose, "Use GPS_RAW_INT data!")
        return gps_fix
    elif args.any_gps:
        t = [
            topic for topic, type_ in topics
            if type_ == 'sensor_msgs/NavSatFix'
        ]
        if len(t) > 0:
            print("Use", t[0], "NavSatFix topic for", op_name)
            return t[0]

    return None


def do_takeoff_cur_gps(args):
    done_evt = threading.Event()

    def fix_cb(fix):
        print("Taking-off from current coord: Lat:", fix.latitude, "Long:",
              fix.longitude)
        print_if(args.verbose, "With desired Altitude:", args.altitude, "Yaw:",
                 args.yaw, "Pitch angle:", args.min_pitch)

        try:
            ret = command.takeoff(min_pitch=args.min_pitch,
                                  yaw=args.yaw,
                                  latitude=fix.latitude,
                                  longitude=fix.longitude,
                                  altitude=args.altitude)
        except rospy.ServiceException as ex:
            fault(ex)

        _check_ret(args, ret)
        done_evt.set()

    topic = _find_gps_topic(args, "takeoff")
    if topic is None:
        fault("NavSatFix topic not exist")

    sub = rospy.Subscriber(topic, NavSatFix, fix_cb)
    if not done_evt.wait(10.0):
        fault("Something went wrong. Topic timed out.")


def do_land_cur_gps(args):
    done_evt = threading.Event()

    def fix_cb(fix):
        print("Landing on current coord: Lat:", fix.latitude, "Long:",
              fix.longitude)
        print_if(args.verbose, "With desired Altitude:", args.altitude, "Yaw:",
                 args.yaw)

        try:
            ret = command.land(min_pitch=0.0,
                               yaw=args.yaw,
                               latitude=fix.latitude,
                               longitude=fix.longitude,
                               altitude=args.altitude)
        except rospy.ServiceException as ex:
            fault(ex)

        _check_ret(args, ret)
        done_evt.set()

    topic = _find_gps_topic(args, "landing")
    if topic is None:
        fault("NavSatFix topic not exist")

    sub = rospy.Subscriber(topic, NavSatFix, fix_cb)
    if not done_evt.wait(10.0):
        fault("Something went wrong. Topic timed out.")


def do_trigger_control(args):
    try:
        ret = command.trigger_control(trigger_enable=args.trigger_enable,
                                      cycle_time=args.cycle_time)
    except rospy.ServiceException as ex:
        fault(ex)

    _check_ret(args, ret)


def main():

    int_args = subarg.add_parser('int', help="Send any command (COMMAND_INT)")
    int_args.set_defaults(func=do_int)
    int_args.add_argument('-c',
                          '--current',
                          action='store_true',
                          help="Is current?")
    int_args.add_argument('-a',
                          '--autocontinue',
                          action='store_true',
                          help="Is autocontinue?")
    int_args.add_argument('-f',
                          '--frame',
                          type=int,
                          default=3,
                          help="Frame Code (default: %(default)s)")
    int_args.add_argument('command', type=int, help="Command Code")
    int_args.add_argument('param1', type=float, help="param1")
    int_args.add_argument('param2', type=float, help="param2")
    int_args.add_argument('param3', type=float, help="param3")
    int_args.add_argument('param4', type=float, help="param4")
    int_args.add_argument('x', type=int, help="Latitude in deg*1E7 or X*1E4 m")
    int_args.add_argument('y',
                          type=int,
                          help="Longitude in deg*1E7 or Y*1E4 m")
    int_args.add_argument('z',
                          type=float,
                          help="Altitude in m, depending on frame")

    # Note: arming service provided by mavsafety

    set_home_args = subarg.add_parser('sethome',
                                      help="Request change home position")
    set_home_args.set_defaults(func=do_set_home)
    set_home_args.add_argument(
        '-c',
        '--current-gps',
        action='store_true',
        help="Use current GPS location (use 0 0 0 for location args)")
    set_home_args.add_argument('latitude', type=float, help="Latitude")
    set_home_args.add_argument('longitude', type=float, help="Longitude")
    set_home_args.add_argument('altitude', type=float, help="Altitude")

    takeoff_args = subarg.add_parser('takeoff', help="Request takeoff")
    takeoff_args.set_defaults(func=do_takeoff)
    takeoff_args.add_argument('min_pitch', type=float, help="Min pitch")
    takeoff_args.add_argument('yaw', type=float, help="Desired Yaw")
    takeoff_args.add_argument('latitude', type=float, help="Latitude")
    takeoff_args.add_argument('longitude', type=float, help="Longitude")
    takeoff_args.add_argument('altitude', type=float, help="Altitude")

    land_args = subarg.add_parser('land', help="Request land")
    land_args.set_defaults(func=do_land)
    land_args.add_argument('yaw', type=float, help="Desired Yaw")
    land_args.add_argument('latitude', type=float, help="Latitude")
    land_args.add_argument('longitude', type=float, help="Longitude")
    land_args.add_argument('altitude', type=float, help="Altitude")

    takeoff_cur_args = subarg.add_parser(
        'takeoffcur', help="Request takeoff from current GPS coordinates")
    takeoff_cur_args.set_defaults(func=do_takeoff_cur_gps)
    takeoff_cur_args.add_argument(
        '-a',
        '--any-gps',
        action="store_true",
        help="Try to find GPS topic (warn: could be dangerous!)")
    takeoff_cur_args.add_argument('min_pitch', type=float, help="Min pitch")
    takeoff_cur_args.add_argument('yaw', type=float, help="Desired Yaw")
    takeoff_cur_args.add_argument('altitude', type=float, help="Altitude")

    land_cur_args = subarg.add_parser(
        'landcur', help="Request land on current GPS coordinates")
    land_cur_args.set_defaults(func=do_land_cur_gps)
    land_cur_args.add_argument(
        '-a',
        '--any-gps',
        action="store_true",
        help="Try to find GPS topic (warn: could be dangerous!)")
    land_cur_args.add_argument('yaw', type=float, help="Desired Yaw")
    land_cur_args.add_argument('altitude', type=float, help="Altitude")

    trigger_ctrl_args = subarg.add_parser(
        'trigger_control',
        help="Control onboard camera triggering system (PX4)")
    trigger_ctrl_args.set_defaults(func=do_trigger_control)
    trigger_en_group = trigger_ctrl_args.add_mutually_exclusive_group()
    trigger_en_group.add_argument('-e',
                                  '--enable',
                                  dest='trigger_enable',
                                  action='store_true',
                                  default=True,
                                  help="Enable camera trigger (default)")
    trigger_en_group.add_argument('-d',
                                  '--disable',
                                  dest='trigger_enable',
                                  action='store_false',
                                  help="Disable camera trigger")
    trigger_ctrl_args.add_argument(
        '-c',
        '--cycle_time',
        default=0.0,
        type=float,
        required=False,
        help="Camera trigger cycle time. Zero to use current onboard value")

    args = parser.parse_args(rospy.myargv(argv=sys.argv)[1:])

    rospy.init_node("mavcmd", anonymous=True)
    mavros.set_namespace(args.mavros_ns)

    if args.wait:
        wait_fcu_connection()

    args.func(args)


if __name__ == '__main__':
    main()
