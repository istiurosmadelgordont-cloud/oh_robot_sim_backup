
#include <grpcpp/grpcpp.h>
#include "control_stubs/sensing.grpc.pb.h"

#include "control_svc/service_manager.hpp"
#include "control_svc/core_service.ros2.hpp"
#include "control_svc/sensing_service.ros2.hpp"
#include "control_svc/mobility_ai_service.ros2.hpp"

#include <rclcpp/rclcpp.hpp>

namespace robot_sim {

using namespace std::chrono_literals;

uint64_t murmur3_hash64(const std::string& str, uint64_t seed = 0x123456789ABCDEF0) {
    const uint64_t c1 = 0x87C37B91114253D5;
    const uint64_t c2 = 0x4CF5AD432745937F;
    const size_t block_size = sizeof(uint64_t);
    const size_t len = str.size();
    const unsigned char* data = reinterpret_cast<const unsigned char*>(str.data());

    uint64_t hash = seed ^ (len * c1);

    for (size_t i = 0; i < len / block_size; ++i) {
        uint64_t block = *reinterpret_cast<const uint64_t*>(data + i * block_size);
        block *= c1;
        block = (block << 31) | (block >> 33);
        block *= c2;
        hash ^= block;
        hash = (hash << 27) | (hash >> 37);
        hash = hash * 5 + 0x52DCE729;
    }

    uint64_t tail = 0;
    for (size_t i = len - len % block_size; i < len; ++i) {
        tail |= static_cast<uint64_t>(data[i]) << (8 * (i % block_size));
    }
    tail *= c1;
    tail = (tail << 31) | (tail >> 33);
    tail *= c2;
    hash ^= tail;

    hash ^= hash >> 33;
    hash *= 0xFF51AFD7ED558CCD;
    hash ^= hash >> 33;
    hash *= 0xC4CEB9FE1A85EC53;
    hash ^= hash >> 33;

    return hash;
}


class ServiceManagerRos2Impl: public ServiceManager {
public:
    ServiceManagerRos2Impl(const std::string &grpc_addr): ServiceManager(grpc_addr) {
        // gRPC server will be created at start time

        // preparing for ROS2 node
        // ROS2 timer & node will be created when started
        // preparing for ROS2 node data containers
        for (const auto &interested_type: sensor_msg_types) {
            discovered_sensor_topics_.emplace(
                interested_type, std::vector<std::string>(10));
        }
    }
    ~ServiceManagerRos2Impl() {
        // ensure resources cleaned (best-effort)
        unregister_signal_handler();
        if (grpc_server_) {
            grpc_server_->Shutdown(std::chrono::system_clock::time_point(std::chrono::duration<int>(5)));
            grpc_server_.reset();
        }
        if (ros_node_) {
            rclcpp::shutdown();
            ros_node_.reset();
        }
    }

    /** @return is the start (sync) success */
    int start(int argc, char** argv) override {
        // initialize ROS2 node env
        rclcpp::init(argc, argv);

        // build ROS2 node & multi-thread callback groups
        this->ros_node_ = std::make_shared<rclcpp::Node>("service_manager_ros2impl");

        // check use_sim_time parameter
        bool use_sim_time = this->ros_node_->get_parameter("use_sim_time").as_bool();
        
        RCLCPP_INFO(this->ros_node_->get_logger(), 
            "Node initialized with use_sim_time: %s", 
            use_sim_time ? "TRUE" : "FALSE");

        // create callback groups for services and emergency
        this->core_cb_group_ = this->ros_node_->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
        this->sensing_cb_group_ = this->ros_node_->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
        this->agent_cb_group_ = this->ros_node_->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
        // Use unique reentrant callback group for navigation2 client in AgentService
        // Because there is thread block in gRPC handler: the client callback will be blocked
        this->dedicated_nav2client_cb_group_ = this->ros_node_->create_callback_group(rclcpp::CallbackGroupType::Reentrant);

        // emergency should be able to preempt -> keep it separate and spin on its own single-threaded executor
        this->emergency_cb_group_ = this->ros_node_->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);


        RCLCPP_INFO(this->ros_node_->get_logger(), "initalizing service manager");

        // set the static instance pointer & install our signal handler (replaces ROS2 default)
        set_instance_and_install_signal_handler(this);

        // start ROS2 topic update timer
        this->ros_node_timer_ = this->ros_node_->create_wall_timer(
            2s,
            std::bind(&ServiceManagerRos2Impl::timer_callback, this)
        );

