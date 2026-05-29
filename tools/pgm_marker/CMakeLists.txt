cmake_minimum_required(VERSION 3.8)
project(pgm_marker)

set(RECORDER_PROJNAME pgm-rich-annotator)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(yaml-cpp REQUIRED)
find_package(Qt5 COMPONENTS Core Gui Widgets REQUIRED)
# map-recorder deps
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(OpenCV REQUIRED)

# set(UI_SRC ui/main_window.ui)

set(MOC_HEADERS
  src/map_viewer.h
  src/marker_window.h
)

set(MAIN_SRC
  src/map_viewer.cpp
  src/marker_window.cpp
  src/marker_main.cpp
)

QT5_WRAP_UI(COMPILED_FORMS ${UI_SRC})
QT5_WRAP_CPP(MOCd_HEADERS ${MOC_HEADERS})

add_executable(${PROJECT_NAME}
  ${MAIN_SRC}
  ${COMPILED_FORMS}
  ${MOCd_HEADERS}
  ${MOC_HEADERS}
)

# map annotator node
add_executable(${RECORDER_PROJNAME}
  src/map_annotator.cpp
)

target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src ${CMAKE_BINARY_DIR})

ament_target_dependencies(${PROJECT_NAME} rclcpp yaml-cpp)
ament_target_dependencies(${RECORDER_PROJNAME} rclcpp yaml-cpp geometry_msgs sensor_msgs std_msgs nav_msgs tf2_ros cv_bridge OpenCV)

target_link_libraries(${PROJECT_NAME}
  Qt5::Core
  Qt5::Gui
  Qt5::Widgets
  yaml-cpp
)
target_link_libraries(${RECORDER_PROJNAME} yaml-cpp)

install(TARGETS ${PROJECT_NAME} ${RECORDER_PROJNAME} DESTINATION lib/${PROJECT_NAME})

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
