
#include <rclcpp/rclcpp.hpp>
#include <mujoco/mujoco.h>
#include <sensor_msgs/msg/image.hpp>
#include <std_srvs/srv/trigger.hpp>

#include "mujoco_ros2_control/mujoco_ros2_control.hpp"
#include "mujoco_ros2_control/mujoco_rendering.hpp"


class MuJoCoRos2ControlNode: public rclcpp::Node {
public:
  MuJoCoRos2ControlNode(const rclcpp::NodeOptions &options)
  : rclcpp::Node("mujoco_ros2_control_node", options) {
    RCLCPP_INFO_STREAM(this->get_logger(), "Initializing mujoco_ros2_control node...");

    auto model_path = this->get_parameter("mujoco_model_path").as_string();
    this->load_model(model_path);
    this->init_data();
    this->init_cameras();
    // // register env reset handler
    // reset_srv_ = this->create_service<std_srvs::srv::Trigger>(
    //   "mujoco_sim_env/reset", std::bind(&MuJoCoRos2ControlNode::reset_env, this, std::placeholders::_1, std::placeholders::_2));
  }

  ~MuJoCoRos2ControlNode() {
    renderer->close();

    // free MuJoCo model and data
    mj_deleteData(mujoco_data);
    mj_deleteModel(mujoco_model);
  }

  void main_loop() {
    // run main loop, target real-time simulation and 60 fps rendering
    while (rclcpp::ok() && !renderer->is_close_flag_raised()) {
      // advance interactive simulation for 1/60 sec
      //  Assuming MuJoCo can simulate faster than real-time, which it usually can,
      //  this loop will finish on time for the next frame to be rendered at 60 fps.
      //  Otherwise add a cpu timer and exit this loop when it is time to render.
      mjtNum simstart = mujoco_data->time;
      while (mujoco_data->time - simstart < 1.0/60.0) {
        ros2_controller->update();
      }
      for (int i = 0; i < ncam; ++i) {
        publish_camera_image(i);
      }
      renderer->update();
    }
  }

  typedef rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr ImagePubPtr;

private:

  static std::string get_camera_type_str(int cam_type) {
      switch (cam_type) {
          case mjCAMLIGHT_FIXED:          return "FIXED";
          case mjCAMLIGHT_TRACK:          return "TRACK"; 
          case mjCAMLIGHT_TRACKCOM:       return "TRACKCOM";
          case mjCAMLIGHT_TARGETBODY:     return "TARGETBODY";
          case mjCAMLIGHT_TARGETBODYCOM:  return "TARGETBODYCOM";
          default:                        return "UNKNOWN";
      }
  }
  void load_model(std::string model_path) {
    // load and compile model
    char error[1000] = "Could not load binary model";
    if (std::strlen(model_path.c_str())>4 && !std::strcmp(model_path.c_str()+std::strlen(model_path.c_str())-4, ".mjb")) {
      mujoco_model = mj_loadModel(model_path.c_str(), 0);
    } else {
      mujoco_model = mj_loadXML(model_path.c_str(), 0, error, 1000);
    }
    if (!mujoco_model) {
      mju_error("Load model error: %s", error);
    }

    RCLCPP_INFO_STREAM(this->get_logger(), "Mujoco model has been successfully loaded !");
  }
  void init_data() {
    // make data
    mujoco_data = mj_makeData(mujoco_model);
    node = std::shared_ptr<rclcpp::Node>(this);

    RCLCPP_INFO(node->get_logger(), "initializing mujoco control...");

    // initialize mujoco control
    ros2_controller = new mujoco_ros2_control::MujocoRos2Control(node, mujoco_model, mujoco_data);
    ros2_controller->init();
    RCLCPP_INFO(node->get_logger(), "Mujoco ros2 controller has been successfully initialized !");

    // initialize mujoco redering
    renderer = mujoco_ros2_control::MujocoRendering::get_instance();
    renderer->init(node, mujoco_model, mujoco_data);
    RCLCPP_INFO(node->get_logger(), "Mujoco rendering has been successfully initialized !");
  }
  void init_cameras() {
    ncam = mujoco_model->ncam;
    RCLCPP_INFO(node->get_logger(), "%d camera(s) detected", ncam);
    cams.resize(ncam);
    for (int i = 0; i < ncam; ++i) {
      const char *cam_name = mj_id2name(mujoco_model, mjOBJ_CAMERA, i);
      if (cam_name == NULL) {
        RCLCPP_WARN(node->get_logger(), "camera with id %d not found", i);
        cams[i].width = cams[i].height = -1;
        continue;
      }
      RCLCPP_INFO(node->get_logger(), "the type of camera '%s' is '%s'",
        cam_name, MuJoCoRos2ControlNode::get_camera_type_str(mujoco_model->cam_mode[i]).c_str());
      // TODO: replace fixed values with requested variables
      cams[i].depth = false;
      cams[i].depth_pub = nullptr;
      cams[i].width = 640;
      cams[i].height = 480;
      cams[i].image_pub = register_camera_publisher(
        cam_name, mjCAMERA_FIXED, cams[i].width, cams[i].height);
    }
  }

