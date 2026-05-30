#pragma once

#include <cstring>

namespace robot_sim {

class ServiceManager {
public:
    ServiceManager(const std::string &grpc_addr): grpc_server_addr(grpc_addr) {}
    ~ServiceManager() {}

    /** @brief sync (blocking) starting */
    virtual int start(int argc, char** argv) = 0;

protected:
    std::string grpc_server_addr;
};

}   // namespace robot_sim
