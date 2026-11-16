"""Bench test of the real Helios: driver + RViz (cloud only) + rate monitor.

Standalone: needs no robot description, TF or odom. The RViz Fixed Frame is the LiDAR's own
frame, and the topic/frame in the RViz config are filled in from `namespace` and
sensor_params.yaml, so it always matches what the driver publishes.

    ros2 launch caddy_ai2_ros2_sensors_rs_helios_5515 test.launch.py
    ros2 launch caddy_ai2_ros2_sensors_rs_helios_5515 test.launch.py namespace:=caddy_ai2 monitor:=false

In a remote (ssh) session on a machine with a monitor, run with DISPLAY=:0.
"""
import os
import tempfile

import yaml
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

PKG = 'caddy_ai2_ros2_sensors_rs_helios_5515'


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

    actions = [
        # Driver only: RViz is opened below with the standalone config.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_share, 'bringup', 'launch', 'general.launch.py')),
            launch_arguments={
                'sim': 'false',
                'rviz': 'false',
                'namespace': namespace,
                'host_address': lc['host_address'],
            }.items()),
    ]

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
