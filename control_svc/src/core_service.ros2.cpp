
#include "control_svc/core_service.ros2.hpp"
#include "robot_sim_common/helpers.hpp"

namespace robot_sim {

const std::string CoreServiceRos2Impl::emergency_stop_topic_name_ = "/emergency_stop";

CoreServiceRos2Impl::CoreServiceRos2Impl(
    std::shared_ptr<rclcpp::Node> node,
    rclcpp::CallbackGroup::SharedPtr core_cb,
    rclcpp::CallbackGroup::SharedPtr emergency_cb)
    : node_(node),
        core_cb_group_(std::move(core_cb)),
        emergency_cb_group_(std::move(emergency_cb)),
        emergency_stop_(false),
        robot_can_servo(true) {
    
    // emergency stop: only cache the last one signal
    rclcpp::QoS emergency_stop_qos_profile = rclcpp::QoS(rclcpp::KeepLast(1))
            .reliable()
            .durability_volatile();
    emergency_stop_pub_ = node_->create_publisher<std_msgs::msg::Bool>(
        CoreServiceRos2Impl::emergency_stop_topic_name_, emergency_stop_qos_profile);
    
    // Subscribe to joint states
    rclcpp::SubscriptionOptions js_options;
    js_options.callback_group = core_cb_group_;
    joint_state_sub_ = node_->create_subscription<sensor_msgs::msg::JointState>(
        "/joint_states", 10,
        std::bind(&CoreServiceRos2Impl::jointStateCallback, this, std::placeholders::_1),
        js_options);
    
    try {
        // Load robot model (semantic representation topic)
        robot_model_loader_ = std::make_shared<robot_model_loader::RobotModelLoader>(
            node_, "robot_description");
        robot_model_ = robot_model_loader_->getModel();
        if (!robot_model_) {
            throw std::runtime_error("semantic robot model load failed");
        }
    } catch (const std::exception &ex) {
        RCLCPP_WARN(node_->get_logger(), "current robot doesn't have semantic representation and is not servo-capable: %s", ex.what());
        robot_can_servo = false;
        return;
    }
    
    // Initialize publishers for MoveIt Servo
    twist_pub_ = node_->create_publisher<geometry_msgs::msg::TwistStamped>(
        "/servo_node/delta_twist_cmds", 10);
    
    joint_jog_pub_ = node_->create_publisher<control_msgs::msg::JointJog>(
        "/servo_node/delta_joint_cmds", 10);
    
    // Initialize MoveGroup for FK/IK at use time (use move_group from user)
    move_group_ = nullptr;
    
    RCLCPP_INFO(node_->get_logger(), "RobotCoreService initialized");
}


grpc::Status CoreServiceRos2Impl::GetRobotState(
    grpc::ServerContext* context,
    const common::Empty* request,
    core::RobotState* response) {

    (void)context;
    (void)request;
    
    std::lock_guard<std::mutex> lock(state_mutex_);

    RCLCPP_DEBUG(node_->get_logger(), "GetRobotState called");
    
    if (!latest_joint_state_) {
        return grpc::Status(grpc::StatusCode::UNAVAILABLE, "No joint state available");
    }
    
    // Fill header
    auto* header = response->mutable_header();
    // TODO: add seq
    header->set_seq(0);
    // TODO: merge all the timestamp use in this framework
    header->set_timestamp(node_->now().seconds());
    // not applicable for JointState of the robot
    header->set_frame_id("N/A");
    
    // Fill joint data
    for (size_t i = 0; i < latest_joint_state_->name.size(); ++i) {
        response->add_name(latest_joint_state_->name[i]);
        response->add_position(latest_joint_state_->position[i]);
        
        if (i < latest_joint_state_->velocity.size()) {
            response->add_velocity(latest_joint_state_->velocity[i]);
        } else {
            response->add_velocity(0.0);
        }
        
        if (i < latest_joint_state_->effort.size()) {
            response->add_effort(latest_joint_state_->effort[i]);
        } else {
            response->add_effort(0.0);
        }
    }
    
    return grpc::Status::OK;
}

grpc::Status CoreServiceRos2Impl::GetRobotSpec(
    grpc::ServerContext* context,
    const common::Empty* request,
    core::RobotSpecification* response) {
    // unused parameters
    (void)context;
    (void)request;
    
    if (!robot_model_) {
        return grpc::Status(grpc::StatusCode::INTERNAL, "Robot model (semantic representation) not loaded");
    }
    
    response->set_robot_name(robot_model_->getName());
    
    // fill all JMGs
    auto *jmg_specs = response->mutable_joint_model_groups();

    // Build JMG lookup map for O(1) joint->group lookup (see "fill all joints" part)
    std::unordered_map<std::string, std::string> joint_to_jmg;
    
    const std::vector<std::string>& jmg_names = robot_model_->getJointModelGroupNames();
    jmg_specs->Reserve(jmg_names.size());
    
    for (const auto& group : jmg_names) {
        core::JointModelGroupSpec *jmg_spec = jmg_specs->Add();
        // fill JMG name
        jmg_spec->set_name(group);
        // fill named states
        const moveit::core::JointModelGroup *jmg = robot_model_->getJointModelGroup(group);
        const std::vector<std::string> &state_names = jmg->getDefaultStateNames();
        jmg_spec->mutable_named_states()->Reserve(state_names.size());
        
        moveit::core::RobotState _tmp_state(robot_model_);
        std::vector<double> values;
        
        for (const auto& state_name: state_names) {
            core::JointModelGroupNamedState *named_state = jmg_spec->add_named_states();
            named_state->set_name(state_name);
            if (_tmp_state.setToDefaultValues(jmg, state_name)) {
                _tmp_state.copyJointGroupPositions(jmg, values);
                named_state->mutable_joint_values()->Reserve(values.size());
                for (const auto& jv: values) {
                    named_state->add_joint_values(jv);
                }
            }
        }
        // fill attached end effectors
        const std::vector<std::string>& attached_ee_names = jmg->getAttachedEndEffectorNames();
        jmg_spec->mutable_end_effectors()->Reserve(attached_ee_names.size());
        for (const auto& ee_name: attached_ee_names) {
            core::EESpec *ee_spec = jmg_spec->add_end_effectors();
            ee_spec->set_name(ee_name);
            ee_spec->set_jmg_name(group);
        }

        // build JMG lookup map for "fill all joints" part
        const std::vector<const moveit::core::JointModel*>& joints = jmg->getJointModels();
        for (const auto* joint : joints) {
            joint_to_jmg[joint->getName()] = group;
        }
    }
    
    auto *joint_specs = response->mutable_joints();
    // fill all joints (include non-active) with their specs
    for (const auto& joint_model : robot_model_->getJointModels()) {
        // A joint may have multiple variables (e.g., a floating joint has 6),
        // but revolute/prismatic joints typically have only 1.
        const std::vector<std::string>& var_names = joint_model->getVariableNames();
        const std::vector<moveit::core::VariableBounds>& bounds = joint_model->getVariableBounds();
        
        // O(1) lookup to find out which JMG does this joint belongs to
        auto it = joint_to_jmg.find(joint_model->getName());
        const std::string& jmg_name_of_joint = (it != joint_to_jmg.end()) ? it->second : "N/A";
        
        for (size_t i = 0; i < var_names.size(); ++i) {
            core::JointLimit* limit = joint_specs->Add();
            limit->set_name(var_names[i]);
            limit->set_type(joint_model->getTypeName());
            limit->set_jmg_name(jmg_name_of_joint);
            const auto& bound = bounds[i];
            limit->set_lower_limit(bound.min_position_);
            limit->set_upper_limit(bound.max_position_);
            limit->set_velocity_limit(bound.max_velocity_);
            if (bound.acceleration_bounded_)
                limit->set_acceleration_limit(bound.max_acceleration_);
            // TODO: add effort limit
        }
    }
    
    return grpc::Status::OK;
}

grpc::Status CoreServiceRos2Impl::SetJointTarget(
    grpc::ServerContext* context,
    const core::JointCommand* request,
    common::Status* response) {
    
    (void)context;

    if (!robot_can_servo) {
        return grpc::Status(grpc::StatusCode::UNAVAILABLE, "Current robot is not servo-capable");
    }
    
    if (emergency_stop_.load()) {
        response->set_code(common::STATUS_FAILURE);
        response->set_message("Emergency stop active");
        return grpc::Status::OK;
    }

    // validate parameters
    if (!is_valid_joint_cmd(*request)) {
        response->set_code(common::STATUS_FAILURE);
        response->set_message("invalid joint command");
        return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, "invalid joint command");
    }

