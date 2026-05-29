## Demo 开发环境

首先因为涉及 OH 设备和宿主机两套开发环境，因此环境准备可能有些复杂。我们理清一下：

docker 有两个环境，一个是跑宿主机上的 ROS2 节点的（即 “环境准备：宿主机（开发环境）”），另一个是用来交叉编译到 oh 上的（即 “环境准备：OpenHarmony SDK/设备”）。

现在我们想让一部分节点跑在宿主机上，另一部分计算节点跑在 OH 上，就需要分别为宿主机、OH 编译这个项目（编译两次）。

- 宿主机开发环境的 docker（参见 “[环境准备：宿主机](#环境准备：宿主机（开发环境）)”）可以用来编译宿主机上的节点，编完就直接可以启动了；
- 交叉编译给 OH 的 docker 环境（参见 “[环境准备：OpenHarmony SDK/设备](#环境准备：OpenHarmony SDK/设备)”）在用 build-ros-humble 编完后还需要传到板子上使用。

### 环境准备：宿主机（开发环境）

> [!TIP]
>
> 注意这里提供 docker 环境只是为了防止打乱您自己宿主机器的环境。

提供了 3 种方法准备宿主机的环境：

- docker 现成的镜像；
  - Docker Hub：`docker pull voxelsky/ros-humble-desktop-classic:v0.0.2`；
  - 国内阿里云镜像（个人仓库，不保证可用性。有问题提 Issue）：`docker pull crpi-ez0mp20rl5djukrk.cn-shanghai.personal.cr.aliyuncs.com/voxelsky/ros-humble-desktop-classic:v0.0.2`；
- docker 自行构建；直接执行 `docker/build-humble-all.sh` 构建 docker 环境（10 min 左右，您的机器网络需要能访问 `github.com`）；
- 裸机安装宿主机环境：环境布置比较繁琐，有些依赖需要现场源码编译（比如 gRPC 是需要固定版本以匹配 Protobuf，所以不能直接用 `apt/yum` 安装，官方不提供），因此您只能参考 `docker/Dockerfile.ros.humble.classic` 的构建流程自行准备环境。

准备完成后，找个空目录下拉本仓库：

```bash
git clone https://gitcode.com/openharmony-robot/oh_robot_sim.git
cd oh_robot_sim
```

直接执行仓库根目录下的 `ros-humble.sh` 进入环境（环境中提供了 ssh server，使用 `root` 用户、密码 `123` 即可另外登入）。

> [!TIP]
>
> 宿主机环境提供的 ssh server 默认监听 22 端口，网络共享宿主机网络。如您宿主机 22 端口被占用，请自行调整。

### 环境准备：OpenHarmony SDK/设备

关于上面的开发环境准备工作（系统依赖、SDK、ROS2 环境），请参见文档教程：[ROS2 Humble 发行版二进制在 OpenHarmony 上的使用方法](https://gitcode.com/openharmony-robot/docs/blob/main/device-dev/usage.md)。



### 启动

以 Agent + MCP 驱动 Navigation2 为例，

按照 “环境准备” 的文档编译上传后，注意 OH 设备要和主机在一个局域网下，设置（`export`）相同的环境变量 `ROS_DOMAIN_ID`，设置允许多播。

#### 第一步：宿主机上的节点

主机需要先进入开发环境，参见 “[环境准备：宿主机](#环境准备：宿主机（开发环境）)”。然后将命令行切换到当前项目仓库的根目录下。

如果您在“环境准备：宿主机”一节使用的是 docker 环境，则进入容器后执行：

```bash
cd /root/workspace
source ~/.bashrc_ros
```

然后在宿主机开发环境中编译本项目：

```bash
colcon build
source install/setup.bash
```

宿主机启动配套虚拟环境、gRPC services：

```bash
ros2 launch demos simhost.nav2.launch.py
```

（可选）在另一个 Python 虚拟环境中安装 `oh_agent/oh_agent/requirements.txt` 或 `environment.yaml` 指定的包，启动 Agent MCP server：

```bash
cd oh_agent/oh_agent
PYTHONPATH=. python main.py
```

> [!TIP]
>
> 关于大模型的配置和 MCP server 监听的 gRPC services 端口，请前往 `oh_agent/oh_agent/configurations/config.py` 中更改。

#### 第二步：OH 设备上的节点

然后我们需要启动 OH 设备环境。按照上面 “[环境准备：OpenHarmony SDK/设备](#环境准备：OpenHarmony SDK/设备)” 准备完毕后，您应该能在 OH 中执行下面的指令：

```shell
ros2 topic list
```

由于 OpenHarmony 不支持原生执行 `colcon build`（因为没有原生编译工具链），因此对于当前 ROS2 项目同样需要交叉编译到 OH 平台。交叉编译本 ROS2 项目的方法请参见 [用户自定义 ROS2 包/项目编译和使用](https://gitcode.com/openharmony-robot/docs/blob/main/device-dev/docker-build.md#%E7%94%A8%E6%88%B7%E8%87%AA%E5%AE%9A%E4%B9%89-ros2-%E5%8C%85%E9%A1%B9%E7%9B%AE%E7%BC%96%E8%AF%91%E5%92%8C%E4%BD%BF%E7%94%A8)。



按上述教程执行完本项目的 `source install/setup.sh` 后，再启动 OH 上的 ROS2 相关节点：

```shell
ros2 launch demos simoh.nav2.launch.py
```

到此为止，模拟器框架后端环境布置完成。您可以在宿主机环境上启动 rviz2 实时检查导航情况：

```shell
rviz2 -d /opt/ros/humble/share/nav2_bringup/rviz/nav2_default_view.rviz
```



（可选）最后，我们启动模拟器前端。进入 `oh-robot-sim-ui` ArkTS 项目，编译启动项目到 OpenHarmony 设备上，在 Chat 界面中的设置与主机连接（配置使用上面 OH Agent 监听的地址），即可向 Agent 发送指令驱动环境中的机器人。
