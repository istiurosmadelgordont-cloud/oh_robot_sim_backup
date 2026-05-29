## Demo 快速开始

如果您不需要编译开发环境，则可以使用懒人包立即运行本项目的 Navigation2 Demo 来查看效果。

您需要下面几步来配置基本运行环境：

### 宿主机环境

1. 在你的机器上准备 Docker 环境。由于 ROS2 本身对 Windows 生态不友好，使用 docker 会更方便一些。

   ```shell
   # Linux 安装方法
   curl -fsSL get.docker.com -o get-docker.sh    # 自动安装脚本
   sudo sh get-docker.sh --mirror Aliyun # 国内阿里云，如果你在国外，删除 --mirror参数
   
   # Windows 请搜索 Docker Desktop + WSL2 下载。可能有用的教程：
   # 1. https://zhuanlan.zhihu.com/p/1900601739113137024
   # 2. https://learn.microsoft.com/zh-cn/windows/wsl/tutorials/wsl-containers
   # 3. 官方文档：https://docs.docker.com/desktop/setup/install/windows-install/
   ```

2. 下载提供给你机器运行的 docker 镜像：

   ```shell
   docker pull voxelsky/ohos-rsim-nav2-demo:v0.0.1
   # 如果无法访问 docker hub，这里提供国内镜像（个人镜像仓，不保证可用性，有问题提 issue）：
   docker pull crpi-ez0mp20rl5djukrk.cn-shanghai.personal.cr.aliyuncs.com/voxelsky/ohos-rsim-nav2-demo:v0.0.1
   ```

3. 宿主机节点启动：

   - 下载仓库，并将命令行切换到当前仓库根目录：

     ```shell
     git clone https://gitcode.com/openharmony-robot/oh_robot_sim.git
     cd oh_robot_sim
     ```

   - 执行命令启动：

     ```shell
     # 进入 docker 环境
     # 内置了 ssh server，以后您可以通过 ssh root@localhost (密码 123) 来连接到容器内部。
     ./ros-demo.sh
     cd /root/oh_robot_sim
     source ~/.bashrc_ros
     source install/setup.bash
     export ROS_DOMAIN_ID=0
     export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
     ros2 launch demos simhost.nav2.launch.py
     ```

### OH EDU 环境

1. 下载 OH EDU 镜像（不需要开发板）以及编译打包好的项目，解压到空目录：

   ```shell
   # 百度网盘
   链接: https://pan.baidu.com/s/13PiVTqBQH4bdR3-O2hrogQ?pwd=w1mm
   提取码: w1mm
   # 交大网盘
   文件名: ohedu-robosim-nav2demo.tar.gz
   链接: https://pan.sjtu.edu.cn/web/share/18fc81b2538b2de546af96f6b35bee68
   提取码: agjb
   ```

2. 进入该目录，安装依赖：

   - Ubuntu Linux 执行：`./install_requests.sh`；

3. 启动节点：

   ```shell
   sudo ./qemu_run_client.sh |& tee kernel.log
   ```

4. 在 `kernel.log` 中找到 `my address is` 字符串所在行，获得 OH EDU 的 IP 地址：

   ```bash
   # Linux
   grep "my address is" kernel.log
   ```

   或者直接翻命令行的输出找到 IP 地址。

5. HDC 连接并启动另一部分节点：

   ```shell
   hdc tconn <IP地址>:55555
   hdc shell
   cd /data/
   source ros2ohos.env
   set +e
   cd ors
   source install/setup.sh
   export ROS_DOMAIN_ID=0
   ros2 launch demos simoh.nav2.launch.py
   ```

   现在节点全部准备完毕。您可以在 docker 容器中打开 `rviz2` 来查看节点全部正常：

   ```shell
   # 密码 123
   ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -p22 root@127.0.0.1
   source ~/.bashrc_ros
   rviz2 -d /opt/ros/humble/share/nav2_bringup/rviz/nav2_default_view.rviz
   # 现在你可以使用 rviz 界面来控制机器人导航
   ```

   > [!TIP]
   >
   > 如果qemu和docker的ros通信出现问题，可能是由于ros2的通信选择了错误的网段。可以通过以下方法修复：
   1. docker端
   
      在docker中创建文件 `/root/cyclonedds.xml`，内容如下：
      ```xml
      <?xml version="1.0" encoding="UTF-8" ?>
      <CycloneDDS xmlns="https://cdds.io/config" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://cdds.io/config https://raw.> thubusercontent.com/eclipse-cyclonedds/cyclonedds/master/etc/cyclonedds.xsd">
      <Domain id="any">
         <General>
            <!-- 这里填入 Docker 和 QEMU 相连的那个虚机网卡接口的 IP -->
            <NetworkInterfaceAddress>192.168.122.1</NetworkInterfaceAddress>
            <AllowMulticast>true</AllowMulticast>
         </General>
      </Domain>
      </CycloneDDS>
      ```
      
      在docker运行ros命令之前，设置：`export CYCLONEDDS_URI=file:///root/cyclonedds.xml`，之后在同一终端启动ros

   2. qemu端

      创建文件 `/root/cyclonedds.xml`，内容如下
      ```xml
      <?xml version="1.0" encoding="UTF-8" ?>
         <CycloneDDS xmlns="https://cdds.io/config" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
         <Domain id="any">
            <General>
               <!-- 这里填入 QEMU 自己的 IP -->
               <NetworkInterfaceAddress>192.168.122.111</NetworkInterfaceAddress>
               <AllowMulticast>true</AllowMulticast>
            </General>
         </Domain>
      </CycloneDDS>
      ```
      设置`export CYCLONEDDS_URI=file:///root/cyclonedds.xml`，并在相同终端启动ros

## 配置AI Agent（可选）

### docker端

编辑项目根目录下的 `oh_agent/oh_agent/configurations/config.py`，填写你自己的 API Key 或者模型提供商。

   > [!TIP]
   >
   > 你需要进入docker容器内编辑config.py。qemu的ip地址可以通过在hdc shell中运行`ifconfig`查看

   修改后，新开一个窗口进入容器执行：

   ```shell
   # 密码 123
   ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -p22 root@127.0.0.1
   mamba activate oh_agent
   cd /root/oh_robot_sim/oh_agent
   export ROBOT_GRPC_HOST=<qemu的IP地址>
   python oh_agent/main.py
   ```

### qemu端

打开OH EDU界面的simc-demo应用，点击右上角设置，输入 IP 为docker的 IP 地址（该IP和qemu在相同网段）。IP 地址查看方式如下：

   ```shell
   # Linux
   ifconfig
   # Windows
   ipconfig
   ```

现在可以和 Agent 交流进行导航了。