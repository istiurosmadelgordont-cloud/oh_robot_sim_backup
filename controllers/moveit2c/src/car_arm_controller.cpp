#include <rclcpp/rclcpp.hpp>
#include <memory>

#if __has_include(<moveit/moveit_cpp/moveit_cpp.hpp>)
    #include <moveit/moveit_cpp/moveit_cpp.hpp>
#else
    #include <moveit/moveit_cpp/moveit_cpp.h>
    #define MOVEIT_HUMBLE
#endif
#if __has_include(<moveit/moveit_cpp/planning_component.hpp>)
    #include <moveit/moveit_cpp/planning_component.hpp>
#else
    #include <moveit/moveit_cpp/planning_component.h>
#endif

#include <geometry_msgs/msg/point_stamped.h>
#include <geometry_msgs/msg/twist.hpp>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
#include <tf2_eigen/tf2_eigen.hpp>

#include <sensor_msgs/msg/joint_state.hpp>

#include <moveit_visual_tools/moveit_visual_tools.h>

namespace rvt = rviz_visual_tools;

static const std::string NODENS = "";
static const std::string NODENAME = "car_arm_controller_node";

static const std::string ARM_PLANNING_GROUP = "arm_group";
static const std::string ARM_FRAME_ID = "link1";
static const std::string ARM_TIP_LINK = "gripper_link";
static const std::string GRIPPER_PLANNING_GROUP = "gripper_group";

static const std::string ready_arm_group_state_name = "ready";
static const std::string calib_arm_group_state_name = "calib";
static const std::string free_gripper_group_state_name = "free";

// the same as moveit_controllers.yaml
static const std::string MOVEIT_ARM_CONTROLLER_NAME = "arm_group_controller";
static const std::string MOVEIT_GRIPPER_CONTROLLER_NAME = "gripper_group_controller";

// ros2_controllers
static const std::vector<std::string> CONTROLLERS({MOVEIT_ARM_CONTROLLER_NAME, MOVEIT_GRIPPER_CONTROLLER_NAME});


class CarArmController: public rclcpp::Node {
public:
    CarArmController(std::string name, std::string ns, const rclcpp::NodeOptions &options)
    : rclcpp::Node(name, ns, options) {
        RCLCPP_INFO(this->get_logger(), "Node initializing...");
        RCLCPP_INFO(this->get_logger(), "Block for 1s for joint states...");
        rclcpp::sleep_for(std::chrono::seconds(1));

        auto shared_node = std::shared_ptr<CarArmController>(this);
        this->moveit_cpp_ptr = std::make_shared<moveit_cpp::MoveItCpp>(shared_node);
        this->moveit_cpp_ptr->getPlanningSceneMonitorNonConst()->providePlanningSceneService();

        this->arm_planning_component = std::make_shared<moveit_cpp::PlanningComponent>(
            ARM_PLANNING_GROUP, this->moveit_cpp_ptr);
        this->arm_model_ptr = this->moveit_cpp_ptr->getRobotModel();
        this->arm_joint_model_group_ptr = this->arm_model_ptr->getJointModelGroup(ARM_PLANNING_GROUP);
        
        // this->visual_tools = std::make_shared<moveit_visual_tools::MoveItVisualTools>(
        //     shared_node, ARM_FRAME_ID, NODENAME, moveit_cpp_ptr->getPlanningSceneMonitorNonConst());
        // this->visual_tools->deleteAllMarkers();
        // this->visual_tools->loadRemoteControl();

        this->relative_move_sub_ = this->create_subscription<geometry_msgs::msg::Twist>(
            "/arm_relative_move", 10,
            std::bind(&CarArmController::relative_move_callback, this, std::placeholders::_1));

        // Joint state publisher initialization
        this->joint_state_publisher_ = this->create_publisher<sensor_msgs::msg::JointState>(
            "/arm/joint_states", 10);

        // Create a timer to publish joint states at a fixed frequency
        this->joint_state_timer_ = this->create_wall_timer(
            std::chrono::milliseconds(1000),  // 1 Hz frequency
            std::bind(&CarArmController::publish_joint_states, this));
    }

    void reset_arm_pose() {
        // set the start state of the plan to the current state of the robot
        this->arm_planning_component->setStartStateToCurrentState();
    }

    /**
     * @brief set the start state of the planner (for plan ONLY).
     * @warning this will set the start state of the planner but not the robot itself!
     * @return true on success. false if the start pose is unreachable for the arm
     */
    bool set_arm_start_state_force(const geometry_msgs::msg::Pose &start_pose) {
        auto cur_state = this->moveit_cpp_ptr->getCurrentState();
        bool valid = cur_state->setFromIK(this->arm_joint_model_group_ptr, start_pose);
        this->arm_planning_component->setStartState(*cur_state);
        return valid;
    }