    if (!this->switchMoveGroupInternal(request->group().jmg_name())) {
        response->set_code(common::STATUS_FAILURE);
        response->set_message(
            "failed to switch to move_group '" + request->group().jmg_name() +
            "': check you parameter and make sure your robot is conrrectly configured");
        return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT,
            "cannot switch move_group to '" + request->group().jmg_name() + "'");
    }
    
    try {
        std::map<std::string, double> target_map;
        for (int i = 0; i < request->name_size(); ++i) {
            target_map[request->name(i)] = request->data(i);
        }
        moveit::core::MoveItErrorCode result;

        {
            std::shared_lock<std::shared_mutex> rlock(this->move_group_rwmutex_);
            move_group_->setJointValueTarget(target_map);
            result = move_group_->move();
        }

        if (result == moveit::core::MoveItErrorCode::SUCCESS) {
            response->set_code(common::STATUS_SUCCESS);
            response->set_message("Joint target reached");
        } else {
            response->set_code(common::STATUS_FAILURE);
            response->set_message("Failed to reach joint target");
        }
    } catch (const std::exception& e) {
        response->set_code(common::STATUS_FAILURE);
        response->set_message(e.what());
    }
    
    return grpc::Status::OK;
}

grpc::Status CoreServiceRos2Impl::GetEndEffectorState(
    grpc::ServerContext* context,
    const core::MoveGroupRequest* request,
    core::EndEffectorState* response) {
    
    (void)context;

    if (!robot_can_servo) {
        return grpc::Status(grpc::StatusCode::UNAVAILABLE, "Current robot is not servo-capable");
    }

    RCLCPP_DEBUG(node_->get_logger(), "GetEndEffectorState called with move_group '%s'", request->jmg_name().c_str());

    if (!this->switchMoveGroupInternal(request->jmg_name())) {
        return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT,
            "cannot switch move_group to '" + request->jmg_name() + "'");
    }

    std::shared_lock<std::shared_mutex> rlock(this->move_group_rwmutex_);
    
    // Compute FK for TCP pose
    moveit::core::RobotStatePtr current_state = move_group_->getCurrentState(1.0);
    if (current_state) {
        const std::string &eelink = move_group_->getEndEffectorLink();
        if (eelink.empty()) {
            std::string errmsg = "there is no end effector link defined for move group '" + move_group_->getName() + "'";
            RCLCPP_WARN(node_->get_logger(), errmsg.c_str());
            
            return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, errmsg);
        } else try {
            const Eigen::Isometry3d& end_effector_state = 
                current_state->getGlobalLinkTransform(eelink);
        
            auto* pose_stamped = response->mutable_pose_stamped();
            auto* header = pose_stamped->mutable_header();
            header->set_frame_id(move_group_->getPlanningFrame());
            // TODO: merge all the timestamp use in this framework
            header->set_timestamp(node_->now().seconds());
            auto* tcp_pose = pose_stamped->mutable_pose();
            auto* position = tcp_pose->mutable_position();
            position->set_x(end_effector_state.translation().x());
            position->set_y(end_effector_state.translation().y());
            position->set_z(end_effector_state.translation().z());
            
            Eigen::Quaterniond quat(end_effector_state.rotation());
            auto* orientation = tcp_pose->mutable_orientation();
            orientation->set_x(quat.x());
            orientation->set_y(quat.y());
            orientation->set_z(quat.z());
            orientation->set_w(quat.w());
        } catch (const std::exception &ex) {
            std::string err = std::string("failed to get end effector state: ") + ex.what();
            RCLCPP_ERROR(node_->get_logger(), err.c_str());
            return grpc::Status(grpc::StatusCode::INTERNAL, err);
        }
    } else {
        std::string err = "failed to current robot state for move group '" + move_group_->getName() + "': maybe it doesn't exist?";
        RCLCPP_ERROR(node_->get_logger(), err.c_str());
        return grpc::Status(grpc::StatusCode::UNKNOWN, err);
    }

    return grpc::Status::OK;
}

