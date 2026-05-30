
#include "control_svc/core_service.ros2.hpp"
#include "control_svc/mobility_ai_service.ros2.hpp"
#include "robot_sim_common/config.h"
#include "robot_sim_common/helpers.hpp"

#include <chrono>
#include <random>

namespace robot_sim {

MobilityServiceRos2Impl::MobilityServiceRos2Impl(
    rclcpp::Node::SharedPtr node,
    rclcpp::CallbackGroup::SharedPtr agent_cb,
    rclcpp::CallbackGroup::SharedPtr dedicated_nav2client_cb,
    rclcpp::CallbackGroup::SharedPtr emergency_cb)
    : node_(node),
        agent_cb_group_(std::move(agent_cb)),
        dedicated_nav2client_cb_group_(std::move(dedicated_nav2client_cb)),
        emergency_cb_group_(std::move(emergency_cb)) {
    
    // setup client for pose manager
    this->pose_manager_client_ = node_->create_client<robot_sim_dto::srv::GetPose2DCov>(
        POSE_MGR_SVC, rmw_qos_profile_services_default, agent_cb_group_);

    // Create publisher for initial pose
    this->initial_pose_pub_ = node_->create_publisher<geometry_msgs::msg::PoseWithCovarianceStamped>(
        "/initialpose", 10);

    this->setInitialPose();
    
    // NOTE: we will not use agent_cb_group_ (MutualExclusive) for nav2 client
    // because the spin waiting in gRPC handler will block the callbacks of the action client.
    // this->nav_client_ = rclcpp_action::create_client<NavigateToPose>(
    //     node_, "navigate_to_pose", agent_cb_group_);
    this->nav_client_ = rclcpp_action::create_client<NavigateToPose>(
        node_, "navigate_to_pose", dedicated_nav2client_cb_group_);
    
    rclcpp::SubscriptionOptions es_options;
    es_options.callback_group = emergency_cb_group_;
    this->emergency_stop_sub_ = node_->create_subscription<std_msgs::msg::Bool>(
        CoreServiceRos2Impl::emergency_stop_topic_name_, 10,
        std::bind(&MobilityServiceRos2Impl::emergencyStopCallback, this, std::placeholders::_1),
        es_options);
    
    RCLCPP_INFO(node_->get_logger(), "MobilityService initialized");
}

std::string MobilityServiceRos2Impl::generate_task_id() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(100000, 999999);
    return "task_" + std::to_string(dis(gen));
}

grpc::Status MobilityServiceRos2Impl::GetRobotPoseInMap(
    grpc::ServerContext *context,
    const common::Empty* request,
    common::PoseStamped* response) {
    
    (void)context;
    (void)request;

    auto req = std::make_shared<robot_sim_dto::srv::GetPose2DCov::Request>();
    auto fut = this->pose_manager_client_->async_send_request(req);

    auto spin_status = rclcpp::spin_until_future_complete(node_, fut, std::chrono::seconds(5));
    if (spin_status != rclcpp::FutureReturnCode::SUCCESS) {
        return grpc::Status(grpc::StatusCode::UNAVAILABLE, "pose manager service call failed/timeout");
    }
    auto resp = fut.get();
    if (!resp->success) {
        return grpc::Status(grpc::StatusCode::INTERNAL, "pose manager reported failure");
    }

    const auto &map_pose = resp->pose;
    // TODO: increment seq
    response->mutable_header()->set_seq(0);
    rclcpp::Time stamp(map_pose.header.stamp);
    response->mutable_header()->set_timestamp(stamp.seconds());
    response->mutable_header()->set_frame_id(map_pose.header.frame_id);

    auto *msg_pose = response->mutable_pose();
    msg_pose->mutable_position()->set_x(map_pose.pose.pose.position.x);
    msg_pose->mutable_position()->set_y(map_pose.pose.pose.position.y);
    msg_pose->mutable_position()->set_z(map_pose.pose.pose.position.z);
    msg_pose->mutable_orientation()->set_x(map_pose.pose.pose.orientation.x);
    msg_pose->mutable_orientation()->set_y(map_pose.pose.pose.orientation.y);
    msg_pose->mutable_orientation()->set_z(map_pose.pose.pose.orientation.z);
    msg_pose->mutable_orientation()->set_w(map_pose.pose.pose.orientation.w);

    return grpc::Status::OK;
}

