#pragma once

#include <grpcpp/grpcpp.h>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <geometry_msgs/msg/pose_with_covariance_stamped.hpp>
#include <nav2_msgs/action/navigate_to_pose.hpp>
#include <std_msgs/msg/bool.hpp>

#include "robot_sim_dto/srv/get_pose2_d_cov.hpp"

#include "control_stubs/common.pb.h"
#include "control_stubs/mobility_ai.grpc.pb.h"

#include <memory>
#include <string>

namespace robot_sim {

class MobilityServiceRos2Impl final : public ai::MobilityService::Service {
public:
    explicit MobilityServiceRos2Impl(
        rclcpp::Node::SharedPtr node,
        rclcpp::CallbackGroup::SharedPtr agent_cb,
        rclcpp::CallbackGroup::SharedPtr dedicated_nav2client_cb,
        rclcpp::CallbackGroup::SharedPtr emergency_cb);
    
    grpc::Status GetRobotPoseInMap(
        grpc::ServerContext *context,
        const common::Empty* request,
        common::PoseStamped* response) override;

    grpc::Status NavigateTo(
        grpc::ServerContext* context,
        const ai::NavGoal* request,
        grpc::ServerWriter<ai::TaskFeedback>* writer) override;
    
    grpc::Status ExecuteNaturalCommand(
        grpc::ServerContext* context,
        const ai::NaturalLanguageRequest* request,
        grpc::ServerWriter<ai::TaskFeedback>* writer) override;

private:

    // --------------- SLAM 2D related ---------------
    // set for SLAM 2D navigation (AMCL)
    void setInitialPose();

    rclcpp::Client<robot_sim_dto::srv::GetPose2DCov>::SharedPtr pose_manager_client_;
    rclcpp::Publisher<geometry_msgs::msg::PoseWithCovarianceStamped>::SharedPtr initial_pose_pub_;

    // -----------------------------------------------

    void emergencyStopCallback(const std_msgs::msg::Bool::SharedPtr is_emergency_stop);
    rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr emergency_stop_sub_;

    using NavigateToPose = nav2_msgs::action::NavigateToPose;
    using GoalHandle = rclcpp_action::ClientGoalHandle<NavigateToPose>;
    
    rclcpp::Node::SharedPtr node_;
    rclcpp::CallbackGroup::SharedPtr agent_cb_group_;
    rclcpp::CallbackGroup::SharedPtr dedicated_nav2client_cb_group_;
    rclcpp::CallbackGroup::SharedPtr emergency_cb_group_;

    rclcpp_action::Client<NavigateToPose>::SharedPtr nav_client_;
    GoalHandle::SharedPtr current_nav_goal_handle_;
    std::mutex current_nav_goal_mutex_; // protect current_nav_goal at cancellation time
    
    
    std::string generate_task_id();
};

}   // namespace robot_sim