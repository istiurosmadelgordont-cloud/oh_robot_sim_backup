
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/pose_with_covariance_stamped.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <std_msgs/msg/empty.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <tf2_ros/transform_listener.h>
#include <tf2_ros/buffer.h>

#if __has_include(<cv_bridge/cv_bridge.h>)
    #include <cv_bridge/cv_bridge.h>
#else
    #include <cv_bridge/cv_bridge.hpp>
#endif
#include <opencv2/opencv.hpp>
#include <yaml-cpp/yaml.h>
#include <fstream>


class PgmRichRecorderNode : public rclcpp::Node {
public:
    PgmRichRecorderNode(const std::string& output_file, bool continuous_mode = false)
        : Node("pgm_rich_annotator_node"),
          output_file_(output_file),
          continuous_mode_(continuous_mode),
          tf_buffer_(std::make_shared<tf2_ros::Buffer>(this->get_clock(), tf2::durationFromSec(10.0))),
          tf_listener_(std::make_shared<tf2_ros::TransformListener>(*tf_buffer_)) {

        // Subscribe to odometry for position and pose
        odom_sub_ = this->create_subscription<nav_msgs::msg::Odometry>(
            "/odom", 10,
            std::bind(&PgmRichRecorderNode::odomCallback, this, std::placeholders::_1));

        // Subscribe to camera data
        image_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
            "/rgbd_camera/image", 10,
            std::bind(&PgmRichRecorderNode::imageCallback, this, std::placeholders::_1));
        
        depth_image_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
            "/rgbd_camera/depth_image", 10,
            std::bind(&PgmRichRecorderNode::depthImageCallback, this, std::placeholders::_1));

        // Subscribe to record trigger topic
        if (continuous_mode_) {
            record_trigger_sub_ = this->create_subscription<std_msgs::msg::Empty>(
                "/pgm_rich/annotate", 10,
                std::bind(&PgmRichRecorderNode::recordTriggerCallback, this, std::placeholders::_1));
            RCLCPP_INFO(this->get_logger(), "Running in continuous mode, waiting for /pgm_rich/annotate triggers");
        }

        RCLCPP_INFO(this->get_logger(), "Data Annotator Node initialized. Output file: %s", output_file_.c_str());
    }

    void recordDataOnce() {
        RCLCPP_INFO(this->get_logger(), "Recording data once...");
        
        // Wait for data to be available
        rclcpp::Rate rate(10);
        int max_attempts = 50;
        int attempts = 0;
        
        while (rclcpp::ok() && attempts < max_attempts) {
            rclcpp::spin_some(this->get_node_base_interface());
            if (latest_odom_ && latest_image_ && latest_depth_image_) {
                break;
            }
            rate.sleep();
            attempts++;
        }

        if (!latest_odom_ || !latest_image_ || !latest_depth_image_) {
            RCLCPP_ERROR(this->get_logger(), "Failed to receive required data within timeout");
            return;
        }

        recordData();
        RCLCPP_INFO(this->get_logger(), "Data recorded successfully");
    }

