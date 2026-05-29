cmake_minimum_required(VERSION 3.8)
project(control_stubs)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(Protobuf REQUIRED)
find_package(gRPC REQUIRED)

# Find host grpc_cpp_plugin for cross-compilation
# We need the host's plugin to generate code, not the target's
find_program(GRPC_CPP_PLUGIN grpc_cpp_plugin)
if(NOT GRPC_CPP_PLUGIN)
  message(FATAL_ERROR "grpc_cpp_plugin not found in PATH")
endif()

message(STATUS "Using grpc_cpp_plugin: ${GRPC_CPP_PLUGIN}")

# Find all .proto files
file(GLOB PROTO_FILES "${CMAKE_CURRENT_SOURCE_DIR}/${PROJECT_NAME}/*.proto")

# Generate C++ code from .proto files
set(PROTO_SRCS)
set(PROTO_HDRS)
set(GRPC_SRCS)
set(GRPC_HDRS)

foreach(PROTO_FILE ${PROTO_FILES})
  get_filename_component(PROTO_NAME ${PROTO_FILE} NAME_WE)
  get_filename_component(PROTO_PATH ${PROTO_FILE} DIRECTORY)
  
  # C++ protobuf outputs
  list(APPEND PROTO_SRCS "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}/${PROTO_NAME}.pb.cc")
  list(APPEND PROTO_HDRS "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}/${PROTO_NAME}.pb.h")
  
  # C++ gRPC outputs
  list(APPEND GRPC_SRCS "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}/${PROTO_NAME}.grpc.pb.cc")
  list(APPEND GRPC_HDRS "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}/${PROTO_NAME}.grpc.pb.h")
  
  # Custom command to generate C++ code
  add_custom_command(
    OUTPUT 
      "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}/${PROTO_NAME}.pb.cc"
      "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}/${PROTO_NAME}.pb.h"
      "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}/${PROTO_NAME}.grpc.pb.cc"
      "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}/${PROTO_NAME}.grpc.pb.h"
    COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}"
    COMMAND ${Protobuf_PROTOC_EXECUTABLE}
      --proto_path=${CMAKE_CURRENT_SOURCE_DIR}
      --cpp_out=${CMAKE_CURRENT_BINARY_DIR}
      --grpc_out=${CMAKE_CURRENT_BINARY_DIR}
      --plugin=protoc-gen-grpc=${GRPC_CPP_PLUGIN}
      ${PROTO_FILE}
    DEPENDS ${PROTO_FILE}
    COMMENT "Generating C++ code from ${PROTO_NAME}.proto"
  )
endforeach()

# Create C++ library
add_library(${PROJECT_NAME} SHARED
  ${PROTO_SRCS}
  ${GRPC_SRCS}
)

target_include_directories(${PROJECT_NAME} PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}>
  $<INSTALL_INTERFACE:include>
)

target_link_libraries(${PROJECT_NAME}
  protobuf::libprotobuf
  gRPC::grpc++
)

# Install C++ library and headers
install(TARGETS ${PROJECT_NAME}
  EXPORT export_${PROJECT_NAME}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(FILES ${PROTO_HDRS} ${GRPC_HDRS}
  DESTINATION include/${PROJECT_NAME}
)

# Install proto files for potential downstream use
install(FILES ${PROTO_FILES}
  DESTINATION share/${PROJECT_NAME}/proto
)

# Export C++ targets
ament_export_targets(export_${PROJECT_NAME} HAS_LIBRARY_TARGET)
ament_export_dependencies(Protobuf gRPC)

# Python setup
ament_python_install_package(${PROJECT_NAME})

# Custom command to generate Python code at build time
add_custom_target(generate_python_stubs ALL
  DEPENDS ${PROTO_FILES}
)

foreach(PROTO_FILE ${PROTO_FILES})
  get_filename_component(PROTO_NAME ${PROTO_FILE} NAME_WE)
  
  add_custom_command(
    TARGET generate_python_stubs
    COMMAND ${Python3_EXECUTABLE} -m grpc_tools.protoc
      -I${CMAKE_CURRENT_SOURCE_DIR}
      --python_out=${CMAKE_CURRENT_SOURCE_DIR}
      --grpc_python_out=${CMAKE_CURRENT_SOURCE_DIR}
      --pyi_out=${CMAKE_CURRENT_SOURCE_DIR}
      ${PROTO_FILE}
    COMMENT "Generating Python code from ${PROTO_NAME}.proto"
  )
endforeach()


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