grpc::Status CoreServiceRos2Impl::ServoControlStream(
    grpc::ServerContext* context,
    grpc::ServerReaderWriter<core::RobotState, core::ServoCommand>* stream) {
    
    (void)context;

    if (!robot_can_servo) {
        return grpc::Status(grpc::StatusCode::UNAVAILABLE, "Current robot is not servo-capable");
    }
    
    RCLCPP_INFO(node_->get_logger(), "ServoControlStream started");
    
    std::atomic<bool> stream_active{true};
    
    // Thread for reading commands from client
    std::thread read_thread([this, stream, &stream_active]() {
        core::ServoCommand command;
        while (stream_active && stream->Read(&command)) {
            if (emergency_stop_.load()) {
                RCLCPP_WARN(node_->get_logger(), "Emergency stop active, ignoring command");
                continue;
            }
            
            processServoCommand(command);
        }
        stream_active = false;
        RCLCPP_INFO(node_->get_logger(), "Client disconnected from servo stream");
    });
    
    // Thread for writing robot state to client
    std::thread write_thread([this, stream, &stream_active]() {
        rclcpp::Rate rate(100); // 100 Hz state feedback
        
        while (stream_active && rclcpp::ok()) {
            core::RobotState state;
            auto status = getRobotStateInternal(&state);
            
            if (status.ok() && !stream->Write(state)) {
                RCLCPP_WARN(node_->get_logger(), "Failed to write to stream");
                break;
            }
            
            rate.sleep();
        }
        stream_active = false;
    });
    
    // Wait for threads to complete
    read_thread.join();
    write_thread.join();
    
    RCLCPP_INFO(node_->get_logger(), "ServoControlStream ended");
    return grpc::Status::OK;
}