    /**
     * @note be careful of the target_pose.header.frame_id
     */
    void set_arm_pose(const geometry_msgs::msg::PoseStamped &target_pose, bool block = true) {
        // best practice: Plan from the real state whenever you intend to execute.
        this->arm_planning_component->setStartStateToCurrentState();
        this->arm_planning_component->setGoal(target_pose, ARM_TIP_LINK);

        RCLCPP_INFO(this->get_logger(),
            "Executing plan for arm with spec target pose (blocking=%d)...", block);
        this->_plan_and_execute(target_pose, block);
    }

    void set_arm_pose(const std::string &target_pose_name, bool block = true) {
        this->arm_planning_component->setStartStateToCurrentState();
        this->arm_planning_component->setGoal(target_pose_name);

        RCLCPP_INFO(this->get_logger(),
            "Executing plan for arm with pose name '%s' (blocking=%d)...", target_pose_name.c_str(), block);
        this->_plan_and_execute(block);
    }

    void relative_move_callback(const geometry_msgs::msg::Twist::ConstSharedPtr msg) {
        RCLCPP_INFO(this->get_logger(), "relative_move_callback: ");
        // // 1. 获取当前末端位姿
        // auto current_state = this->arm_planning_component->getStartState();
        // Eigen::Isometry3d current_pose = current_state->getGlobalLinkTransform(ARM_TIP_LINK);
        
        // // 2. 应用平移变换
        // current_pose.translation().x() += msg->linear.x;
        // current_pose.translation().y() += msg->linear.y;
        // current_pose.translation().z() += msg->linear.z;
        
        // // 3. 应用旋转变换 (使用四元数)
        // if (msg->angular.x != 0 || msg->angular.y != 0 || msg->angular.z != 0) {
        //     // 获取当前旋转的四元数表示
        //     Eigen::Quaterniond current_rotation(current_pose.rotation());
            
        //     // 创建旋转增量四元数 (使用固定坐标系)
        //     tf2::Quaternion rotation_delta;
        //     rotation_delta.setRPY(msg->angular.x, msg->angular.y, msg->angular.z);
            
        //     // 转换为 Eigen 四元数
        //     Eigen::Quaterniond delta_quat(
        //         rotation_delta.w(),
        //         rotation_delta.x(),
        //         rotation_delta.y(),
        //         rotation_delta.z()
        //     );
            
        //     // 应用旋转增量
        //     // Eigen::Quaterniond new_rotation = delta_quat * current_rotation;
        //     Eigen::Quaterniond new_rotation = current_rotation * delta_quat;
        //     new_rotation.normalize();
            
        //     // 更新姿态的旋转部分
        //     current_pose.linear() = new_rotation.toRotationMatrix();
        // }
        
        // // 4. 转换为PoseStamped
        // geometry_msgs::msg::PoseStamped target_pose;
        // target_pose.header.frame_id = ARM_FRAME_ID;
        // target_pose.header.stamp = this->get_clock()->now();
        // target_pose.pose = tf2::toMsg(current_pose);
        
        // // 5. 规划并执行
        // this->set_arm_pose(target_pose, false);

        geometry_msgs::msg::PoseStamped target_pose;
        target_pose.header.frame_id = ARM_TIP_LINK;
        target_pose.header.stamp = this->get_clock()->now();
        target_pose.pose.position.x = msg->linear.x;
        target_pose.pose.position.y = msg->linear.y;
        target_pose.pose.position.z = msg->linear.z;
        tf2::Quaternion rotation_delta;
        rotation_delta.setRPY(msg->angular.x, msg->angular.y, msg->angular.z);
        target_pose.pose.orientation.w = rotation_delta.getW();
        target_pose.pose.orientation.x = rotation_delta.getX();
        target_pose.pose.orientation.y = rotation_delta.getY();
        target_pose.pose.orientation.z = rotation_delta.getZ();

        this->set_arm_pose(target_pose, false);
    }

    /**
     * @brief Add/Remove object to/in planning scene, depending on the object's operation
     * @note You may want to build an object like this:
     * 
     * moveit_msgs::msg::CollisionObject collision_object;
     * collision_object.header.frame_id = ROBOT_FRAME_ID;
     * collision_object.id = "box";
     * 
     * shape_msgs::msg::SolidPrimitive box;
     * box.type = box.BOX;
     * box.dimensions = { 0.1, 0.4, 0.1 };
     * 
     * geometry_msgs::msg::Pose box_pose;
     * box_pose.position.x = 0.4;
     * box_pose.position.y = 0.0;
     * box_pose.position.z = 1.0;
     * 
     * collision_object.primitives.push_back(box);
     * collision_object.primitive_poses.push_back(box_pose);
     * collision_object.operation = collision_object.ADD;
     */
    void process_object_in_scene(const moveit_msgs::msg::CollisionObject &collision_object) {
        // Lock PlanningScene
        planning_scene_monitor::LockedPlanningSceneRW scene(
            this->moveit_cpp_ptr->getPlanningSceneMonitorNonConst());
        scene->processCollisionObjectMsg(collision_object);
        // Unlock PlanningScene
    }