        // create gRPC service
        core_svc_ = std::make_shared<CoreServiceRos2Impl>(this->ros_node_, core_cb_group_, emergency_cb_group_);
        sensing_svc_ = std::make_shared<SensingServiceRos2Impl>(this->ros_node_, sensing_cb_group_);
        agent_svc_ = std::make_shared<MobilityServiceRos2Impl>(
            this->ros_node_,
            agent_cb_group_,
            dedicated_nav2client_cb_group_,
            emergency_cb_group_);

        // Setup executors
        unsigned int hw_threads = std::max<unsigned int>(2, std::thread::hardware_concurrency()); // at least 2
        // this->main_executor_ = std::make_shared<ExecMulti>(hw_threads);
        rclcpp::ExecutorOptions exec_opts;   // keep defaults
        this->main_executor_ =
            std::make_shared<rclcpp::executors::MultiThreadedExecutor>(
                exec_opts,
                hw_threads,              // number_of_threads
                false,                   // yield_before_execute
                std::chrono::nanoseconds(-1)   // timeout
            );
        // this->emergency_executor_ = std::make_shared<ExecSingle>();
        rclcpp::ExecutorOptions emergency_opts;
        this->emergency_executor_ =
            std::make_shared<rclcpp::executors::SingleThreadedExecutor>(
                emergency_opts
            );
        
        // NOTE: default callback group of the node should be added!!! Otherwise vanilla ROS2 timers/param servers won't work.
        auto default_cb_group = this->ros_node_->get_node_base_interface()->get_default_callback_group();
        this->main_executor_->add_callback_group(default_cb_group, this->ros_node_->get_node_base_interface());

        // Add custom callback groups to custom executor (otherwise callbacks in callback group won't run)
        // Add **only** the intended callback groups to each executor so we control which executor runs which callbacks
        this->main_executor_->add_callback_group(core_cb_group_, this->ros_node_->get_node_base_interface());
        this->main_executor_->add_callback_group(sensing_cb_group_, this->ros_node_->get_node_base_interface());
        this->main_executor_->add_callback_group(agent_cb_group_, this->ros_node_->get_node_base_interface());
        this->main_executor_->add_callback_group(dedicated_nav2client_cb_group_, this->ros_node_->get_node_base_interface());

        // Emergency group gets its own executor (single thread)
        this->emergency_executor_->add_callback_group(emergency_cb_group_, this->ros_node_->get_node_base_interface());

        // build gRPC server
        grpc::ServerBuilder builder;
        builder.AddListeningPort(this->grpc_server_addr, grpc::InsecureServerCredentials());
        builder.RegisterService(this->core_svc_.get());
        builder.RegisterService(this->sensing_svc_.get());
        builder.RegisterService(this->agent_svc_.get());
        builder.SetSyncServerOption(grpc::ServerBuilder::SyncServerOption::MAX_POLLERS, 8);

        // async start gRPC services
        this->grpc_server_ = builder.BuildAndStart();
        if (!this->grpc_server_) {
            RCLCPP_ERROR(
                this->ros_node_->get_logger(),
                "failed to start grpc server on %s",
                this->grpc_server_addr.c_str());
            // uninstall our signal handler and cleanup instance pointer
            unregister_signal_handler();
            return 1;
        }
        RCLCPP_INFO(this->ros_node_->get_logger(), "############# gRPC services launched at %s #############",
            this->grpc_server_addr.c_str());

        // async start ROS2 node
        this->main_executor_thread_ = std::thread([this]() {
            RCLCPP_INFO(this->ros_node_->get_logger(), "# svc_mgr::main_executor spinning with %zu threads", this->main_executor_->get_number_of_threads());
            this->main_executor_->spin();
            RCLCPP_INFO(this->ros_node_->get_logger(), "# svc_mgr::main_executor stopped");
        });
        this->emergency_executor_thread_ = std::thread([this]() {
            RCLCPP_INFO(this->ros_node_->get_logger(), "# svc_mgr::emergency_executor spinning (dedicated thread)");
            this->emergency_executor_->spin();
            RCLCPP_INFO(this->ros_node_->get_logger(), "# svc_mgr::emergency_executor stopped");
        });
        RCLCPP_INFO(this->ros_node_->get_logger(),
            "###########################################################");
        // deprecated: single thread run
        // std::thread ros_node_thread([this]() {this->ros_node_main_procedure();});

