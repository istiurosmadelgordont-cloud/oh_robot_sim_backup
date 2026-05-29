cmake_minimum_required(VERSION 3.8)
project(moveit2c)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(moveit REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(moveit_visual_tools REQUIRED)
find_package(robot_sim_dto REQUIRED)

set(PROJ_NAME car_arm_controller)

add_executable(${PROJ_NAME} src/car_arm_controller.cpp)
add_executable(test_jog src/test_jog.cpp)

ament_target_dependencies(${PROJ_NAME} robot_sim_dto rclcpp moveit geometry_msgs moveit_visual_tools)
ament_target_dependencies(test_jog rclcpp geometry_msgs)


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


install(TARGETS ${PROJ_NAME} test_jog DESTINATION lib/${PROJECT_NAME})
