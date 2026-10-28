# caddy_ai2_ros2_sensors_rs_helios_5515

LiDAR 3D **RoboSense RS-Helios-5515** para el Caddy AI2, siguiendo la estructura de
`caddy_ai2_ros2_sensors_sick_lms_291`.

Ficha: <https://www.roscomponents.com/es/producto/rs-helios-5515-es/>

| | |
|---|---|
| Canales | 32 |
| FOV | 360° horizontal, 70° vertical (-55° a +15°) |
| Frecuencia | 10 Hz (600 rpm) o 20 Hz (1200 rpm) |
| Puntos/s | 576 000 (retorno simple) / 1 152 000 (doble) |
| Rango | 0.1 m a 150 m, precisión ±2 cm (1–100 m) |
| Tamaño / peso | Ø100 × 100 mm / ~1 kg |

## Estado

| Parte | Estado |
|---|---|
| Simulación (Gazebo Harmonic `gpu_lidar` → `PointCloud2`) | ✅ |
| Driver de hardware real (`rslidar_sdk` / `rs_driver`) | ⏳ pendiente |

## Contenido

```
description/sensor.urdf.j2        # link + joint + sensor gpu_lidar (Jinja2)
bringup/config/sensor_params.yaml # parámetros operativos y de simulación
```

El modelo visual es un **cilindro provisional** (no hay malla oficial en el repo).

## Integración en el robot

Este paquete no se lanza solo: lo consume la descripción del robot.

1. **`caddy_ai2_ros2_description/bringup/config/robot_params.yaml`** — entrada
   `lidar_3d_rs_helios_5515` (`type: lidar_3d`) con la pose respecto a `base_link`.
   Provisional: techo, centrado, `z = 1.4 m`. Medir en el vehículo real.
2. **`caddy_ai2_ros2_gazebo_simulation/bringup/launch/spawn_robot.launch.py`** — rama
   `lidar_3d` que pasa los parámetros de simulación a la plantilla.
3. **`caddy_ai2_ros2_gazebo_simulation/bringup/config/gz_msg_bridge.yaml.j2`** — puente
   `gz.msgs.PointCloudPacked` → `sensor_msgs/msg/PointCloud2`.

## Topic

```
/<namespace>/rs_helios_5515/points   sensor_msgs/msg/PointCloud2
frame_id: lidar_3d_rs_helios_5515_link
```

## Parámetros de simulación

`bringup/config/sensor_params.yaml`, sección `simulation`:

- `horizontal_samples: 1800` → 0.2° de resolución (576 000 pts/s ÷ 10 Hz ÷ 32 canales).
  Son 57 600 rayos por vuelta; si la GPU va justa, bájalo (p. ej. 900).
- Los 32 canales se reparten **uniformemente** en -55°…+15°. El sensor real tiene una
  distribución no uniforme.
- Ruido gaussiano σ = 2 cm (precisión de la hoja de datos).

## Pendiente

- Driver real: envolver `rslidar_sdk` en un `general.launch.py` (`sim:=false`).
- Malla oficial del sensor.
- Medir la posición real de montaje.