        // Wait here until shutdown is requested (server_should_exit flag set)
        {
            std::unique_lock<std::mutex> lock(this->server_mtx);
            this->main_cv.wait(lock, [this]() { return this->server_should_exit.load(); });
        }

        RCLCPP_INFO(this->ros_node_->get_logger(), "shutting down gRPC server");

        // shutdown sequence triggered: first tell gRPC to stop (non-blocking), then wait
        if (this->grpc_server_) {
            // Shutdown gracefully; this unblocks rpc.Wait() below.
            this->grpc_server_->Shutdown();
        }
        // join ROS2 multi-thread executors
        if (this->main_executor_) {
            this->main_executor_->cancel(); // stop spinning
        }
        if (this->emergency_executor_) {
            this->emergency_executor_->cancel();
        }
        if (this->main_executor_thread_.joinable()) this->main_executor_thread_.join();
        if (this->emergency_executor_thread_.joinable()) this->emergency_executor_thread_.join();

        // allow ROS2 spin loop to break by calling rclcpp::shutdown()
        if (rclcpp::ok()) {
            rclcpp::shutdown();
        }
        // (single thread deprecated) join ROS thread: wait for ROS2 node main procedure thread to stop
        // ros_node_thread.join();
        // wait for gRPC Wait() to finish (if there is still an active server)
        if (this->grpc_server_) {
            this->grpc_server_->Wait();
        }

        // destroy gRPC server & ROS2 env manually
        this->grpc_server_.reset();
        this->ros_node_.reset();
        
        // uninstall our signal handler
        unregister_signal_handler();

        return 0;
    }

    // deprecated: default single thread executor
    // void ros_node_main_procedure() {
    //     RCLCPP_INFO(this->ros_node_->get_logger(), "ros2 node main procedure launched");
    //     // start main loop
    //     while (rclcpp::ok()) {
    //         // quick exit check without lock
    //         if (this->server_should_exit.load()) break;
    //         rclcpp::spin_some(this->ros_node_);
    //         // small sleep to avoid tight loop if spin_some returns immediately
    //         std::this_thread::sleep_for(std::chrono::milliseconds(10));
    //     }
    //     RCLCPP_INFO(this->ros_node_->get_logger(), "shutting down ros2 node");
    // }

    void exit_handler(int signum) {
        RCLCPP_INFO(
            this->ros_node_ ? this->ros_node_->get_logger() : rclcpp::get_logger("service_manager_ros2impl"), 
            "Signal %d received: initiating shutdown...", signum);
        
        // notify main routine (in `start`)
        {
            std::lock_guard<std::mutex> lock(this->server_mtx);
            this->server_should_exit.store(true);
        }
        this->main_cv.notify_all();

        // We *do not* call grpc_server_->Shutdown() or rclcpp::shutdown() here to avoid
        // doing non-reentrant calls inside a signal handler (if this was invoked directly).
        // Instead, the normal shutdown sequence in start() will perform Shutdown() and rclcpp::shutdown().
    }

    void timer_callback() {
        this->discoverSensorTopics();
        this->registerAllSensors();
    }

    void registerAllSensors() {
        const auto &cam_topics = this->discovered_sensor_topics_["sensor_msgs/msg/Image"];
        const auto &lidar_topics = this->discovered_sensor_topics_["sensor_msgs/msg/LaserScan"];
        const auto &imu_topics = this->discovered_sensor_topics_["sensor_msgs/msg/Imu"];
        // TODO: use sensor names in SDF
        for (const auto &cam_topic: cam_topics) {
            std::string name = "camera_" + std::to_string(murmur3_hash64(cam_topic));
            this->sensing_svc_->ensure_camera(name, cam_topic);
        }
        for (const auto &lidar_topic: lidar_topics) {
            std::string name = "lidar_" + std::to_string(murmur3_hash64(lidar_topic));
            this->sensing_svc_->ensure_lidar(name, lidar_topic);
        }
        for (const auto &imu_topic: imu_topics) {
            std::string name = "imu_" + std::to_string(murmur3_hash64(imu_topic));
            this->sensing_svc_->ensure_imu(name, imu_topic);
        }
    }
    // TODO: use sensor defs in SDF
    void discoverSensorTopics() {
        // clear the original sensors
        for (const auto &interested_type: sensor_msg_types) {
            this->discovered_sensor_topics_[interested_type].clear();
        }
        auto topics = this->ros_node_->get_topic_names_and_types();
        for (const auto& [topic_name, type_list] : topics) {
            for (const auto& msg_type : type_list) {
                if (std::find(sensor_msg_types.begin(), sensor_msg_types.end(), msg_type) 
                    != sensor_msg_types.end()) {
                    this->discovered_sensor_topics_[msg_type].push_back(topic_name);
                    RCLCPP_DEBUG(
                        this->ros_node_->get_logger(),
                        "Discover sensor topic with type '%s' with name '%s'",
                        msg_type.c_str(), topic_name.c_str());
                }
            }
        }
    }