    void print_pose_stamped(const geometry_msgs::msg::PoseStamped &pose) {
        RCLCPP_INFO(this->get_logger(), "PoseStamped { header.frame_id: %s, header.stamp: %d, "
            "pose: { position: { x: %f, y: %f, z: %f }, orientation: { x: %f, y: %f, z: %f, w: %f } } }",
            pose.header.frame_id.c_str(), pose.header.stamp.sec,
            pose.pose.position.x, pose.pose.position.y, pose.pose.position.z,
            pose.pose.orientation.x, pose.pose.orientation.y, pose.pose.orientation.z,
            pose.pose.orientation.w);
    }


    /* ----------- Visualization ----------- */

    // void block_for_prompt() {
    //     this->visual_tools->prompt("Press 'next' in the RvizVisualToolsGui window to continue...");
    // }

    // /**
    //  * @brief show the plan in RViz
    //  * @note If you want to use the start_state of the planner (msg), you can:
    //  * 
    //  * moveit::core::RobotState robot_state(robot_model_ptr);
    //  * moveit::core::robotStateMsgToRobotState(plan_solution.start_state, robot_state);
    //  * 
    //  * and provide robot_state as the start_state argument.
    //  * 
    //  * And you may want to use RobotState::getGlobalLinkTransform(<link_name>) to get the global pose of <link_name>.
    //  */
    // void show_move_animation(
    //     const geometry_msgs::msg::Pose &target_pose,
    //     const planning_interface::MotionPlanResponse &plan_solution,
    //     const moveit::core::JointModelGroup *joint_model_group,
    //     std::string tip_link_name) {
        
    //     moveit::core::RobotState start_state(this->arm_model_ptr);
    //     moveit::core::robotStateMsgToRobotState(plan_solution.start_state, start_state);

    //     // Visualize the start pose in Rviz
    //     this->visual_tools->publishAxisLabeled(start_state.getGlobalLinkTransform(tip_link_name), "start_pose");
    //     // Visualize the goal pose in Rviz
    //     this->visual_tools->publishAxisLabeled(target_pose, "target_pose");
    //     // Visualize the trajectory in Rviz
    //     this->visual_tools->publishTrajectoryLine(plan_solution.trajectory, joint_model_group);
    //     this->visual_tools->trigger();
    // }

    // void clear_window() {
    //     this->visual_tools->deleteAllMarkers();
    //     this->visual_tools->trigger();
    // }

private:

    void publish_joint_states() {
        // Create a JointState message
        auto joint_state_msg = sensor_msgs::msg::JointState();
        joint_state_msg.header.stamp = this->get_clock()->now();

        // Get current joint states from the robot model
        const moveit::core::RobotState &current_state = *this->moveit_cpp_ptr->getCurrentState();

        RCLCPP_INFO(this->get_logger(), "Joint model group: %s", this->arm_joint_model_group_ptr->getName().c_str());
        const std::vector<std::string> &joint_names = this->arm_joint_model_group_ptr->getVariableNames();
        std::vector<double> joint_values;
    
        // Get the joint values for the current state
        current_state.copyJointGroupPositions(this->arm_joint_model_group_ptr, joint_values);


        RCLCPP_INFO(this->get_logger(), "Joint Names: ");
        for (const auto& name : joint_names) {
            RCLCPP_INFO(this->get_logger(), "  %s", name.c_str());
        }

        RCLCPP_INFO(this->get_logger(), "Joint Values: ");
        for (double value : joint_values) {
            if (std::isnan(value) || std::isinf(value)) {
                RCLCPP_ERROR(this->get_logger(), "Invalid joint value: %f", value);
            } else {
                RCLCPP_INFO(this->get_logger(), "  %f", value);
            }
        }

        // Fill joint_state_msg with joint names and positions
        joint_state_msg.name = joint_names;
        joint_state_msg.position = joint_values;

        // Publish the joint state message
        joint_state_publisher_->publish(joint_state_msg);
    }

#ifndef MOVEIT_HUMBLE
    /**
     * @note set goal & start_state before you plane and execute.
     */
    void _plan_and_execute(const geometry_msgs::msg::PoseStamped &target_pose, bool block = true, bool visual = false) {
        const planning_interface::MotionPlanResponse plan_solution = this->arm_planning_component->plan();
        if (plan_solution) {
            if (visual) {
                // this->show_move_animation(
                //     target_pose.pose, plan_solution,
                //     this->arm_joint_model_group_ptr, ARM_TIP_LINK);
                // this->clear_window();
            }
            // and execute the plan if solution is valid
            moveit_controller_manager::ExecutionStatus result = this->moveit_cpp_ptr->execute(
                plan_solution.trajectory, block, CONTROLLERS);
            RCLCPP_INFO(this->get_logger(), "Plan execution status: %s", result.asString().c_str());
        } else {
            RCLCPP_ERROR(this->get_logger(), "Failed to plan for pose:");
            this->print_pose_stamped(target_pose);
            RCLCPP_ERROR(this->get_logger(),
                "Error code: %s", moveit::core::errorCodeToString(plan_solution.error_code).c_str());
        }
    }

