#pragma once

#include <grpcpp/grpcpp.h>

#include <rclcpp/rclcpp.hpp>
#include <control_msgs/msg/joint_jog.hpp>
#include <geometry_msgs/msg/twist_stamped.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#if __has_include(<moveit/robot_state/robot_state.h>)
    #include <moveit/robot_state/robot_state.h>
    #include <moveit/robot_model_loader/robot_model_loader.h>
    #include <moveit/move_group_interface/move_group_interface.h>
#else
    #include <moveit/robot_state/robot_state.hpp>
    #include <moveit/robot_model_loader/robot_model_loader.hpp>
    #include <moveit/move_group_interface/move_group_interface.hpp>
#endif

#include <std_msgs/msg/bool.hpp>

#include "control_stubs/robot_core.grpc.pb.h"
#include "control_stubs/common.pb.h"

#include <memory>
#include <thread>
#include <mutex>
#include <shared_mutex>
#include <atomic>
#include <queue>


namespace robot_sim {


class CoreServiceRos2Impl final : public core::RobotCoreService::Service {
public:
    explicit CoreServiceRos2Impl(
        std::shared_ptr<rclcpp::Node> node,
        rclcpp::CallbackGroup::SharedPtr core_cb,
        rclcpp::CallbackGroup::SharedPtr emergency_cb);

    // Get robot description with joint limits
    grpc::Status GetRobotSpec(
        grpc::ServerContext* context,
        const common::Empty* request,
        core::RobotSpecification* response) override;

    // Get current robot state
    grpc::Status GetRobotState(
        grpc::ServerContext* context,
        const common::Empty* request,
        core::RobotState* response) override;

    // Set joint target (non-realtime planning)
    grpc::Status SetJointTarget(
        grpc::ServerContext* context,
        const core::JointCommand* request,
        common::Status* response) override;
    
    grpc::Status GetEndEffectorState(
        grpc::ServerContext* context,
        const core::MoveGroupRequest* request,
        core::EndEffectorState* response) override;

    // Bidirectional streaming for real-time servo control
    grpc::Status ServoControlStream(
        grpc::ServerContext* context,
        grpc::ServerReaderWriter<core::RobotState, core::ServoCommand>* stream) override;

    // Emergency stop
    grpc::Status EmergencyStop(
        grpc::ServerContext* context,
        const common::Empty* request,
        common::Status* response) override;

    
    const static std::string emergency_stop_topic_name_;

private:
    void jointStateCallback(const sensor_msgs::msg::JointState::SharedPtr msg);

    // process and publish to moveit2 servo node (moveit_servo:servo_node)
    void processServoCommand(const core::ServoCommand& command);

    bool switchMoveGroupInternal(const std::string& move_group);

    grpc::Status getRobotStateInternal(core::RobotState* response);

    std::shared_ptr<rclcpp::Node> node_;
    rclcpp::CallbackGroup::SharedPtr core_cb_group_;
    rclcpp::CallbackGroup::SharedPtr emergency_cb_group_;

    std::shared_ptr<robot_model_loader::RobotModelLoader> robot_model_loader_;
    std::shared_ptr<moveit::core::RobotModel> robot_model_;

    // cached for each moving group
    std::unordered_map<std::string, std::shared_ptr<moveit::planning_interface::MoveGroupInterface>> move_groups_;
    std::shared_ptr<moveit::planning_interface::MoveGroupInterface> move_group_;
    std::shared_mutex move_group_rwmutex_;    // protect move_group_
    
    rclcpp::Publisher<geometry_msgs::msg::TwistStamped>::SharedPtr twist_pub_;
    rclcpp::Publisher<control_msgs::msg::JointJog>::SharedPtr joint_jog_pub_;
    rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_state_sub_;
    
    sensor_msgs::msg::JointState::SharedPtr latest_joint_state_;
    std::mutex state_mutex_;    // protect latest_joint_state_
    
    rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr emergency_stop_pub_;
    std::atomic<bool> emergency_stop_;

    bool robot_can_servo;
};


}   // namespace robot_sim
