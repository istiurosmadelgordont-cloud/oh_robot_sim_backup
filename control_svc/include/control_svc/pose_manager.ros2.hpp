#pragma once

#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <geometry_msgs/msg/pose_with_covariance_stamped.hpp>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>

#include "robot_sim_dto/srv/get_pose2_d_cov.hpp"

#include <fstream>
#include <sstream>
#include <optional>


class PoseManager : public rclcpp::Node {
public:
    using GetPose2DCov = robot_sim_dto::srv::GetPose2DCov;

    PoseManager(const rclcpp::NodeOptions & options, std::optional<std::string> pose_file);
    ~PoseManager() override;

    static const std::string init_pose_svc_name_;

private:

    bool load_pose_from_file(const std::string & file);
    void save_pose_to_file(const std::string & file);

    void amcl_callback(const geometry_msgs::msg::PoseWithCovarianceStamped::SharedPtr msg);

    void timer_update();

    void get_pose(const std::shared_ptr<GetPose2DCov::Request> req,
                std::shared_ptr<GetPose2DCov::Response> res);

    std::optional<std::string> pose_file_;

    geometry_msgs::msg::PoseWithCovarianceStamped init_pose_;
    geometry_msgs::msg::PoseWithCovarianceStamped current_pose_;

    std::optional<geometry_msgs::msg::PoseWithCovarianceStamped> last_amcl_pose_;

    rclcpp::Subscription<geometry_msgs::msg::PoseWithCovarianceStamped>::SharedPtr amcl_sub_;
    rclcpp::TimerBase::SharedPtr timer_;
    rclcpp::Service<GetPose2DCov>::SharedPtr get_pose_srv_;
};