    // ------------ gRPC server Utils --------------

    std::shared_ptr<CoreServiceRos2Impl> core_svc_;
    std::shared_ptr<SensingServiceRos2Impl> sensing_svc_;
    std::shared_ptr<MobilityServiceRos2Impl> agent_svc_;
    std::unique_ptr<grpc::Server> grpc_server_;

    std::mutex server_mtx;
    std::condition_variable main_cv;
    std::atomic<bool> server_should_exit { false };

    // ------------ ROS2 Node Utils --------------
    
    std::shared_ptr<rclcpp::Node> ros_node_;

    // Executors
    std::shared_ptr<rclcpp::executors::MultiThreadedExecutor> main_executor_;
    std::shared_ptr<rclcpp::executors::SingleThreadedExecutor> emergency_executor_;

    // Callback groups (one per critical service + emergency)
    rclcpp::CallbackGroup::SharedPtr core_cb_group_;
    rclcpp::CallbackGroup::SharedPtr sensing_cb_group_;
    rclcpp::CallbackGroup::SharedPtr agent_cb_group_;
    rclcpp::CallbackGroup::SharedPtr dedicated_nav2client_cb_group_;
    rclcpp::CallbackGroup::SharedPtr emergency_cb_group_;

    // executor threads
    std::thread main_executor_thread_;
    std::thread emergency_executor_thread_;

    std::shared_ptr<rclcpp::TimerBase> ros_node_timer_;
    static std::vector<std::string> sensor_msg_types;
    // {<sensor msg type>: [<sensor topic list>]}
    std::unordered_map<std::string, std::vector<std::string>> discovered_sensor_topics_;

    // ---------- signal handling helpers ----------

    // Static pointer to current manager instance used by the (static) C-style signal handler.
    static ServiceManagerRos2Impl* s_instance_;
    static void install_signal_handler() {
        // Note: set handlers for SIGINT and SIGTERM
        std::signal(SIGINT, &ServiceManagerRos2Impl::static_signal_handler);
        std::signal(SIGTERM, &ServiceManagerRos2Impl::static_signal_handler);
    }
    static void uninstall_signal_handler() {
        std::signal(SIGINT, SIG_DFL);
        std::signal(SIGTERM, SIG_DFL);
    }

    // called from start() to set instance and install handler
    static void set_instance_and_install_signal_handler(ServiceManagerRos2Impl* inst) {
        s_instance_ = inst;
        install_signal_handler();
    }
    static void unregister_signal_handler() {
        s_instance_ = nullptr;
        uninstall_signal_handler();
    }

    // static C-style handler that gets registered with std::signal()
    static void static_signal_handler(int signum) {
        // we forward to the instance if present; otherwise fallback to default behavior
        if (s_instance_) {
            // forward to instance method (not async-signal-safe in strict sense)
            s_instance_->exit_handler(signum);
        } else {
            // restore default and re-raise so default action occurs
            std::signal(signum, SIG_DFL);
            std::raise(signum);
        }
    }
};

std::vector<std::string> ServiceManagerRos2Impl::sensor_msg_types = {
    "sensor_msgs/msg/Image",
    "sensor_msgs/msg/LaserScan",
    "sensor_msgs/msg/Imu",
    "sensor_msgs/msg/PointCloud2",
    "sensor_msgs/msg/CameraInfo"
};
ServiceManagerRos2Impl* ServiceManagerRos2Impl::s_instance_ = nullptr;


}   // namespace robot_sim


int main(int argc, char *argv[]) {
    robot_sim::ServiceManagerRos2Impl svc_mgr("0.0.0.0:50051");
    return svc_mgr.start(argc, argv);
}

