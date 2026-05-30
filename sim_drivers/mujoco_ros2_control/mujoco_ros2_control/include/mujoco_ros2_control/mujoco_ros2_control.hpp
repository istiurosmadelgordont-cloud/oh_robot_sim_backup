#ifndef MUJOCO_ROS2_CONTROL__MUJOCO_ROS2_CONTROL_HPP_
#define MUJOCO_ROS2_CONTROL__MUJOCO_ROS2_CONTROL_HPP_

#include "rclcpp/rclcpp.hpp"
#include "pluginlib/class_loader.hpp"
#include "controller_manager/controller_manager.hpp"
#include "rosgraph_msgs/msg/clock.hpp"

#include "mujoco/mujoco.h"

#include "mujoco_ros2_control/mujoco_system.hpp"

namespace mujoco_ros2_control
{
class MujocoRos2Control
{
public:
  MujocoRos2Control(rclcpp::Node::SharedPtr & node, mjModel* mujoco_model, mjData* mujoco_data);
  ~MujocoRos2Control();
  void init();
  void update();
  /** @brief reset MuJoCo env to start state */
  void reset();

private:
  void publish_sim_time(rclcpp::Time sim_time);
  rclcpp::Node::SharedPtr node_;  // TODO: delete node
  mjModel* mj_model_;
  mjData* mj_data_;

  /* ------------ state vectors for state recover ------------ */
  // see: https://mujoco.readthedocs.io/en/stable/programming/simulation.html#state-and-control
  std::vector<mjtNum> initial_qpos_;
  std::vector<mjtNum> initial_qvel_;
  std::vector<mjtNum> initial_act_;
  // other states for user consideration
  std::vector<mjtNum> initial_mocap_pose_;
  std::vector<mjtNum> initial_mocap_quat_;
  std::vector<mjtNum> initial_userdata_;
  std::vector<mjtNum> initial_qacc_warmstart_;

  mjData *mj_data_bak_;

  rclcpp::Logger logger_;
  std::shared_ptr<pluginlib::ClassLoader<MujocoSystemInterface>> robot_hw_sim_loader_;

  std::shared_ptr<controller_manager::ControllerManager> controller_manager_;
  rclcpp::executors::MultiThreadedExecutor::SharedPtr cm_executor_;
  std::thread cm_thread_;
  bool stop_cm_thread_;
  rclcpp::Duration control_period_;

  rclcpp::Time last_update_sim_time_ros_;
  rclcpp::Publisher<rosgraph_msgs::msg::Clock>::SharedPtr clock_publisher_;
};
}  // namespace mujoco_ros2_control

#endif  // MUJOCO_ROS2_CONTROL__MUJOCO_ROS2_CONTROL_HPP_