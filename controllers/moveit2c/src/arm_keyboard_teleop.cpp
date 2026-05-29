#include <rclcpp/rclcpp.hpp>
#include <interfaces/srv/move_arm.hpp>
#include <termios.h>
#include <unistd.h>
#include <iostream>

class ArmTeleop : public rclcpp::Node {
public:
    ArmTeleop() : Node("arm_keyboard_teleop") {
        cli_ = create_client<interfaces::srv::MoveArm>("/car_arm_controller_node/relative_move");
        RCLCPP_INFO(this->get_logger(), "Keyboard Controls:");
        RCLCPP_INFO(this->get_logger(), "  Translation: W/A/S/D (X/Y), Q/E (Z)");
        RCLCPP_INFO(this->get_logger(), "  Rotation:    I/J/K/L (Roll/Pitch), U/O (Yaw)");
        RCLCPP_INFO(this->get_logger(), "  Exit:        X");
        configureTerminal(false);
        spin();
        configureTerminal(true);
    }

private:
    rclcpp::Client<interfaces::srv::MoveArm>::SharedPtr cli_;

    void configureTerminal(bool reset) {
        static struct termios oldt, newt;
        if (!reset) {
            tcgetattr(STDIN_FILENO, &oldt);
            newt = oldt;
            newt.c_lflag &= ~(ICANON | ECHO);
            tcsetattr(STDIN_FILENO, TCSANOW, &newt);
        } else {
            tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
        }
    }

    void spin() {
        while (rclcpp::ok()) {
            char c = getchar();
            if (c == 'x') break;
            auto req = std::make_shared<interfaces::srv::MoveArm::Request>();
            req->command  = std::string(1, c);
            req->blocking = true;

            if (!cli_->wait_for_service(std::chrono::seconds(2))) {
                RCLCPP_ERROR(get_logger(), "Arm Control Service not available. Waiting...");
                continue;
            }
            auto fut = cli_->async_send_request(req);
            RCLCPP_INFO(get_logger(), "Sending command: '%c'", c);
            rclcpp::spin_until_future_complete(get_node_base_interface(), fut);
            auto resp = fut.get();
            if (!resp->success)
                RCLCPP_WARN(get_logger(), "Rejected: %s", resp->message.c_str());
        }
    }
};

int main(int argc,char** argv) {
    rclcpp::init(argc,argv);
    rclcpp::spin(std::make_shared<ArmTeleop>());
    rclcpp::shutdown();
    return 0;
}