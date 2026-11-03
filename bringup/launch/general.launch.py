import os
import tempfile

import yaml
from jinja2 import Environment, FileSystemLoader
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('sim',       default_value='false',
                              description='Only false is supported here: in simulation the sensor is '
                                          'spawned by caddy_ai2_ros2_gazebo_simulation.'),
        DeclareLaunchArgument('rviz',      default_value='true',
                              description='Launch RViz2 with bringup/rviz/rs_helios_5515.rviz.'),
        DeclareLaunchArgument('namespace', default_value='',
                              description='ROS 2 namespace for the points topic.'),
        DeclareLaunchArgument('host_address', default_value='',
                              description='Local address to listen on. Empty reads sensor_params.yaml.'),
        OpaqueFunction(function=_launch),
    ])


def _launch(context, *args, **kwargs):
    lc = context.launch_configurations

    if lc['sim'].lower() == 'true':
        raise RuntimeError(
            'caddy_ai2_ros2_sensors_rs_helios_5515 general.launch.py only drives the real '
            'LiDAR (sim:=false). In simulation the sensor is spawned by '
            'caddy_ai2_ros2_gazebo_simulation.')

    use_rviz  = lc['rviz'].lower() == 'true'
    namespace = lc['namespace'].strip('/')

    pkg_share = get_package_share_directory('caddy_ai2_ros2_sensors_rs_helios_5515')
    with open(os.path.join(pkg_share, 'bringup', 'config', 'sensor_params.yaml')) as f:
        params = yaml.safe_load(f)

    drv = params['driver']
    points_topic = f'/{namespace}/rs_helios_5515/points' if namespace else '/rs_helios_5515/points'

    cfg_env = Environment(
        loader=FileSystemLoader(os.path.join(pkg_share, 'bringup', 'config')),
        keep_trailing_newline=True,
    )
    cfg_str = cfg_env.get_template('rslidar_sdk_config.yaml.j2').render(
        lidar_type=drv['lidar_type'],
        msop_port=drv['msop_port'],
        difop_port=drv['difop_port'],
        host_address=lc['host_address'] or drv['host_address'],
        frame_id=params['hardware']['frame_id'],
        points_topic=points_topic,
    )
    tmp_cfg = tempfile.NamedTemporaryFile(
        mode='w', suffix='.yaml', prefix='rs_helios_5515_rslidar_sdk_', delete=False)
    tmp_cfg.write(cfg_str)
    tmp_cfg.close()

    # rslidar_sdk_node is built from the vendored submodule (see CMakeLists.txt).
    nodes = [
        Node(
            package='rslidar_sdk',
            executable='rslidar_sdk_node',
            name='rslidar_sdk_node',
            output='screen',
            parameters=[{'config_path': tmp_cfg.name}],
        ),
    ]

    if use_rviz:
        nodes.append(Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='log',
            arguments=['-d', os.path.join(pkg_share, 'bringup', 'rviz', 'rs_helios_5515.rviz')],
        ))

    return nodes
