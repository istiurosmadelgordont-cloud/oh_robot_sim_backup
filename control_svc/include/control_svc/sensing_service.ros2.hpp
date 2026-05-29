#pragma once

#include <grpcpp/grpcpp.h>
#include "control_stubs/sensing.grpc.pb.h"
#include "control_stubs/common.pb.h"

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>
#include <sensor_msgs/msg/imu.hpp>

#if __has_include(<cv_bridge/cv_bridge.h>)
	#include <cv_bridge/cv_bridge.h>
#else
	#include <cv_bridge/cv_bridge.hpp>
#endif
#include <opencv2/opencv.hpp>

#include <mutex>
#include <condition_variable>
#include <unordered_map>
#include <deque>
#include <atomic>
#include <memory>
#include <vector>
#include <chrono>


namespace robot_sim {


class SensingServiceRos2Impl final : public robot_sim::sensing::SensingService::Service {
public:
	explicit SensingServiceRos2Impl(
		rclcpp::Node::SharedPtr node,
		rclcpp::CallbackGroup::SharedPtr sensing_cb);
	~SensingServiceRos2Impl() override = default;

	// gRPC methods
	grpc::Status ListSensors(
		grpc::ServerContext* context,
		const robot_sim::common::Empty* request,
		robot_sim::sensing::SensorMetaList* response
	) override;
	
	grpc::Status GetSensors(
		grpc::ServerContext* context,
		const robot_sim::sensing::SensorRequest* request,
		robot_sim::sensing::SensorData* response
	) override;

	grpc::Status StreamSensors(
		grpc::ServerContext* context,
		const robot_sim::sensing::SensorRequest* request,
		grpc::ServerWriter<robot_sim::sensing::SensorData>* writer
	) override;

	// Runtime registration of sensors
	void ensure_camera(const std::string &name, const std::string &topic);
	void ensure_lidar(const std::string &name, const std::string &topic);
	void ensure_imu(const std::string &name, const std::string &topic);

private:

	template <typename SensorMessageT>
    using SensorCallback = void (SensingServiceRos2Impl::*)(const std::string&, const std::shared_ptr<SensorMessageT>);

	template <typename SensorMessageT, typename SensorSnapshotT>
	void register_common(
		const std::string &name, const std::string &topic,
		std::unordered_map<std::string, std::shared_ptr<rclcpp::Subscription<SensorMessageT>>> &sensor_subs_,
		std::unordered_map<std::string, SensorSnapshotT> &sensors_,
		SensorCallback<SensorMessageT> callback
	);

	/** @return should register */
	template <typename SensorMessageT, typename SensorSnapshotT>
	bool ensure_common(
		const std::string &name, const std::string &topic,
		std::unordered_map<std::string, std::shared_ptr<rclcpp::Subscription<SensorMessageT>>> &sensor_subs_
	);

	void register_camera(const std::string &name, const std::string &topic);
	void register_lidar(const std::string &name, const std::string &topic);
	void register_imu(const std::string &name, const std::string &topic);

	// Callbacks for ROS2 subscriptions
	void camera_callback(const std::string &name, const sensor_msgs::msg::Image::SharedPtr msg);
	void lidar_callback(const std::string &name, const sensor_msgs::msg::LaserScan::SharedPtr msg);
	void imu_callback(const std::string &name, const sensor_msgs::msg::Imu::SharedPtr msg);

	// Helper to populate header
	void fill_common_header(robot_sim::common::Header* out, const rclcpp::Time &stamp, const std::string &frame);

	// Produce a SensorData message for the requested set of sensors using latest snapshots
	void build_sensor_data(const std::vector<std::string> &names, robot_sim::sensing::SensorData* out);

	// Internal types to hold latest data
	struct CameraSnapshot {
		rclcpp::Time stamp;
		std::string frame_id;
		cv::Mat color; // empty if not available
		cv::Mat depth; // float32 depth in meters, empty if not available
		std::string encoding; // original encoding of color image
	};

	struct LidarSnapshot {
		rclcpp::Time stamp;
		std::string frame_id;
		sensor_msgs::msg::LaserScan::SharedPtr msg;
	};

	struct ImuSnapshot {
		rclcpp::Time stamp;
		std::string frame_id;
		sensor_msgs::msg::Imu::SharedPtr msg;
	};

	rclcpp::Node::SharedPtr node_;
	rclcpp::CallbackGroup::SharedPtr sensing_cb_group_;
	std::mutex data_mutex_;

	// maps by sensor name
	std::unordered_map<std::string, CameraSnapshot> cameras_;
	std::unordered_map<std::string, LidarSnapshot> lidars_;
	std::unordered_map<std::string, ImuSnapshot> imus_;

	// ros subscriptions stored so they remain alive
	std::unordered_map<std::string, rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr> camera_subs_;
	std::unordered_map<std::string, rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr> lidar_subs_;
	std::unordered_map<std::string, rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr> imu_subs_;

	// cache map for {sensor topic -> sensor name}
	std::unordered_map<std::string, std::string> topic_to_sensor_name_;

	// notify streaming threads when there's an update
	std::condition_variable_any update_cv_;
	std::atomic<bool> shutting_down_{false};

	// Helper to mark update and wake streaming threads
	void notify_update();
};


}	// namespace robot_sim