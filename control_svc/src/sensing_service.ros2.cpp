
#include "control_svc/sensing_service.ros2.hpp"

namespace robot_sim {

using namespace std::chrono_literals;

// convenience aliases for proto types
using sensing::SensorRequest;
using sensing::SensorMetaList;
using sensing::SensorType;
using sensing::SensorData;
using sensing::CameraImage;
using sensing::LidarScan;
using sensing::ImuData;
using common::Header;

SensingServiceRos2Impl::SensingServiceRos2Impl(
    rclcpp::Node::SharedPtr node,
    rclcpp::CallbackGroup::SharedPtr sensing_cb)
: node_(std::move(node)),
    sensing_cb_group_(std::move(sensing_cb)) {
    // Nothing else registered automatically; the framework should call register_* for sensors it knows about.
}

template <typename SensorMessageT, typename SensorSnapshotT>
void SensingServiceRos2Impl::register_common(
    const std::string &name, const std::string &topic,
    std::unordered_map<std::string, std::shared_ptr<rclcpp::Subscription<SensorMessageT>>> &sensor_subs_,
    std::unordered_map<std::string, SensorSnapshotT> &sensors_,
    SensorCallback<SensorMessageT> callback
) {
    // first lock and insert a placeholder to ensure that
    // when the callback is triggered, the entry already exists in sensors_.
    std::lock_guard<std::mutex> lk(data_mutex_);

    // create the entry of map{sensor name -> data snapshot}
    auto [_s_it, inserted] = sensors_.emplace(name, SensorSnapshotT());
    if (!inserted) {
        RCLCPP_WARN(node_->get_logger(), "sensor '%s' already registered: ignored", name.c_str());
        return;
    }

    // create the subscription
    rclcpp::SubscriptionOptions options;
    options.callback_group = sensing_cb_group_;

    auto sub = node_->create_subscription<SensorMessageT>(
        topic, rclcpp::SensorDataQoS(),
        [this, callback, name](std::shared_ptr<SensorMessageT> msg) {
            (this->*callback)(name, msg);
        },
        options
    );

    // create the entry of map{topic -> sensor name}
    topic_to_sensor_name_[topic] = name;

    // create the entry of map{sensor name -> topic subscriber ptr}
    auto [_ssub_it, sub_inserted] = sensor_subs_.emplace(name, sub);
    if (!sub_inserted) {
        RCLCPP_WARN(node_->get_logger(),
            "data corruption: sensor '%s' already registered but snapshot list untouched", name.c_str());
        return;
    }
}

template <typename SensorMessageT, typename SensorSnapshotT>
bool SensingServiceRos2Impl::ensure_common(
    const std::string &name, const std::string &topic,
    std::unordered_map<std::string, std::shared_ptr<rclcpp::Subscription<SensorMessageT>>> &sensor_subs_
) {
    std::lock_guard<std::mutex> lk(data_mutex_);

    // validate name & topic
    if (name.empty() || topic.empty()) {
        RCLCPP_ERROR(node_->get_logger(), "invalid (empty) sensor name or topic: rejected");
        return false;
    }

    // check duplicated topic
    auto dup_topic_it = topic_to_sensor_name_.find(topic);

    if (dup_topic_it != topic_to_sensor_name_.end()) {
        std::string binded_sensor_name = dup_topic_it->second;
        if (binded_sensor_name == name) {
            // same name with same topic
            RCLCPP_DEBUG(node_->get_logger(),
                "sensor '%s' already subscribes to '%s', no change", name.c_str(), topic.c_str());
            return false;
        } else {
            // same topic with different names (registered or not registered sensor names)
            RCLCPP_ERROR(node_->get_logger(),
                "ensure different sensor name ('%s') with a same topic ('%s') which is subscribed by sensor '%s': alias is not supported",
                name.c_str(), topic.c_str(), dup_topic_it->second.c_str());
            return false;
        }
    }

    // check registered name
    auto sensor_sub_it = sensor_subs_.find(name);
    if (sensor_sub_it != sensor_subs_.end()) {
        std::string sensor_sub_topic = sensor_sub_it->second->get_topic_name();
        assert(sensor_sub_topic != topic);
        // same name with different topics: override the previous topic
        RCLCPP_INFO(node_->get_logger(),
                "override the previous topic '%s' to '%s' for sensor '%s'",
                sensor_sub_topic.c_str(), topic.c_str(), name.c_str());
        
        // free the topic subscriber in the old mapping of sensor `name`
        sensor_sub_it->second.reset();
        // remove the old mapping of sensor `name` in {sensor name -> topic subscriber ptr}
        sensor_subs_.erase(sensor_sub_it);
        // also remove the old mapping of sensor `name` in {topic -> sensor name}
        auto cur_map_it = topic_to_sensor_name_.find(sensor_sub_topic);
        if (cur_map_it == topic_to_sensor_name_.end()) {
            RCLCPP_ERROR(node_->get_logger(),
                "data corruption: sensor '%s' registered but topic (%s) is not recorded in map{topic -> sensor name}",
                name.c_str(), sensor_sub_topic.c_str());
        } else {
            topic_to_sensor_name_.erase(cur_map_it);
        }
        // also flush the snapshot? Not necessary
        // sensors_.erase(name);
    }

    return true;
}

void SensingServiceRos2Impl::register_camera(const std::string &name, const std::string &topic) {

    this->register_common<sensor_msgs::msg::Image, CameraSnapshot>(
        name, topic,
        this->camera_subs_, this->cameras_,
        &SensingServiceRos2Impl::camera_callback);

    RCLCPP_INFO(node_->get_logger(), "Registered camera '%s' listening on '%s'", name.c_str(), topic.c_str());
}

void SensingServiceRos2Impl::register_lidar(const std::string &name, const std::string &topic) {
    
    this->register_common<sensor_msgs::msg::LaserScan, LidarSnapshot>(
        name, topic,
        this->lidar_subs_, this->lidars_,
        &SensingServiceRos2Impl::lidar_callback);
    
    RCLCPP_INFO(node_->get_logger(), "Registered lidar '%s' listening on '%s'", name.c_str(), topic.c_str());
}

void SensingServiceRos2Impl::register_imu(const std::string &name, const std::string &topic) {
    
    this->register_common<sensor_msgs::msg::Imu, ImuSnapshot>(
        name, topic,
        this->imu_subs_, this->imus_,
        &SensingServiceRos2Impl::imu_callback);
    
    RCLCPP_INFO(node_->get_logger(), "Registered imu '%s' listening on '%s'", name.c_str(), topic.c_str());
}

void SensingServiceRos2Impl::ensure_camera(const std::string &name, const std::string &topic) {
    if (this->ensure_common<sensor_msgs::msg::Image, CameraSnapshot>(
        name, topic, this->camera_subs_)) {

        this->register_camera(name, topic);
    }
}

void SensingServiceRos2Impl::ensure_lidar(const std::string &name, const std::string &topic) {
    if (this->ensure_common<sensor_msgs::msg::LaserScan, LidarSnapshot>(
        name, topic, this->lidar_subs_)) {

        this->register_lidar(name, topic);
    }
}

void SensingServiceRos2Impl::ensure_imu(const std::string &name, const std::string &topic) {
    if (this->ensure_common<sensor_msgs::msg::Imu, ImuSnapshot>(
        name, topic, this->imu_subs_)) {

        this->register_imu(name, topic);
    }
}

void SensingServiceRos2Impl::camera_callback(const std::string &name, const sensor_msgs::msg::Image::SharedPtr msg) {
    try {
        cv_bridge::CvImageConstPtr cv_ptr = cv_bridge::toCvShare(msg, msg->encoding);
        CameraSnapshot snap;
        snap.stamp = rclcpp::Time(msg->header.stamp);
        snap.frame_id = msg->header.frame_id;
        snap.encoding = msg->encoding;

        // Distinguish color vs depth by encoding or name:
        // If encoding indicates 32FC1 or 16UC1 treat it as depth, otherwise as color.
        if (msg->encoding == "32FC1" || msg->encoding == "16UC1") {
            // depth
            if (cv_ptr->image.type() == CV_32FC1) {
                snap.depth = cv_ptr->image.clone();
            } else if (cv_ptr->image.type() == CV_16UC1) {
                // convert to float32 in meters (assumes mm if common)
                cv_ptr->image.convertTo(snap.depth, CV_32F, 1.0); // caller must ensure scale if needed
            } else {
                // fallback: convert single channel to float
                cv_ptr->image.convertTo(snap.depth, CV_32F);
            }
        } else {
            // color: convert to BGR8 cv::Mat (OpenCV default)
            cv::Mat color_mat;
            if (msg->encoding == "rgb8") {
                cv::cvtColor(cv_ptr->image, color_mat, cv::COLOR_RGB2BGR);
            } else if (msg->encoding == "bgr8") {
                color_mat = cv_ptr->image.clone();
            } else if (msg->encoding == "mono8") {
                cv::cvtColor(cv_ptr->image, color_mat, cv::COLOR_GRAY2BGR);
            } else {
                // fallback - try to convert to BGR
                cv_ptr->image.convertTo(color_mat, CV_8UC3);
            }
            snap.color = color_mat;
        }

        {
            std::lock_guard<std::mutex> lk(data_mutex_);
            auto it = cameras_.find(name);
            if (it == cameras_.end()) {
                // in case it wasn't pre-registered
                cameras_.emplace(name, snap);
            } else {
                // merge: if color or depth empty keep existing other channel
                if (!snap.color.empty())
                    it->second.color = std::move(snap.color);
                if (!snap.depth.empty())
                    it->second.depth = std::move(snap.depth);
                it->second.stamp = snap.stamp;
                it->second.frame_id = snap.frame_id;
                it->second.encoding = snap.encoding;
            }
        }

        notify_update();

    } catch (const cv_bridge::Exception &e) {
        RCLCPP_WARN(node_->get_logger(), "cv_bridge exception in camera_callback(%s): %s", name.c_str(), e.what());
    } catch (const std::exception &e) {
        RCLCPP_WARN(node_->get_logger(), "Exception in camera_callback(%s): %s", name.c_str(), e.what());
    }
}

void SensingServiceRos2Impl::lidar_callback(const std::string &name, const sensor_msgs::msg::LaserScan::SharedPtr msg) {
    {
        std::lock_guard<std::mutex> lk(data_mutex_);
        auto &snap = lidars_[name]; // creates if missing due to operator[]
        snap.stamp = rclcpp::Time(msg->header.stamp);
        snap.frame_id = msg->header.frame_id;
        snap.msg = msg;
    }
    notify_update();
}

void SensingServiceRos2Impl::imu_callback(const std::string &name, const sensor_msgs::msg::Imu::SharedPtr msg) {
    {
        std::lock_guard<std::mutex> lk(data_mutex_);
        auto &snap = imus_[name];
        snap.stamp = rclcpp::Time(msg->header.stamp);
        snap.frame_id = msg->header.frame_id;
        snap.msg = msg;
    }
    notify_update();
}

void SensingServiceRos2Impl::notify_update() {
    update_cv_.notify_all();
}

void SensingServiceRos2Impl::fill_common_header(common::Header* out, const rclcpp::Time &stamp, const std::string &frame) {
    if (!out) return;
    // TODO: optionally increment a sequence counter per-sensor
    out->set_seq(0);
    double seconds = stamp.seconds();
    out->set_timestamp(seconds);
    out->set_frame_id(frame);
}

void SensingServiceRos2Impl::build_sensor_data(const std::vector<std::string> &names, sensing::SensorData* out) {
    if (!out) return;

    std::lock_guard<std::mutex> lk(data_mutex_);

    // fill header with "now" at top-level if any sensor present
    rclcpp::Time now = node_->now();

    for (const auto &name : names) {
        // cameras
        auto cam_it = cameras_.find(name);
        if (cam_it != cameras_.end()) {
            const CameraSnapshot &snap = cam_it->second;
            if (!snap.color.empty()) {
                CameraImage *ci = out->add_images();
                ci->set_name(name);
                ci->set_height((uint32_t)snap.color.rows);
                ci->set_width((uint32_t)snap.color.cols);
                ci->set_encoding("bgr8");
                ci->set_is_bigendian(false);
                ci->set_step((uint32_t)(snap.color.step));
                // encode JPEG to reduce size
                std::vector<uchar> buf;
                cv::imencode(".jpg", snap.color, buf);
                ci->set_data(std::string(reinterpret_cast<char*>(buf.data()), buf.size()));
                fill_common_header(ci->mutable_header(), now, snap.frame_id);
            }
            if (!snap.depth.empty()) {
                CameraImage *di = out->add_images();
                di->set_name(name);
                di->set_height((uint32_t)snap.depth.rows);
                di->set_width((uint32_t)snap.depth.cols);
                di->set_encoding("32FC1");
                di->set_is_bigendian(false);
                di->set_step((uint32_t)(snap.depth.step));
                // depth as float32 raw bytes (row-major)
                size_t bytes = (size_t)snap.depth.total() * snap.depth.elemSize();
                di->set_data(std::string(reinterpret_cast<const char*>(snap.depth.data), bytes));
                fill_common_header(di->mutable_header(), now, snap.frame_id);
            }
            continue;
        }

        // lidars
        auto lidar_it = lidars_.find(name);
        if (lidar_it != lidars_.end() && lidar_it->second.msg) {
            const auto &snap = lidar_it->second;
            const auto &msg = snap.msg;
            LidarScan *ls = out->add_lidars();
            ls->set_name(name);
            ls->set_angle_min(msg->angle_min);
            ls->set_angle_max(msg->angle_max);
            ls->set_angle_increment(msg->angle_increment);
            for (auto r : msg->ranges) ls->add_ranges(r);
            for (auto i : msg->intensities) ls->add_intensities(i);
            // update frame id
            fill_common_header(ls->mutable_header(), now, snap.frame_id);
            continue;
        }

        // imus
        auto imu_it = imus_.find(name);
        if (imu_it != imus_.end() && imu_it->second.msg) {
            const auto &snap = imu_it->second;
            const auto &msg = snap.msg;
            ImuData *im = out->add_imus();
            im->set_name(name);
            auto *q = im->mutable_orientation();
            q->set_x(msg->orientation.x);
            q->set_y(msg->orientation.y);
            q->set_z(msg->orientation.z);
            q->set_w(msg->orientation.w);
            auto *av = im->mutable_angular_velocity();
            av->set_x(msg->angular_velocity.x);
            av->set_y(msg->angular_velocity.y);
            av->set_z(msg->angular_velocity.z);
            auto *la = im->mutable_linear_acceleration();
            la->set_x(msg->linear_acceleration.x);
            la->set_y(msg->linear_acceleration.y);
            la->set_z(msg->linear_acceleration.z);
            // update frame id
            fill_common_header(im->mutable_header(), now, snap.frame_id);
            continue;
        }

        // If sensor not found we simply ignore it (could set warnings instead)
    }
}

grpc::Status SensingServiceRos2Impl::ListSensors(
    grpc::ServerContext* context,
    const common::Empty* request,
    sensing::SensorMetaList* response
) {
    (void)context;
    (void)request;

    std::lock_guard<std::mutex> lk(data_mutex_);
    for (const auto &cam: cameras_) {
        auto *entry = response->add_entries();
        entry->set_name(cam.first);
        entry->set_type(SensorType::CAMERA);
    }
    for (const auto &lidar: lidars_) {
        auto *entry = response->add_entries();
        entry->set_name(lidar.first);
        entry->set_type(SensorType::LIDAR);
    }
    for (const auto &imu: imus_) {
        auto *entry = response->add_entries();
        entry->set_name(imu.first);
        entry->set_type(SensorType::IMU);
    }
    return grpc::Status::OK;
}

grpc::Status SensingServiceRos2Impl::GetSensors(
    grpc::ServerContext* context,
    const SensorRequest* request,
    SensorData* response
) {
    (void)context;

    std::vector<std::string> names;
    for (int i = 0; i < request->sensor_names_size(); ++i)
        names.push_back(request->sensor_names(i));

    build_sensor_data(names, response);
    return grpc::Status::OK;
}

grpc::Status SensingServiceRos2Impl::StreamSensors(
    grpc::ServerContext* context,
    const SensorRequest* request,
    grpc::ServerWriter<SensorData>* writer
) {
    // Prepare requested names once
    std::vector<std::string> names;
    for (int i = 0; i < request->sensor_names_size(); ++i)
        names.push_back(request->sensor_names(i));

    // simple streaming strategy:
    // - wake on any update (notify_update) or every X ms to send the latest snapshot
    // - respect client cancellation via context->IsCancelled()

    const std::chrono::milliseconds max_period{100}; // 10Hz default
    while (!context->IsCancelled() && !shutting_down_) {
        // wait for update or timeout
        std::unique_lock<std::mutex> lk(data_mutex_);
        // using condition_variable_any to work with mutex type
        update_cv_.wait_for(lk, max_period);   // wake on notify or timeout
        // release lock before calling build_sensor_data which locks internally
        lk.unlock();

        // build under its own lock (build_sensor_data uses lock internally)
        SensorData data;
        build_sensor_data(names, &data);

        // Try to send; if sending fails (client disconnected), stop streaming
        if (!writer->Write(data)) {
            // client disconnected
            break;
        }
        // loop continues, will wait again for next update or timeout
    }
    return grpc::Status::OK;
}


}   // namespace robot_sim