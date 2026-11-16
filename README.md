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
| Driver de hardware real (`rslidar_sdk` como submódulo) | ✅ verificado con el sensor en la ZED Box Orin NX (Ubuntu 24.04, Jazzy, aarch64): nube de 57 600 puntos, `frame_id` correcto, 10.00 Hz con suscriptor `reliable` |

## Contenido

```
description/sensor.urdf.j2        # link + joint + sensor gpu_lidar (Jinja2)
bringup/config/sensor_params.yaml # parámetros operativos, de simulación y del driver
bringup/launch/general.launch.py  # driver real (sim:=false) + RViz opcional
bringup/launch/real.launch.py     # wrapper sin RViz para robot.launch.py
bringup/launch/test.launch.py     # prueba en banco: driver + RViz solo con la nube + monitor de frecuencia
bringup/config/rslidar_sdk_config.yaml.j2 # config de rslidar_sdk (se renderiza al lanzar)
third_party/rslidar_sdk/          # submódulo git (RoboSense, con rs_driver dentro)
third_party/rslidar_msg/          # submódulo git (RoboSense)
bringup/rviz/rs_helios_5515.rviz  # RViz del robot completo: nube del Helios y scan del SICK (Fixed Frame odom)
bringup/rviz/rs_helios_5515_test.rviz # RViz independiente (solo la nube, Fixed Frame = frame del LiDAR)
src/cloud_rate_monitor.cpp        # herramienta C++ para medir la frecuencia real
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

## Hardware real

### Instalación (autocontenida, x86_64 y aarch64/Jetson)

`rslidar_sdk` y `rslidar_msg` (RoboSense) van como **submódulos git** en `third_party/`
(`rslidar_sdk` 1.5.20 según su `package.xml`, commit `8b4b4b7`, que a su vez trae `rs_driver` como submódulo). No se modifican:
el `CMakeLists.txt` de este paquete los compila con `ExternalProject` usando su CMake
original (colcon no descubre paquetes anidados dentro de otro paquete) y los instala en el
prefijo de este paquete. Después `ros2 run rslidar_sdk rslidar_sdk_node` funciona como en
una instalación normal. No hace falta tocar `COMPILE_METHOD` ni copiar `package_ros2.xml`
(la versión 1.5.20 ya es ROS 2 de serie).

```bash
git clone --recurse-submodules <repo> <ws>/src/caddy_ai2_ros2_sensors_rs_helios_5515
# si ya está clonado:  git submodule update --init --recursive
cd <ws> && colcon build --symlink-install --packages-select caddy_ai2_ros2_sensors_rs_helios_5515
```

- Si falta algún submódulo, CMake falla indicando el comando anterior. Si este paquete va
  dentro de otro repo, ese repo también tiene que inicializar los submódulos.
- `libpcap-dev` es opcional: si está instalado se habilita la reproducción de pcap
  (`msg_source: 3`); si no, se compila sin ella.
- Dependencias del sistema: solo ROS 2 (`rclcpp`, `sensor_msgs`, `yaml-cpp`, `rosidl`).
- Los submódulos apuntan a **forks propios** (`racarla96/rslidar_sdk`, `rslidar_msg`, `rs_driver`), no al upstream de RoboSense, para que el paquete siga instalable aunque el original cambie o desaparezca. El `.gitmodules` de `rslidar_sdk` usa URL relativa (`../rs_driver.git`), así que su `rs_driver` se resuelve solo al fork. Upstream: <https://github.com/RoboSense-LiDAR>.
- Para actualizar el SDK: `git -C third_party/rslidar_sdk checkout <tag>` + `git submodule update --init --recursive` y commit.

ZED Box Orin NX: **probado** en aarch64 con Ubuntu 24.04 y ROS 2 Jazzy nativo (sin contenedor);
`colcon build` tarda ~1 min la primera vez y compila sin errores. La CPU del driver es
~40 % de un núcleo. Con JetPack 6 (Ubuntu 22.04, Humble) haría falta Ubuntu 24.04 o un
contenedor `ros:jazzy`. Si el workspace se copia con `rsync` en vez de clonarlo, hay que
incluir `third_party/` (submódulos).

### Red: 10.10.10.x

De fábrica el LiDAR es `192.168.1.200` y envía a `192.168.1.102`. Para usar 10.10.10.x:

1. PC temporalmente en 192.168.1.102/24: `sudo ip addr add 192.168.1.102/24 dev <iface>`.
2. Abrir `http://192.168.1.200` (o RSView): LiDAR → `10.10.10.200`, destino de datos →
   `10.10.10.102`. Guardar y reiniciar el LiDAR (los nombres de campos varían según firmware).
3. PC persistente:
   `nmcli con mod <conexion> ipv4.method manual ipv4.addresses 10.10.10.102/24 && nmcli con up <conexion>`.

Alternativa: dejar el LiDAR como está y añadir al PC la IP secundaria 192.168.1.102/24.
Con `host_address: 0.0.0.0` el driver recibe UDP por cualquier IP; basta con que el destino
configurado en el LiDAR coincida con la IP del PC.

### Lanzar

```bash
ros2 launch caddy_ai2_ros2_sensors_rs_helios_5515 general.launch.py sim:=false namespace:=<ns>
```

Lanza `rslidar_sdk_node` con `lidar_type: RSHELIOS` (32 canales) y puertos MSOP 6699 /
DIFOP 7788 (`sensor_params.yaml`, sección `driver`). El launch renderiza
`bringup/config/rslidar_sdk_config.yaml.j2` en un fichero temporal con el topic
`/<ns>/rs_helios_5515/points` y `ros_frame_id: lidar_3d_rs_helios_5515_link`, igual que la
simulación. Sin LiDAR conectado el nodo arranca y avisa con `ERRCODE_MSOPTIMEOUT`.

