cmake_minimum_required(VERSION 3.8)
project(control_svc)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
set(COMMON_DEPS
  rclcpp
  moveit_core
  moveit_ros_planning
  moveit_ros_planning_interface
  control_msgs
  nav2_msgs
  sensor_msgs
  std_msgs
  cv_bridge
  OpenCV

  control_stubs
  robot_sim_common
  robot_sim_dto
  geometry_msgs
)

set(POSE_MGR_DEPS
  robot_sim_common
  robot_sim_dto
  geometry_msgs
  tf2
  tf2_geometry_msgs
)

set(ALL_DEPS ${COMMON_DEPS} ${POSE_MGR_DEPS})

find_package(ament_cmake REQUIRED)

foreach(dep IN ITEMS ${ALL_DEPS})
  find_package(${dep} REQUIRED)
endforeach()

set(
  SVC_SRCS
  src/sensing_service.ros2.cpp
  src/core_service.ros2.cpp
  src/mobility_ai_service.ros2.cpp
)

set(SVC_MGR svc_mgr)
set(
  SVC_MGR_SRCS
  src/service_manager.ros2.cpp
  ${SVC_SRCS}
)

set(POSE_MGR pose_mgr)
set(
  POSE_MGR_SRCS
  src/pose_manager.ros2.cpp
)

add_library(${PROJECT_NAME} SHARED ${SVC_SRCS})
# use $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include> if external package want to use out headers
target_include_directories(
  ${PROJECT_NAME}
  PUBLIC
  ${CMAKE_SOURCE_DIR}/include
)

add_executable(${SVC_MGR} ${SVC_MGR_SRCS})
target_include_directories(
  ${SVC_MGR}
  PUBLIC
  ${CMAKE_SOURCE_DIR}/include
)

add_executable(${POSE_MGR} ${POSE_MGR_SRCS})
target_include_directories(
  ${POSE_MGR}
  PUBLIC
  ${CMAKE_SOURCE_DIR}/include
)

ament_target_dependencies(${PROJECT_NAME} ${COMMON_DEPS})
target_link_libraries(${PROJECT_NAME} grpc grpc++ protobuf)
ament_target_dependencies(${SVC_MGR} ${COMMON_DEPS})
target_link_libraries(${SVC_MGR} grpc grpc++ protobuf)
ament_target_dependencies(${POSE_MGR} ${POSE_MGR_DEPS})

install(TARGETS ${PROJECT_NAME} ${SVC_MGR} ${POSE_MGR} DESTINATION lib/${PROJECT_NAME})

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)


if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