private:
    void odomCallback(const nav_msgs::msg::Odometry::SharedPtr msg) {
        latest_odom_ = msg;
    }

    void imageCallback(const sensor_msgs::msg::Image::SharedPtr msg) {
        latest_image_ = msg;
    }
    
    void depthImageCallback(const sensor_msgs::msg::Image::SharedPtr msg) {
        latest_depth_image_ = msg;
    }

    void recordTriggerCallback(const std_msgs::msg::Empty::SharedPtr) {
        RCLCPP_INFO(this->get_logger(), "Annotate trigger received");
        recordData();
    }

    void recordData() {
        if (!latest_odom_ || !latest_image_ || !latest_depth_image_) {
            RCLCPP_WARN(this->get_logger(), "Missing data for recording");
            return;
        }

        // Create YAML structure
        YAML::Node data;
        
        // Add timestamp
        auto now = std::chrono::system_clock::now();
        auto timestamp = std::chrono::system_clock::to_time_t(now);
        std::stringstream ss;
        ss << std::put_time(std::localtime(&timestamp), "%Y-%m-%d_%H:%M:%S");
        data["timestamp"] = ss.str();

        // Add position
        data["position"]["x"] = latest_odom_->pose.pose.position.x;
        data["position"]["y"] = latest_odom_->pose.pose.position.y;
        data["position"]["z"] = latest_odom_->pose.pose.position.z;

        // Add orientation (quaternion)
        data["orientation"]["x"] = latest_odom_->pose.pose.orientation.x;
        data["orientation"]["y"] = latest_odom_->pose.pose.orientation.y;
        data["orientation"]["z"] = latest_odom_->pose.pose.orientation.z;
        data["orientation"]["w"] = latest_odom_->pose.pose.orientation.w;

        // Add velocity
        // data["velocity"]["linear"]["x"] = latest_odom_->twist.twist.linear.x;
        // data["velocity"]["linear"]["y"] = latest_odom_->twist.twist.linear.y;
        // data["velocity"]["linear"]["z"] = latest_odom_->twist.twist.linear.z;
        // data["velocity"]["angular"]["x"] = latest_odom_->twist.twist.angular.x;
        // data["velocity"]["angular"]["y"] = latest_odom_->twist.twist.angular.y;
        // data["velocity"]["angular"]["z"] = latest_odom_->twist.twist.angular.z;

        // Add camera data information
        data["image"]["width"] = latest_image_->width;
        data["image"]["height"] = latest_image_->height;
        data["image"]["encoding"] = latest_image_->encoding;
        data["image"]["frame_id"] = latest_image_->header.frame_id;

        // Save image to file
        try {
            cv_bridge::CvImagePtr cv_ptr = cv_bridge::toCvCopy(latest_image_, sensor_msgs::image_encodings::BGR8);
            std::string image_filename = output_file_.substr(0, output_file_.find_last_of('.')) + 
                                        "_" + ss.str() + ".jpg";
            // Replace spaces and colons in filename
            std::replace(image_filename.begin(), image_filename.end(), ' ', '_');
            std::replace(image_filename.begin(), image_filename.end(), ':', '-');
            
            cv::imwrite(image_filename, cv_ptr->image);
            data["image"]["image_file"] = image_filename;
            RCLCPP_INFO(this->get_logger(), "Image saved to: %s", image_filename.c_str());
        } catch (cv_bridge::Exception& e) {
            RCLCPP_ERROR(this->get_logger(), "cv_bridge exception: %s", e.what());
            data["image"]["image_file"] = "error_saving_image";
        }

        // Save depth image to file
        // NOTE: Here we convert float32 depth (meters) → uint16 PNG (millimeters)
        // This is the same scheme used by: OpenNI / Azure Kinect SDK / Intel RealSense (uint16 = depth_in_mm)
        // We can do this to recover:
        // depth = cv2.imread('file.png', cv2.IMREAD_UNCHANGED).astype(np.float32)
        // depth_m = depth / 1000.0
        try {
            cv_bridge::CvImageConstPtr depth_ptr;

            // Convert depth image depending on encoding
            if (latest_depth_image_->encoding == sensor_msgs::image_encodings::TYPE_32FC1 ||
                latest_depth_image_->encoding == sensor_msgs::image_encodings::MONO16 ||
                latest_depth_image_->encoding == sensor_msgs::image_encodings::TYPE_16UC1) {
                depth_ptr = cv_bridge::toCvCopy(latest_depth_image_);
            } else {
                // fallback: try to convert to 32FC1
                depth_ptr = cv_bridge::toCvCopy(latest_depth_image_, sensor_msgs::image_encodings::TYPE_32FC1);
            }

            cv::Mat depth_img = depth_ptr->image;

            // Output filename
            std::string depth_filename = output_file_.substr(0, output_file_.find_last_of('.')) +
                                        "_" + ss.str() + "_depth.png";
            std::replace(depth_filename.begin(), depth_filename.end(), ' ', '_');
            std::replace(depth_filename.begin(), depth_filename.end(), ':', '-');

            cv::Mat depth_to_save;

            // Convert depth image to 16UC1 PNG
            if (depth_img.type() == CV_32FC1) {
                // Depth in meters → convert to millimeters for storage
                depth_to_save = cv::Mat(depth_img.rows, depth_img.cols, CV_16UC1);
                for (int r = 0; r < depth_img.rows; ++r) {
                    for (int c = 0; c < depth_img.cols; ++c) {
                        float d = depth_img.at<float>(r, c);
                        if (std::isfinite(d) && d > 0.0f)
                            depth_to_save.at<uint16_t>(r, c) = static_cast<uint16_t>(d * 1000.0f);  // meters → mm
                        else
                            depth_to_save.at<uint16_t>(r, c) = 0;
                    }
                }
            } else if (depth_img.type() == CV_16UC1) {
                // Already suitable for PNG
                depth_to_save = depth_img.clone();
            } else {
                throw std::runtime_error("Unsupported depth image type for PNG export");
            }

            // Save depth map
            cv::imwrite(depth_filename, depth_to_save);
            data["image"]["depth_image_file"] = depth_filename;

            RCLCPP_INFO(this->get_logger(), "Depth image saved to: %s", depth_filename.c_str());

        } catch (cv_bridge::Exception& e) {
            RCLCPP_ERROR(this->get_logger(), "cv_bridge exception during depth saving: %s", e.what());
            data["image"]["depth_image_file"] = "error_saving_depth_image";
        } catch (std::exception& e) {
            RCLCPP_ERROR(this->get_logger(), "Depth save exception: %s", e.what());
            data["image"]["depth_image_file"] = "error_saving_depth_image";
        }

        // Try to get map to base_link transform
        // TODO: set frame ID by parameters
        try {
            auto transform = tf_buffer_->lookupTransform(
                "map", "base_link", 
                rclcpp::Time(0),  // Get latest available transform
                rclcpp::Duration::from_seconds(1.0));  // Wait up to 1 second
            data["map_transform"]["translation"]["x"] = transform.transform.translation.x;
            data["map_transform"]["translation"]["y"] = transform.transform.translation.y;
            data["map_transform"]["translation"]["z"] = transform.transform.translation.z;
            data["map_transform"]["rotation"]["x"] = transform.transform.rotation.x;
            data["map_transform"]["rotation"]["y"] = transform.transform.rotation.y;
            data["map_transform"]["rotation"]["z"] = transform.transform.rotation.z;
            data["map_transform"]["rotation"]["w"] = transform.transform.rotation.w;
        } catch (tf2::TransformException& ex) {
            RCLCPP_WARN(this->get_logger(), "Could not get map transform: %s", ex.what());
        }

        // Read existing data if file exists
        YAML::Node root;
        std::ifstream fin(output_file_);
        if (fin.good()) {
            root = YAML::Load(fin);
            fin.close();
            if (!root["annotations"]) {
                root["annotations"] = YAML::Node(YAML::NodeType::Sequence);
            }
        } else {
            root["annotations"] = YAML::Node(YAML::NodeType::Sequence);
        }

        // Append new record
        root["annotations"].push_back(data);

        // Write to file
        std::ofstream fout(output_file_);
        fout << root;
        fout.close();

        RCLCPP_INFO(this->get_logger(), "Data written to %s", output_file_.c_str());
    }

    std::string output_file_;
    bool continuous_mode_;
    
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr image_sub_;
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr depth_image_sub_;
    rclcpp::Subscription<std_msgs::msg::Empty>::SharedPtr record_trigger_sub_;

    nav_msgs::msg::Odometry::SharedPtr latest_odom_;
    sensor_msgs::msg::Image::SharedPtr latest_image_;
    sensor_msgs::msg::Image::SharedPtr latest_depth_image_;

    std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
    std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
};


int main(int argc, char** argv) {
    rclcpp::init(argc, argv);

    // Parse command-line arguments
    std::string output_file = "annotations.yaml";
    bool continuous_mode = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "-o" || arg == "--output") {
            if (i + 1 < argc) {
                output_file = argv[++i];
            }
        } else if (arg == "-c" || arg == "--continuous") {
            continuous_mode = true;
        } else if (arg == "-h" || arg == "--help") {
            std::cout << "Usage: " << argv[0] << " [OPTIONS]\n"
                      << "Options:\n"
                      << "  -o, --output FILE     Output YAML file (default: annotations.yaml)\n"
                      << "  -c, --continuous      Run in continuous mode, listening to /record topic\n"
                      << "  -h, --help            Show this help message\n";
            return 0;
        }
    }

    auto node = std::make_shared<PgmRichRecorderNode>(output_file, continuous_mode);

    if (continuous_mode) {
        // Run as a node and keep spinning
        rclcpp::spin(node);
    } else {
        // Record once and exit
        node->recordDataOnce();
    }

    rclcpp::shutdown();
    return 0;
}