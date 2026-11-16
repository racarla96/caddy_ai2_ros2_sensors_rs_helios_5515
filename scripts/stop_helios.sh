#!/usr/bin/env bash
# Stop the RS-Helios-5515 driver and everything test.launch.py / general.launch.py started
# (rslidar_sdk_node, rviz2, cloud_rate_monitor), leaving no orphans.
#
# Why a script: rslidar_sdk_node ignores SIGTERM, and processes started in the background
# from a non-interactive shell (ssh, nohup ... &) also inherit an ignored SIGINT, so neither
# Ctrl-C nor pkill is enough. This sends SIGINT to the launch (clean path), waits, and then
# SIGKILLs whatever is left.
#
#   ros2 run caddy_ai2_ros2_sensors_rs_helios_5515 stop_helios.sh [-t SECONDS] [-n]
#     -t SECONDS  how long to wait for the launch to close its children (default 8)
#     -n          dry run: only list what is running
set -u

TIMEOUT=8
DRY=0
while getopts "t:nh" opt; do
  case "$opt" in
    t) TIMEOUT="$OPTARG" ;;
    n) DRY=1 ;;
    *) sed -n '2,13p' "$0"; exit 0 ;;
  esac
done

NAMES=(rslidar_sdk_node rviz2 cloud_rate_monitor)
# Process names are truncated to 15 chars in /proc/<pid>/comm, so match with pgrep -x on that.
comm15() { printf '%s' "${1:0:15}"; }

list_workers() {
  local n p
  for n in "${NAMES[@]}"; do
    for p in $(pgrep -x "$(comm15 "$n")" 2>/dev/null); do
      [ "$p" = "$$" ] || echo "$p"
    done
  done | sort -un
}

list_launches() {
  # `ros2 launch <pkg> ...` of this package (not this script, not `ros2 run`).
  pgrep -f "ros2 launch caddy_ai2_ros2_sensors_rs_helios_5515" 2>/dev/null | grep -vx "$$" || true
}

show() {
  local p
  for p in "$@"; do
    ps -o pid=,etimes=,comm= -p "$p" 2>/dev/null | awk '{printf "  pid %s  (%ss)  %s\n",$1,$2,$3}'
  done
}

launches=$(list_launches)
workers=$(list_workers)
if [ -z "$launches" ] && [ -z "$workers" ]; then
  echo "Nothing running: no Helios launch, driver, RViz or monitor."
  exit 0
fi
echo "Running now:"
[ -n "$launches" ] && { echo " launch:"; show $launches; }
[ -n "$workers" ]  && { echo " processes:"; show $workers; }
[ "$DRY" = 1 ] && exit 0

# 1) Clean path: SIGINT to the launch (same as Ctrl-C).
for p in $launches; do kill -INT "$p" 2>/dev/null; done
waited=0
while [ "$waited" -lt "$TIMEOUT" ] && [ -n "$(list_workers)" ]; do
  sleep 1; waited=$((waited + 1))
done

# 2) Whatever is left ignores SIGINT/SIGTERM: SIGKILL.
left=$(list_workers)
if [ -n "$left" ]; then
  echo "Still alive after ${waited}s, sending SIGKILL:"; show $left
  for p in $left; do kill -9 "$p" 2>/dev/null; done
  sleep 1
else
  echo "Closed cleanly by the launch in ${waited}s."
fi
for p in $(list_launches); do kill -9 "$p" 2>/dev/null; done

final=$(list_workers)
if [ -n "$final" ]; then
  echo "ERROR: could not stop:"; show $final; exit 1
fi
echo "Stopped. The LiDAR stays powered; only the driver is down."
