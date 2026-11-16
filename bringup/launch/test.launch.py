"""Bench test of the real Helios: driver + RViz (cloud only) + rate monitor.

Standalone: needs no robot description, TF or odom. The RViz Fixed Frame is the LiDAR's own
frame, and the topic/frame in the RViz config are filled in from `namespace` and
sensor_params.yaml, so it always matches what the driver publishes.

    ros2 launch caddy_ai2_ros2_sensors_rs_helios_5515 test.launch.py
    ros2 launch caddy_ai2_ros2_sensors_rs_helios_5515 test.launch.py namespace:=caddy_ai2 monitor:=false

In a remote (ssh) session on a machine with a monitor, run with DISPLAY=:0.
"""
import os
import signal
import tempfile
import time

import yaml
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

PKG = 'caddy_ai2_ros2_sensors_rs_helios_5515'
DRIVER_COMM = 'rslidar_sdk_nod'   # /proc/<pid>/comm is truncated to 15 characters


def _running_drivers():
    """Return [(pid, seconds_running)] of rslidar_sdk_node processes already alive."""
    found = []
    hz = os.sysconf('SC_CLK_TCK')
    try:
        with open('/proc/uptime') as f:
            uptime = float(f.read().split()[0])
    except OSError:
        uptime = 0.0
    for entry in os.listdir('/proc'):
        if not entry.isdigit():
            continue
        try:
            with open(f'/proc/{entry}/comm') as f:
                if f.read().strip() != DRIVER_COMM:
                    continue
            with open(f'/proc/{entry}/stat') as f:
                start_ticks = int(f.read().rsplit(')', 1)[1].split()[19])
        except (OSError, IndexError, ValueError):
            continue
        found.append((int(entry), max(0.0, uptime - start_ticks / hz)))
    return found


def _stop(pid, grace=4.0):
    """SIGINT first (what Ctrl-C sends). rslidar_sdk_node ignores SIGTERM, so go to SIGKILL."""
    for sig in (signal.SIGINT, signal.SIGKILL):
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            return True
        deadline = time.time() + (grace if sig == signal.SIGINT else 2.0)
        while time.time() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            time.sleep(0.1)
    return False


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='',
                              description='ROS 2 namespace of the points topic.'),
        DeclareLaunchArgument('rviz', default_value='true',
                              description='Open RViz2 with the standalone cloud-only config.'),
        DeclareLaunchArgument('monitor', default_value='true',
                              description='Run cloud_rate_monitor (prints Hz, gaps, latency).'),
        DeclareLaunchArgument('reliability', default_value='reliable',
                              description='QoS of the monitor: reliable or best_effort.'),
        DeclareLaunchArgument('existing_driver', default_value='restart',
                              description='What to do if an rslidar_sdk_node is already running '
                                          '(two drivers fight for UDP port 6699): '
                                          'restart = stop it and launch a fresh one; '
                                          'reuse = keep it and launch only RViz/monitor; '
                                          'abort = do nothing and exit with an error.'),
        DeclareLaunchArgument('host_address', default_value='',
                              description='Local address to listen on. Empty reads sensor_params.yaml.'),
        OpaqueFunction(function=_launch),
    ])


def _launch(context, *args, **kwargs):
    lc = context.launch_configurations
    pkg_share = get_package_share_directory(PKG)
    namespace = lc['namespace'].strip('/')
    points_topic = f'/{namespace}/rs_helios_5515/points' if namespace else '/rs_helios_5515/points'

    with open(os.path.join(pkg_share, 'bringup', 'config', 'sensor_params.yaml')) as f:
        params = yaml.safe_load(f)
    frame_id = params['hardware']['frame_id']
    expected_hz = float(params['operation']['frequency'])

    # Is a driver already running (e.g. left over from a previous test)?
    policy = lc['existing_driver'].lower()
    if policy not in ('restart', 'reuse', 'abort'):
        raise RuntimeError(f"existing_driver must be restart|reuse|abort, got '{policy}'")
    launch_driver = True
    for pid, age in _running_drivers():
        print(f'[test.launch] rslidar_sdk_node already running: pid {pid}, up {age:.0f} s')
        if policy == 'abort':
            raise RuntimeError(
                f'rslidar_sdk_node (pid {pid}) is already running. Stop it (Ctrl-C in its '
                'terminal, or kill -9) or use existing_driver:=restart|reuse.')
        if policy == 'reuse':
            print('[test.launch] existing_driver:=reuse -> not launching another driver. '
                  'The topic must match the namespace you gave.')
            launch_driver = False
        else:
            ok = _stop(pid)
            print(f"[test.launch] existing_driver:=restart -> pid {pid} {'stopped' if ok else 'COULD NOT be stopped'}")
            if not ok:
                raise RuntimeError(f'Could not stop rslidar_sdk_node pid {pid}')

    actions = []
    if launch_driver:
        # Driver only: RViz is opened below with the standalone config.
        actions.append(IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_share, 'bringup', 'launch', 'general.launch.py')),
            launch_arguments={
                'sim': 'false',
                'rviz': 'false',
                'namespace': namespace,
                'host_address': lc['host_address'],
            }.items()))

    if lc['rviz'].lower() == 'true':
        with open(os.path.join(pkg_share, 'bringup', 'rviz', 'rs_helios_5515_test.rviz')) as f:
            cfg = f.read().replace('__POINTS_TOPIC__', points_topic).replace('__FIXED_FRAME__', frame_id)
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.rviz', prefix='rs_helios_5515_test_', delete=False)
        tmp.write(cfg)
        tmp.close()
        actions.append(Node(
            package='rviz2', executable='rviz2', name='rviz2_helios_test',
            output='log', arguments=['-d', tmp.name]))

    if lc['monitor'].lower() == 'true':
        actions.append(Node(
            package=PKG, executable='cloud_rate_monitor', name='cloud_rate_monitor',
            output='screen',
            parameters=[{
                'topic': points_topic,
                'reliability': lc['reliability'],
                'expected_hz': expected_hz,
            }]))

    return actions
