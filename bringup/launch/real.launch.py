import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    """Thin wrapper used by robot.launch.py to include the real Helios driver."""
    pkg_share = get_package_share_directory('caddy_ai2_ros2_sensors_rs_helios_5515')
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value=''),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_share, 'bringup', 'launch', 'general.launch.py')
            ),
            launch_arguments={
                'sim': 'false',
                'rviz': 'false',
                'namespace': LaunchConfiguration('namespace'),
            }.items(),
        ),
    ])