grpc::Status CoreServiceRos2Impl::EmergencyStop(
    grpc::ServerContext* context,
    const common::Empty* request,
    common::Status* response) {
    
    (void)context;
    (void)request;
    
    RCLCPP_WARN(node_->get_logger(), "EMERGENCY STOP ACTIVATED");
    emergency_stop_.store(true, std::memory_order_relaxed);

    if (robot_can_servo) {
        // Publish zero velocity commands
        geometry_msgs::msg::TwistStamped zero_twist;
        zero_twist.header.stamp = node_->now();
        if (move_group_) {
            std::shared_lock<std::shared_mutex> rlock(this->move_group_rwmutex_);
            zero_twist.header.frame_id = move_group_->getPlanningFrame();
        }
        twist_pub_->publish(zero_twist);
        
        control_msgs::msg::JointJog zero_jog;
        zero_jog.header.stamp = node_->now();
        // TODO: remove fixed frame_id
        zero_jog.header.frame_id = "base_link";
        joint_jog_pub_->publish(zero_jog);
    }

    // publish emergency_stop
    std_msgs::msg::Bool res;
    res.data = true;
    emergency_stop_pub_->publish(res);
    
    response->set_code(common::STATUS_SUCCESS);
    response->set_message("Emergency stop activated");
    
    return grpc::Status::OK;
}

void CoreServiceRos2Impl::jointStateCallback(const sensor_msgs::msg::JointState::SharedPtr msg) {
    std::lock_guard<std::mutex> lock(state_mutex_);
    latest_joint_state_ = msg;
}