  void reset_env(
    std_srvs::srv::Trigger_Request::SharedPtr request,
    std_srvs::srv::Trigger_Response::SharedPtr response) {
    ros2_controller->reset();
    response->success = true;
    response->message = "MuJoCo simulation env reset: success";
  }

  MuJoCoRos2ControlNode::ImagePubPtr
  register_camera_publisher(
    const std::string &cam_name, int cam_type, int W = 640, int H = 480,
    MuJoCoRos2ControlNode::ImagePubPtr *depth_pub = NULL) {

    RCLCPP_INFO(node->get_logger(),
      "registering %s camera '%s'...", (depth_pub == NULL) ? "rgb" : "rgbd", cam_name.c_str());
    auto image_pub_ = this->create_publisher<sensor_msgs::msg::Image>(
                    "cam/" + cam_name + "/image_raw", rclcpp::SensorDataQoS());
    if (depth_pub) {
      *depth_pub = this->create_publisher<sensor_msgs::msg::Image>(
        "cam/" + cam_name + "/depth", rclcpp::SensorDataQoS());
    }

    int cam_id = renderer->register_offscreen_camera(cam_name, W, H);

    RCLCPP_INFO(node->get_logger(), "camera MuJoCo id for '%s' is %d", cam_name.c_str(), cam_id);
    return image_pub_;
  }

  void publish_camera_image(int cam_id) {
    const auto &cam = cams[cam_id];
    if (cam.width <= 0) return; // skip invalid cam record
    std::vector<unsigned char> rgb(cam.width * cam.height * 3);
    
    if (cam.depth) {
      std::vector<float> depth(cam.width * cam.height);
      renderer->render_offscreen_camera(cam_id, rgb.data(), depth.data());
      // TODO: publish depth image
    } else {
      renderer->render_offscreen_camera(cam_id, rgb.data(), NULL);
    }
    // fill and publish a ROS2 Image message
    auto msg = sensor_msgs::msg::Image();
    msg.header.stamp = this->get_clock()->now();
    msg.header.frame_id = "cam_" + std::to_string(cam_id) + "_frame";
    msg.height = cam.height;
    msg.width  = cam.width;
    msg.encoding = "rgb8";
    msg.is_bigendian = 0;
    msg.step = 3 * cam.width;
    msg.data = std::move(rgb);

    cam.image_pub->publish(msg);
  }

  mjModel* mujoco_model;
  mjData* mujoco_data;
  rclcpp::Node::SharedPtr node; // this

  mujoco_ros2_control::MujocoRos2Control *ros2_controller;
  mujoco_ros2_control::MujocoRendering *renderer;

  // rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr reset_srv_;

  struct ModelCamera_t {
    ImagePubPtr image_pub;
    ImagePubPtr depth_pub;  // this is optional depending on depth flag
    int width;
    int height;
    bool depth;
  };
  std::vector<ModelCamera_t> cams;
  int ncam;
};


// main function
int main(int argc, const char** argv) {

  rclcpp::init(argc, argv);

  rclcpp::NodeOptions options;
  options.automatically_declare_parameters_from_overrides(true);
  auto node = std::make_shared<MuJoCoRos2ControlNode>(options);

  rclcpp::executors::MultiThreadedExecutor executor;
  auto sim_worker_thread = std::make_unique<std::thread>([&executor, &node]() {
      executor.add_node(node);
      executor.spin();
      executor.remove_node(node);
  });

  node->main_loop();

  sim_worker_thread->join();
  rclcpp::shutdown();

  return 1;
}
