#ifndef MUJOCO_ROS2_CONTROL__MUJOCO_RENDERING_HPP_
#define MUJOCO_ROS2_CONTROL__MUJOCO_RENDERING_HPP_

#include "rclcpp/rclcpp.hpp"
#include "mujoco/mujoco.h"
#include "GLFW/glfw3.h"

namespace mujoco_ros2_control
{
class MujocoRendering
{
public:
  MujocoRendering(const MujocoRendering& obj) = delete;
  void operator=(const MujocoRendering &) = delete;

  static MujocoRendering* get_instance();
  void init(rclcpp::Node::SharedPtr & node, mjModel* mujoco_model, mjData* mujoco_data);
  bool is_close_flag_raised();
  void update();
  void close();

  /**
   * @brief Register offscreen camera (mjCAMERA_FIXED) defined in mujoco_model.
   * @param[in] cam_name the name of the camera in mujoco model
   * @param[in] width, height the size of the camera viewport
   * @param[in] maxgeom max geometry in camera
   * @return fixed camera description id. -1 indicates cannot find the specific camera in model.
   *  -2 indicates repeated registration.
   */
  int register_offscreen_camera(const std::string cam_name, int width, int height, int maxgeom = 1000);

  /**
   * @brief Render viewport of the specific camera to buffer.
   * @param[in] fixed_cam_id the description id of the fixed offscreen camera defined in model
   * @param[out] buf the rendered rgb buffer
   * @param[out] depth (optional) the depth channel. Pass NULL if you don't need.
   * @note If the `cam_id` is invalid, then this method will do nothing to `buf`.
   */
  void render_offscreen_camera(int fixed_cam_id, unsigned char *buf, float *depth);

private:
  MujocoRendering();
  ~MujocoRendering();
  static void keyboard_callback(GLFWwindow* window, int key, int scancode, int act, int mods);
  static void mouse_button_callback(GLFWwindow* window, int button, int act, int mods);
  static void mouse_move_callback(GLFWwindow* window, double xpos, double ypos);
  static void scroll_callback(GLFWwindow* window, double xoffset, double yoffset);
  void keyboard_callback_impl(GLFWwindow* window, int key, int scancode, int act, int mods);
  void mouse_button_callback_impl(GLFWwindow* window, int button, int act, int mods);
  void mouse_move_callback_impl(GLFWwindow* window, double xpos, double ypos);
  void scroll_callback_impl(GLFWwindow* window, double xoffset, double yoffset);

  static MujocoRendering* instance_;
  rclcpp::Node::SharedPtr node_;  // TODO: delete node and add logger
  mjModel* mj_model_;
  mjData* mj_data_;
  mjvCamera mjv_cam_;
  mjvOption mjv_opt_;
  mjvScene mjv_scn_;
  mjrContext mjr_con_;

  /* --- offscreen cameras --- */
  struct OffscreenCamera_t {
    mjrContext con_;
    mjvScene   scn_;
    mjvOption  opt_;
    mjvCamera  cam_;
    mjrRect    viewport_;
  };
  std::unordered_map<int, OffscreenCamera_t*> off_cams;

  GLFWwindow* window_;

  bool button_left_;
  bool button_middle_;
  bool button_right_;
  double lastx_;
  double lasty_;
};
}  // namespace mujoco_ros2_control

#endif  // MUJOCO_ROS2_CONTROL__MUJOCO_RENDERING_HPP_