void CoreServiceRos2Impl::processServoCommand(const core::ServoCommand& command) {
    if (command.has_twist_cmd()) {
        // Cartesian velocity control
        geometry_msgs::msg::TwistStamped twist_msg;
        const auto& twist_cmd = command.twist_cmd();

        const auto& original_twist_stamped = twist_cmd.twist();
        twist_msg.header.stamp = node_->now();
        twist_msg.twist.linear.x = original_twist_stamped.twist().linear().x();
        twist_msg.twist.linear.y = original_twist_stamped.twist().linear().y();
        twist_msg.twist.linear.z = original_twist_stamped.twist().linear().z();
        
        twist_msg.twist.angular.x = original_twist_stamped.twist().angular().x();
        twist_msg.twist.angular.y = original_twist_stamped.twist().angular().y();
        twist_msg.twist.angular.z = original_twist_stamped.twist().angular().z();

        // check twist cmd config and build frame_id
        core::TwistCmdType twistTy = twist_cmd.cmd_type();
        core::MoveGroupRequest spec_mg;
        std::string spec_frame_id = original_twist_stamped.header().frame_id();
        switch (twistTy) {
        case core::TwistCmdType::CMD_VEL:
            if (spec_frame_id.empty()) {
                RCLCPP_WARN(node_->get_logger(), "empty frame_id in TwistCommand: use default 'base_link'");
                // TODO: remove fixed frame_id
                twist_msg.header.frame_id = "base_link";
            } else {
                twist_msg.header.frame_id = spec_frame_id;
            }
            break;
        case core::TwistCmdType::MOVEIT:
            // get & use move_group
            spec_mg = twist_cmd.group();
            if (this->switchMoveGroupInternal(spec_mg.jmg_name())) {
                // failed to switch move group
                return;
            }
            // use move group ee link
            {
                std::shared_lock<std::shared_mutex> rlock(this->move_group_rwmutex_);
                twist_msg.header.frame_id = move_group_->getEndEffectorLink();
            }
            if (spec_frame_id != twist_msg.header.frame_id) {
                RCLCPP_WARN(node_->get_logger(),
                    "specific a frame_id that is a not end effector link at TwistCmdType::MOVEIT: ignored");
            }
            break;
        default:
            RCLCPP_ERROR(node_->get_logger(), "unsupported twist cmd type %d", twistTy);
            return;
        }
        
        twist_pub_->publish(twist_msg);
        
    } else if (command.has_joint_cmd()) {
        // Joint velocity control
        control_msgs::msg::JointJog jog_msg;
        const auto& joint_cmd = command.joint_cmd();
        
        jog_msg.header.stamp = node_->now();
        // TODO: remove fixed frame_id
        jog_msg.header.frame_id = "base_link";
        
        for (int i = 0; i < joint_cmd.name_size(); ++i) {
            jog_msg.joint_names.push_back(joint_cmd.name(i));
            jog_msg.velocities.push_back(joint_cmd.data(i));
        }
        
        joint_jog_pub_->publish(jog_msg);
        
    } else if (command.has_pose_cmd()) {
        // Pose servoing - convert to twist command
        // This requires computing the error between current and target pose
        RCLCPP_WARN(node_->get_logger(), 
            "Pose servoing not fully implemented, use twist commands");
    }
}

bool CoreServiceRos2Impl::switchMoveGroupInternal(const std::string& joint_model_group_name) {
    
    std::unique_lock<std::shared_mutex> wlock(this->move_group_rwmutex_);

    // use move_groups_ cache
    auto it = move_groups_.find(joint_model_group_name);
    if (it != move_groups_.end()) {
        move_group_ = it->second;
        return true;
    }

    // check move group
    if (joint_model_group_name.empty()) {
        RCLCPP_ERROR(node_->get_logger(), "invalid (empty) move group while switching move-group");
        return false;
    }
    // rebuild move group
    if (!this->move_group_ || this->move_group_->getName() != joint_model_group_name) {
        if (this->robot_model_->hasJointModelGroup(joint_model_group_name)) {
            this->move_group_ = std::make_shared<moveit::planning_interface::MoveGroupInterface>(
                node_, joint_model_group_name);
        } else {
            RCLCPP_ERROR(node_->get_logger(), "move group '%s' doesn't exist", joint_model_group_name.c_str());
        }
    }
    if (!this->move_group_) {
        RCLCPP_ERROR(node_->get_logger(), "cannot switch to move group '%s'", joint_model_group_name.c_str());
        return false;
    }

    // update move_groups_ cache
    move_groups_[joint_model_group_name] = this->move_group_;

    return true;
}

grpc::Status CoreServiceRos2Impl::getRobotStateInternal(core::RobotState* response) {
    std::lock_guard<std::mutex> lock(state_mutex_);
    
    if (!latest_joint_state_) {
        return grpc::Status(grpc::StatusCode::UNAVAILABLE, "No joint state");
    }
    
    auto* header = response->mutable_header();
    // TODO: add seq
    header->set_seq(0);
    header->set_timestamp(node_->now().seconds());
    // TODO: remove fixed frame_id
    header->set_frame_id("base_link");
    
    for (size_t i = 0; i < latest_joint_state_->name.size(); ++i) {
        response->add_name(latest_joint_state_->name[i]);
        response->add_position(i < latest_joint_state_->position.size() 
            ? latest_joint_state_->position[i] : 0.0);
        response->add_velocity(i < latest_joint_state_->velocity.size() 
            ? latest_joint_state_->velocity[i] : 0.0);
        response->add_effort(i < latest_joint_state_->effort.size() 
            ? latest_joint_state_->effort[i] : 0.0);
    }
    
    return grpc::Status::OK;
}


}   // namespace robot_sim