### Prueba en banco (ver la nube en RViz)

Con solo el LiDAR conectado, sin descripción del robot, TF ni odometría:

```bash
ros2 launch caddy_ai2_ros2_sensors_rs_helios_5515 test.launch.py
```

Arranca el driver, RViz con solo la nube (Fixed Frame = `lidar_3d_rs_helios_5515_link`,
coloreada por altura, QoS `Reliable`) y `cloud_rate_monitor`, que imprime cada 5 s los Hz,
huecos y latencia. El topic y el frame de RViz se rellenan solos a partir de `namespace` y
`sensor_params.yaml`, así que siempre coinciden con lo que publica el driver.

Argumentos: `namespace` (vacío por defecto → `/rs_helios_5515/points`), `rviz:=false`,
`monitor:=false`, `reliability:=reliable|best_effort`, `host_address`.

**Driver ya en marcha.** Antes de lanzar, `test.launch.py` busca un `rslidar_sdk_node` vivo
(dos drivers se disputan el puerto UDP 6699) y actúa según `existing_driver`:

| Valor | Qué hace |
|---|---|
| `restart` (por defecto) | Lo cierra (SIGINT, y SIGKILL si no responde) y lanza uno nuevo |
| `reuse` | No lanza otro driver; abre solo RViz y el monitor sobre el que ya hay (el `namespace` debe coincidir con el suyo) |
| `abort` | No toca nada y termina con un error que indica el PID |

Imprime el PID y el tiempo que llevaba en marcha.

Para parar: `Ctrl-C` en la terminal del launch, o desde cualquier terminal:

```bash
ros2 run caddy_ai2_ros2_sensors_rs_helios_5515 stop_helios.sh        # -n solo lista, -t 8 segundos de espera
```

`rslidar_sdk_node` ignora `SIGTERM`, y lo lanzado en segundo plano desde un shell no
interactivo (ssh, `nohup ... &`) también hereda un `SIGINT` ignorado, así que ni `pkill` ni
`Ctrl-C` bastan y quedarían procesos huérfanos (dos drivers se disputan el puerto 6699).
`stop_helios.sh` manda `SIGINT` al launch, espera y hace `kill -9` a lo que quede (driver,
RViz, monitor). El LiDAR sigue alimentado; solo se para el driver.

Por SSH en un equipo con monitor (p. ej. la ZED Box): `DISPLAY=:0 ros2 launch ... test.launch.py`.
Sin monitor, `rviz:=false` y mirar el monitor de frecuencia en la consola, o abrir RViz en otro
PC de la misma red y `ROS_DOMAIN_ID` (la nube son ~9 MB/s).

El `rs_helios_5515.rviz` de `general.launch.py` es el del robot completo: espera el namespace
`caddy_ai2` y el frame `odom`, por eso no sirve para probar el sensor suelto.

### Verificación

- `ros2 topic hz /<ns>/rs_helios_5515/points` → ~10 Hz.
- RViz con Fixed Frame `lidar_3d_rs_helios_5515_link` (lo abre el launch por defecto).
- Sin datos: `sudo tcpdump -i <iface> udp port 6699`. Si llegan paquetes pero no hay nube,
  revisar `lidar_type` y el firewall.
- Con buffers UDP pequeños pueden perderse paquetes: `sudo sysctl -w net.core.rmem_max=26214400`.

### Medir la frecuencia real: `cloud_rate_monitor`

`ros2 topic hz` es un suscriptor Python y con nubes de ~920 KB puede ir más lento que el
publicador; como el topic del driver es `RELIABLE`, el número que da depende del
suscriptor. Para medir de verdad hay un suscriptor C++ ligero en este paquete:

```bash
ros2 run caddy_ai2_ros2_sensors_rs_helios_5515 cloud_rate_monitor --ros-args \
  -p topic:=/caddy_ai2/rs_helios_5515/points -p reliability:=reliable
```

Cada `window_s` (5 s) imprime: Hz y % del esperado, periodo mín/máx, **huecos** (periodos
> `gap_factor` × esperado, con una estimación de nubes perdidas), puntos por nube, latencia
(llegada − `header.stamp`) y `frame_id`. Parámetros: `topic`, `reliability`
(`best_effort`|`reliable`), `depth`, `window_s`, `expected_hz` (10), `gap_factor` (1.5).

Medido en la ZED Box Orin NX (Ubuntu 24.04, Jazzy, Fast DDS, MAXN), mismo equipo que el
driver, nube de 57 600 puntos:

| Suscriptor | Frecuencia |
|---|---|
| `reliable` | 10.00 Hz, 0 huecos, latencia 4–7 ms |
| `best_effort` | 6–7 Hz, huecos de 0.5 s |

Conclusión: el driver y el LiDAR dan 10 Hz. Un suscriptor `best_effort` (por ejemplo con
`SensorDataQoS`) pierde nubes de este tamaño en la entrega por DDS; usar `reliable` o
revisar los buffers/transporte de Fast DDS.

## Pendiente

- Suscriptores con QoS `best_effort` (p. ej. `SensorDataQoS`) pierden nubes de este tamaño por DDS (6–7 Hz en la misma máquina). Fijar el QoS de los consumidores en `reliable` o ajustar Fast DDS, y repetir la medida entre la ZED Box y el LattePanda.
- El `rs_helios_5515.rviz` del robot completo usa `Best Effort`; revisarlo con lo anterior.
- Medir la pose real de montaje y actualizar `robot_params.yaml`.
- Malla oficial del sensor.
