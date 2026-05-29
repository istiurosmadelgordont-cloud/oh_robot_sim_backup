#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <termios.h>
#include <unistd.h>
#include <map>

class KeyboardControl : public rclcpp::Node {
public:
    KeyboardControl() : Node("keyboard_control") {
        pub_ = this->create_publisher<geometry_msgs::msg::Twist>("/arm_relative_move", 10);
        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(100),
            std::bind(&KeyboardControl::timer_callback, this));
        
        tcgetattr(STDIN_FILENO, &orig_termios_);
        struct termios new_termios = orig_termios_;
        new_termios.c_lflag &= ~(ICANON | ECHO);
        tcsetattr(STDIN_FILENO, TCSANOW, &new_termios);
        
        RCLCPP_INFO(this->get_logger(), "Keyboard Controls:");
        RCLCPP_INFO(this->get_logger(), "  Translation: W/A/S/D (X/Y), Q/E (Z)");
        RCLCPP_INFO(this->get_logger(), "  Rotation:    I/J/K/L (Roll/Pitch), U/O (Yaw)");
        RCLCPP_INFO(this->get_logger(), "  Exit:        X");
    }
    
    ~KeyboardControl() {
        tcsetattr(STDIN_FILENO, TCSANOW, &orig_termios_);
    }

private:
    void timer_callback() {
        char c;
        if (read(STDIN_FILENO, &c, 1) < 0) return;
        
        auto twist = std::make_unique<geometry_msgs::msg::Twist>();
        const double step = 0.1;  // 10cm移动步长
        const double angle_step = 0.05; // 0.05弧度旋转步长
        
        // 键盘映射
        std::map<char, std::function<void()>> keymap = {
            {'w', [&](){ twist->linear.x = step; }},   // +X
            {'s', [&](){ twist->linear.x = -step; }},  // -X
            {'a', [&](){ twist->linear.y = step; }},   // +Y
            {'d', [&](){ twist->linear.y = -step; }},  // -Y
            {'q', [&](){ twist->linear.z = step; }},   // +Z
            {'e', [&](){ twist->linear.z = -step; }},  // -Z
            {'i', [&](){ twist->angular.x = angle_step; }},    // +Roll
            {'k', [&](){ twist->angular.x = -angle_step; }},   // -Roll
            {'j', [&](){ twist->angular.y = angle_step; }},    // +Pitch
            {'l', [&](){ twist->angular.y = -angle_step; }},   // -Pitch
            {'u', [&](){ twist->angular.z = angle_step; }},    // +Yaw
            {'o', [&](){ twist->angular.z = -angle_step; }}    // -Yaw
        };
        
        if (keymap.count(c)) {
            keymap[c]();
            RCLCPP_INFO(this->get_logger(), "Key: %c", c);
            pub_->publish(std::move(twist));
        }
        else if (c == 'x') {
            RCLCPP_INFO(this->get_logger(), "Exiting...");
            rclcpp::shutdown();
        }
        else {
            RCLCPP_WARN(this->get_logger(), "Unknown key: %c", c);
        }
    }
    
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;
    struct termios orig_termios_;
};

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<KeyboardControl>());
    rclcpp::shutdown();
    return 0;
}