grpc::Status MobilityServiceRos2Impl::NavigateTo(
    grpc::ServerContext* context,
    const ai::NavGoal* request,
    grpc::ServerWriter<ai::TaskFeedback>* writer) {
    
    // validate parameters
    if (!is_valid_nav_goal(*request)) {
        return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, "invalid nav_goal parameter");
    }
    
    std::string task_id = generate_task_id();
    
    // Wait for action server
    if (!nav_client_->wait_for_action_server(std::chrono::seconds(5))) {
        ai::TaskFeedback feedback;
        feedback.set_task_id(task_id);
        feedback.mutable_status()->set_code(common::STATUS_FAILURE);
        feedback.mutable_status()->set_message("Navigation action server not available");
        writer->Write(feedback);
        return grpc::Status::OK;
    }
    
    // Build Nav2 goal
    NavigateToPose::Goal nav_goal;
    nav_goal.pose.header.frame_id = request->target_frame().empty() ? "map" : request->target_frame();
    nav_goal.pose.header.stamp = node_->now();
    nav_goal.pose.pose.position.x = request->target_pose().position().x();
    nav_goal.pose.pose.position.y = request->target_pose().position().y();
    nav_goal.pose.pose.position.z = request->target_pose().position().z();
    nav_goal.pose.pose.orientation.x = request->target_pose().orientation().x();
    nav_goal.pose.pose.orientation.y = request->target_pose().orientation().y();
    nav_goal.pose.pose.orientation.z = request->target_pose().orientation().z();
    nav_goal.pose.pose.orientation.w = request->target_pose().orientation().w();

    // request->max_velocity();
    
    // Send goal
    auto send_goal_options = rclcpp_action::Client<NavigateToPose>::SendGoalOptions();
    
    std::atomic<bool> goal_done{false};
    std::atomic<bool> goal_accepted{false};
    common::StatusCode final_status = common::STATUS_UNKNOWN;
    std::string final_message;
    
    send_goal_options.goal_response_callback = 
        [this, &goal_accepted](GoalHandle::SharedPtr goal_handle) {
            RCLCPP_INFO(this->node_->get_logger(), "action server ACKed after receiving goal");
            if (goal_handle) {
                goal_accepted = true;
                std::lock_guard<std::mutex> guard(this->current_nav_goal_mutex_);
                if (this->current_nav_goal_handle_) {
                    RCLCPP_WARN(this->node_->get_logger(), "data corruption: previous goal handle not reset");
                }
                this->current_nav_goal_handle_ = goal_handle;
                RCLCPP_INFO(this->node_->get_logger(), "goal received by action server");
            } else {
                RCLCPP_ERROR(this->node_->get_logger(), "goal rejected by action server");
            }
        };
    
    send_goal_options.feedback_callback =
        [writer, task_id](GoalHandle::SharedPtr, const std::shared_ptr<const NavigateToPose::Feedback> feedback) {
            ai::TaskFeedback fb;
            fb.set_task_id(task_id);
            fb.mutable_status()->set_code(common::STATUS_RUNNING);
            
            auto remaining = feedback->distance_remaining;
            // RCLCPP_INFO(rclcpp::get_logger("svc_mgr_nav2goal_fb"), "Distance to goal: %.3f m", remaining);
            auto eta = static_cast<uint32_t>(feedback->estimated_time_remaining.sec);
            fb.set_eta(eta);
            fb.set_feedback_text("Distance remaining: " + std::to_string(remaining) + "m");
            
            writer->Write(fb);
        };
    
    send_goal_options.result_callback =
        [this, &goal_done, &final_status, &final_message](const GoalHandle::WrappedResult& result) {
            switch (result.code) {
                case rclcpp_action::ResultCode::SUCCEEDED:
                    final_status = common::STATUS_SUCCESS;
                    final_message = "Navigation succeeded";
                    break;
                case rclcpp_action::ResultCode::ABORTED:
                    final_status = common::STATUS_FAILURE;
                    final_message = "Navigation aborted";
                    break;
                case rclcpp_action::ResultCode::CANCELED:
                    final_status = common::STATUS_PREEMPTED;
                    final_message = "Navigation canceled";
                    break;
                default:
                    final_status = common::STATUS_FAILURE;
                    final_message = "Navigation failed with unknown error";
                    break;
            }
            goal_done = true;
            // clear the goal handle
            std::lock_guard<std::mutex> guard(this->current_nav_goal_mutex_);
            this->current_nav_goal_handle_ = nullptr;
        };
    
    auto goal_handle_future = nav_client_->async_send_goal(nav_goal, send_goal_options);
    
    // FIXME: make the gRPC handler fully async
    // Wait for goal acceptance (spin wait)
    auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
    while (!goal_accepted && std::chrono::steady_clock::now() < deadline) {
        // !!! IMPORTANT !!! DO NOT use rclcpp::spin_some in MultiThreadExecutor with Reentrant callback group
        // It can cause recursive spinning / deadlock or corrupt scheduling.
        // rclcpp::spin_some(node_);
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    
    if (!goal_accepted) {
        ai::TaskFeedback feedback;
        feedback.set_task_id(task_id);
        feedback.mutable_status()->set_code(common::STATUS_FAILURE);
        feedback.mutable_status()->set_message("Goal was rejected by navigation server");
        writer->Write(feedback);
        return grpc::Status::OK;
    }
    
    // Initial feedback
    ai::TaskFeedback initial_fb;
    initial_fb.set_task_id(task_id);
    initial_fb.mutable_status()->set_code(common::STATUS_RUNNING);
    initial_fb.set_feedback_text("Navigation started");
    writer->Write(initial_fb);
    
    // Wait for completion
    while (!goal_done && !context->IsCancelled()) {
        // rclcpp::spin_some(node_);
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    
    // Final feedback
    ai::TaskFeedback final_fb;
    final_fb.set_task_id(task_id);
    final_fb.mutable_status()->set_code(final_status);
    final_fb.mutable_status()->set_message(final_message);
    writer->Write(final_fb);
    
    return grpc::Status::OK;
}

grpc::Status MobilityServiceRos2Impl::ExecuteNaturalCommand(
    grpc::ServerContext* context,
    const ai::NaturalLanguageRequest* request,
    grpc::ServerWriter<ai::TaskFeedback>* writer) {
    
    (void)context;
    
    std::string task_id = generate_task_id();

    std::string prompt = request->prompt();
    // std::map<std::string, std::string> n_context = request->context();
    // ai::NaturalLanguageRequest::ModelType model_selector = request->model_selector();
    if (prompt.empty()) {
        RCLCPP_WARN(node_->get_logger(), "ExecuteNaturalCommand: empty prompt");
    }

    // TODO: Implement VLA/VLN execution logic here
    // 1. Parse the natural language command
    // 2. Select appropriate model based on model_selector
    // 3. Execute actions and stream feedback
    
    ai::TaskFeedback feedback;
    feedback.set_task_id(task_id);
    feedback.mutable_status()->set_code(common::STATUS_FAILURE);
    feedback.mutable_status()->set_message("sorry, VLA/VLN command is not available for now :(");
    writer->Write(feedback);
    
    return grpc::Status::OK;
}

void MobilityServiceRos2Impl::setInitialPose() {
    
    // Wait for service to become available
    RCLCPP_INFO(node_->get_logger(), "Waiting for pose_manager service...");
    if (!pose_manager_client_->wait_for_service(std::chrono::seconds(30))) {
        throw std::runtime_error("service pose_manager not available after 30 seconds");
    }
    
    // Call service
    auto request = std::make_shared<robot_sim_dto::srv::GetPose2DCov::Request>();
    auto future = pose_manager_client_->async_send_request(request);
    
    // Wait for response
    auto spin_status = rclcpp::spin_until_future_complete(
        node_, future, std::chrono::seconds(10));
    
    if (spin_status != rclcpp::FutureReturnCode::SUCCESS) {
        throw std::runtime_error("failed to call pose_manager service");
    }
    
    auto response = future.get();
    if (!response->success) {
        throw std::runtime_error("failed to get initial pose from pose_manager");
    }
    
    // Publish initial pose to AMCL
    geometry_msgs::msg::PoseWithCovarianceStamped initial_pose = response->pose;
    initial_pose_pub_->publish(initial_pose);
    
    // Wait a bit for AMCL to process
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    
    RCLCPP_INFO(node_->get_logger(), "initial pose set successfully at (%.2f, %.2f)",
                initial_pose.pose.pose.position.x,
                initial_pose.pose.pose.position.y);
}

void MobilityServiceRos2Impl::emergencyStopCallback(const std_msgs::msg::Bool::SharedPtr is_emergency_stop) {
    if (!is_emergency_stop->data) return;

    std::lock_guard<std::mutex> guard(this->current_nav_goal_mutex_);
    if (this->current_nav_goal_handle_) {
        RCLCPP_INFO(this->node_->get_logger(), "MobilityServiceRos2Impl: emergency stop signal received. Try to cancel the current navigation");
        this->nav_client_->async_cancel_goal(this->current_nav_goal_handle_,
            [this](auto resp){
                (void)resp;
                std::lock_guard<std::mutex> guard(this->current_nav_goal_mutex_);
                this->current_nav_goal_handle_ = nullptr;
            });
    }
}

}   // namespace robot_sim
