
#include "control_svc/pose_manager.ros2.hpp"
#include "robot_sim_common/config.h"

const std::string PoseManager::init_pose_svc_name_ = robot_sim::POSE_MGR_SVC;


PoseManager::PoseManager(const rclcpp::NodeOptions & options, std::optional<std::string> pose_file)
    : Node("nav2sim_pose_manager", options), pose_file_(pose_file) {
    
    RCLCPP_INFO(this->get_logger(),
        "#################################################");
    RCLCPP_INFO(this->get_logger(), "###  PoseManager Started");
    RCLCPP_INFO(this->get_logger(),
        "#################################################");

    if (pose_file_.has_value() && load_pose_from_file(*pose_file_)) {
        RCLCPP_INFO(this->get_logger(), "loaded init_pose from: %s", pose_file_->c_str());
    } else {
        // default save file
        pose_file_.emplace("robot_sim.initial.pose");
        // default initial pose
        init_pose_.header.frame_id = "map";
        init_pose_.pose.pose.position.x = 0.0;
        init_pose_.pose.pose.position.y = 0.0;
        tf2::Quaternion q;
        q.setRPY(0, 0, 0);
        init_pose_.pose.pose.orientation = tf2::toMsg(q);
        // with 0 cov
        RCLCPP_INFO(this->get_logger(), "loaded with default initial pose");
    }
    current_pose_ = init_pose_;

    amcl_sub_ = this->create_subscription<geometry_msgs::msg::PoseWithCovarianceStamped>(
        "/amcl_pose", 10,
        std::bind(&PoseManager::amcl_callback, this, std::placeholders::_1));

    // Slow timer (e.g., 2Hz) to update pose (resource friendly)
    timer_ = this->create_wall_timer(
        std::chrono::milliseconds(500),
        std::bind(&PoseManager::timer_update, this));
    
    // publish to other services
    get_pose_srv_ = this->create_service<GetPose2DCov>(
        PoseManager::init_pose_svc_name_,
        std::bind(&PoseManager::get_pose, this,
                std::placeholders::_1, std::placeholders::_2));

    RCLCPP_INFO(this->get_logger(), "PoseManager initialized");
}

PoseManager::~PoseManager() {
    if (pose_file_.has_value()) {
        save_pose_to_file(*pose_file_);
    }
}

bool PoseManager::load_pose_from_file(const std::string & file) {
    std::ifstream fin(file);
    if (!fin.is_open())
        return false;

    double x=0, y=0, yaw_deg=0;
    fin >> x >> y >> yaw_deg;

    if (!fin.good())
        return false;

    init_pose_.header.frame_id = "map";
    init_pose_.pose.pose.position.x = x;
    init_pose_.pose.pose.position.y = y;

    auto &cov = init_pose_.pose.covariance;
    size_t actual_sz;
    fin >> actual_sz;
    if (actual_sz != cov.size())
        return false;
    for (size_t i = 0; i < actual_sz; i++) {
        fin >> cov[i];
    }

    tf2::Quaternion q;
    q.setRPY(0, 0, yaw_deg * M_PI/180.0);
    init_pose_.pose.pose.orientation = tf2::toMsg(q);

    return true;
}

void PoseManager::save_pose_to_file(const std::string & file) {
    tf2::Quaternion q(
        current_pose_.pose.pose.orientation.x,
        current_pose_.pose.pose.orientation.y,
        current_pose_.pose.pose.orientation.z,
        current_pose_.pose.pose.orientation.w);

    double roll, pitch, yaw;
    tf2::Matrix3x3(q).getRPY(roll, pitch, yaw);

    std::ofstream fout(file);
    fout << current_pose_.pose.pose.position.x << " "
            << current_pose_.pose.pose.position.y << " ";

    size_t actual_sz = current_pose_.pose.covariance.size();
    for (size_t i = 0; i < actual_sz; i++) {
        fout << current_pose_.pose.covariance[i] << " ";
    }
    fout << (yaw * 180.0 / M_PI) << "\n";
    RCLCPP_INFO(this->get_logger(), "saved pose to file: %s", file.c_str());
}

void PoseManager::amcl_callback(const geometry_msgs::msg::PoseWithCovarianceStamped::SharedPtr msg) {
    last_amcl_pose_ = *msg;  // store latest, update in timer
}

void PoseManager::timer_update() {
    if (last_amcl_pose_.has_value()) {
        const auto & p = last_amcl_pose_.value();
        current_pose_.header.stamp = this->get_clock()->now();
        current_pose_.pose = p.pose;
    }
}

void PoseManager::get_pose(const std::shared_ptr<GetPose2DCov::Request> req,
            std::shared_ptr<GetPose2DCov::Response> res) {
    (void)req;

    RCLCPP_INFO(this->get_logger(), "get_pose service called");

    res->success = true;
    res->pose = current_pose_;
}

int main(int argc, char * argv[]) {
    rclcpp::init(argc, argv);

    // Simple CLI parsing
    std::optional<std::string> pose_file;
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--pose_file" && i + 1 < argc) {
            pose_file = argv[i+1];
            i++;
        }
    }

    rclcpp::NodeOptions options;
    auto node = std::make_shared<PoseManager>(options, pose_file);

    rclcpp::spin(node);

    rclcpp::shutdown();
    return 0;
}

