#pragma once

#include <geometry_msgs/msg/pose.hpp>

#include "control_stubs/common.pb.h"
#include "control_stubs/robot_core.pb.h"
#include "control_stubs/mobility_ai.pb.h"

namespace robot_sim {

bool is_valid_double(double x);
bool is_valid_pose(const geometry_msgs::msg::Pose &pose);
bool is_valid_position(double x, double y, double z);
bool is_valid_position2d(double x, double y, double z);
bool is_valid_quaternion(double x, double y, double z, double w);
// NOTE: throws if invalid so you should check `is_valid_quaternion`
void normalize_quaternion(double &x, double &y, double &z, double &w);

/* ----------------- control_stubs validation helpers ----------------- */

bool is_valid_pose(const common::Pose &pose);
bool is_valid_quaternion(const common::Quaternion &quat);
bool is_valid_joint_cmd(const core::JointCommand &joint_cmd);
bool is_valid_nav_goal(const ai::NavGoal &goal);

}   // namespace robot_sim
