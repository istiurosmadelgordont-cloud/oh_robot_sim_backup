cmake_minimum_required(VERSION 3.8)
project(robot_sim_dto)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(std_msgs REQUIRED)
find_package(std_srvs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)


rosidl_generate_interfaces(${PROJECT_NAME}
    "msg/PixelPosition.msg"
    "msg/Point2D.msg"
    "msg/Points.msg"
    "msg/Pose2D.msg"

    "srv/GetPose2D.srv"
    "srv/GetPose2DCov.srv"
    "srv/MoveArm.srv"
    "srv/SetBox.srv"
    "srv/SetColorRGBA.srv"
    "srv/SetFloat64.srv"
    "srv/SetFloat64List.srv"
    "srv/SetInt64.srv"
    "srv/SetPoint.srv"
    "srv/SetPose2D.srv"
    "srv/SetStringList.srv"
    "srv/SetString.srv"
    "srv/SetStringBool.srv"
  DEPENDENCIES std_msgs std_srvs geometry_msgs builtin_interfaces 
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