    void _plan_and_execute(bool block = true) {
        const planning_interface::MotionPlanResponse plan_solution = this->arm_planning_component->plan();
        if (plan_solution) {
            moveit_controller_manager::ExecutionStatus result = this->moveit_cpp_ptr->execute(
                plan_solution.trajectory, block, CONTROLLERS);
            RCLCPP_INFO(this->get_logger(), "Plan execution status: %s", result.asString().c_str());
        } else {
            RCLCPP_ERROR(this->get_logger(),
                "Failed to plan. Error code: %s",
                moveit::core::errorCodeToString(plan_solution.error_code).c_str());
        }
    }
#else
    void _plan_and_execute(const geometry_msgs::msg::PoseStamped &target_pose, bool block = true, bool visual = false) {
        const moveit_cpp::PlanningComponent::PlanSolution plan_solution = this->arm_planning_component->plan();
        if (plan_solution) {
            if (visual) {
                // this->show_move_animation(
                //     target_pose.pose, plan_solution,
                //     this->arm_joint_model_group_ptr, ARM_TIP_LINK);
                // this->clear_window();
            }
            // and execute the plan if solution is valid
            moveit_controller_manager::ExecutionStatus result = this->moveit_cpp_ptr->execute(
                ARM_PLANNING_GROUP, plan_solution.trajectory, block);
            RCLCPP_INFO(this->get_logger(), "Plan execution status: %s", result.asString().c_str());
        } else {
            RCLCPP_ERROR(this->get_logger(), "Failed to plan for pose:");
            this->print_pose_stamped(target_pose);
            RCLCPP_ERROR(this->get_logger(),
                "Error code: %s", moveit::core::error_code_to_string(plan_solution.error_code).c_str());
        }
    }

    void _plan_and_execute(bool block = true) {
        const moveit_cpp::PlanningComponent::PlanSolution plan_solution = this->arm_planning_component->plan();
        if (plan_solution) {
            moveit_controller_manager::ExecutionStatus result = this->moveit_cpp_ptr->execute(
                ARM_PLANNING_GROUP, plan_solution.trajectory, block);
            RCLCPP_INFO(this->get_logger(), "Plan execution status: %s", result.asString().c_str());
        } else {
            RCLCPP_ERROR(this->get_logger(),
                "Failed to plan. Error code: %s",
                moveit::core::error_code_to_string(plan_solution.error_code).c_str());
        }
    }
#endif

    moveit_cpp::MoveItCppPtr moveit_cpp_ptr;
    moveit_cpp::PlanningComponentPtr arm_planning_component;
    moveit::core::RobotModelConstPtr arm_model_ptr;
    const moveit::core::JointModelGroup *arm_joint_model_group_ptr;
    // std::shared_ptr<moveit_visual_tools::MoveItVisualTools> visual_tools;

    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr relative_move_sub_;

    rclcpp::Publisher<sensor_msgs::msg::JointState>::SharedPtr joint_state_publisher_;
    rclcpp::TimerBase::SharedPtr joint_state_timer_;
};

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    rclcpp::NodeOptions node_options;
    node_options.automatically_declare_parameters_from_overrides(true);

    auto car_arm_controller = std::make_shared<CarArmController>(NODENAME, NODENS, node_options);

    car_arm_controller->set_arm_pose("ready");

    // We spin up a SingleThreadedExecutor for the current state monitor to get information
    // about the robot's state.
    rclcpp::executors::SingleThreadedExecutor executor;
    executor.add_node(car_arm_controller);
    // std::thread([&executor]() { executor.spin(); }).detach();
    executor.spin();

    rclcpp::shutdown();
    return 0;
}