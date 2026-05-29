## 开发环境：不使用 OpenHarmony 生态

### 1. 主机环境准备

如果您完全不想使用 OpenHarmony 的生态（或者上手 OH 很困难），本项目同样提供开发环境，方便解耦开发，提升社区共建度。

> [!NOTE]
>
> 无 OpenHarmony 生态的开发环境暂不支持 Agent 前端控制（因为前端由 ArkTS 实现）。

您必须准备一台 Ubuntu 宿主机（已测试 22.04）+ docker 环境。docker 安装方法：

```bash
curl -fsSL get.docker.com -o get-docker.sh    # 自动安装脚本
sudo sh get-docker.sh --mirror Aliyun # 国内阿里云，如果你在国外，删除 --mirror参数
```

然后使用本项目提供的镜像。以下 3 中方法任选一个即可：

- 下拉 docker 现成的镜像；
  - Docker Hub：`docker pull voxelsky/ros-humble-desktop-classic:v0.0.1`；
  - 国内阿里云镜像（个人仓库，不保证可用性。有问题提 Issue）：`docker pull crpi-ez0mp20rl5djukrk.cn-shanghai.personal.cr.aliyuncs.com/voxelsky/ros-humble-desktop-classic:v0.0.1`；
- docker 自行构建；直接执行 `docker/build-humble-all.sh` 构建 docker 环境（10 min 左右，您的机器网络需要能访问 `github.com`）；
- 裸机安装宿主机环境：环境布置比较繁琐，有些依赖需要现场源码编译（比如 gRPC 是需要固定版本以匹配 Protobuf，所以不能直接用 `apt/yum` 安装，官方不提供），因此您只能参考 `docker/Dockerfile.ros.humble.classic` 的构建流程自行准备环境。

准备完成后，找一个空目录下拉本仓库：

```bash
git clone https://gitcode.com/openharmony-robot/oh_robot_sim.git
cd oh_robot_sim
```

直接执行仓库根目录下的 `ros-humble.sh` 进入 docker 环境（环境中提供了 ssh server，使用 `root` 用户、密码 `123` 即可另外登入）。

> [!TIP]
>
> `ros-humble.sh` 的逻辑是：设置一些 X11 参数、配置 GUI session 后再进入你之前拉取的 docker 容器。这是为了确保 docker 内的 GUI 程序能够显示到你的机器上。

> [!NOTE]
>
> 宿主机环境提供的 ssh server 默认监听 22 端口，网络共享宿主机网络。如您宿主机 22 端口被占用，请自行调整。

### 2. 项目构建和运行

进入刚刚启动的 docker 容器中（如上面提及的，可以通过 ssh 进去多个终端）解压必要素材：

```bash
cd /root/workspace
# 此脚本仅第一次需要执行
./scripts/download_mujoco.sh
# 此脚本仅第一次或者 git 远程仓库更新后需要执行
./scripts/extract_assets.sh
```

准备 ROS2 环境变量（每次进入终端需要执行）：

```bash
cd /root/workspace
source ~/.bashrc_ros
```

构建本项目：

```bash
colcon build
source install/setup.bash
```

现在环境已经布置完成，您可以执行下面的指令并稍等片刻，检查开发环境是否能正常运作：

```bash
ros2 launch demos gzsim.nav2.launch.py
```
