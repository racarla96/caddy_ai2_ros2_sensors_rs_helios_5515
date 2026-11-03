cmake_minimum_required(VERSION 3.8)
project(caddy_ai2_ros2_sensors_rs_helios_5515)

find_package(ament_cmake REQUIRED)

# --- Vendored RoboSense driver (git submodules, built unmodified) ---------------------------
# colcon does not discover packages nested inside another package, so rslidar_msg and
# rslidar_sdk are built here with ExternalProject using their own upstream CMakeLists, and
# installed into this package's prefix. Afterwards `ros2 run rslidar_sdk rslidar_sdk_node`
# works as with a normal workspace install.
include(ExternalProject)

set(RSLIDAR_SDK_DIR ${CMAKE_CURRENT_SOURCE_DIR}/third_party/rslidar_sdk)
set(RSLIDAR_MSG_DIR ${CMAKE_CURRENT_SOURCE_DIR}/third_party/rslidar_msg)
foreach(dir ${RSLIDAR_SDK_DIR}/CMakeLists.txt
            ${RSLIDAR_SDK_DIR}/src/rs_driver/CMakeLists.txt
            ${RSLIDAR_MSG_DIR}/CMakeLists.txt)
  if(NOT EXISTS ${dir})
    message(FATAL_ERROR
      "Missing ${dir}. Run: git submodule update --init --recursive")
  endif()
endforeach()

# PCAP replay (msg_source: 3) needs libpcap-dev; enable it only when it is installed.
find_path(PCAP_HEADER pcap.h)
if(PCAP_HEADER)
  set(RS_PCAP_ARGS "")
else()
  message(STATUS "libpcap-dev not found: building rslidar_sdk without PCAP replay")
  set(RS_PCAP_ARGS -DDISABLE_PCAP_PARSE=ON "-DCMAKE_CXX_FLAGS=-DDISABLE_PCAP_PARSE")
endif()

set(RS_STAGE ${CMAKE_CURRENT_BINARY_DIR}/rs_stage)
set(RS_PREFIX_PATH "${RS_STAGE}\;$ENV{CMAKE_PREFIX_PATH}")
string(REPLACE ":" "\;" RS_PREFIX_PATH "${RS_PREFIX_PATH}")
set(RS_COMMON_ARGS
  -DCMAKE_INSTALL_PREFIX=${RS_STAGE}
  -DCMAKE_BUILD_TYPE=Release
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON)

ExternalProject_Add(rslidar_msg_ep
  SOURCE_DIR ${RSLIDAR_MSG_DIR}
  BINARY_DIR ${CMAKE_CURRENT_BINARY_DIR}/rslidar_msg_build
  CMAKE_ARGS ${RS_COMMON_ARGS}
  INSTALL_DIR ${RS_STAGE})

ExternalProject_Add(rslidar_sdk_ep
  DEPENDS rslidar_msg_ep
  SOURCE_DIR ${RSLIDAR_SDK_DIR}
  BINARY_DIR ${CMAKE_CURRENT_BINARY_DIR}/rslidar_sdk_build
  CMAKE_ARGS ${RS_COMMON_ARGS} ${RS_PCAP_ARGS}
    "-DCMAKE_PREFIX_PATH=${RS_PREFIX_PATH}"
  INSTALL_DIR ${RS_STAGE})

install(DIRECTORY ${RS_STAGE}/ DESTINATION . USE_SOURCE_PERMISSIONS)

install(DIRECTORY bringup description
  DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
