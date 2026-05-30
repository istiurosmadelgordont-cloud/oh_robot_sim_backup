# 🏥 智慧病房仿真系统 — 完美启动与部署教程

由于 OpenHarmony 端的 `hdc` 工具和虚拟机连接配置较为繁琐，本教程将启动方式分为**两种模式**：

1. **🌟【极速推荐模式】纯 Docker 运行 Nav2 导航（无需 QEMU，无需 hdc，100% 马上可用）**：直接在 Docker 宿主机内跑完整的 Gazebo + Nav2 + RViz2 导航，可立即测试机器人的定位与路径规划。
2. **🛡️【分布式联调模式】宿主机 Docker + OpenHarmony QEMU 联调（后续调试软总线时使用）**：通过虚拟局域网和 hdc 连接进行双机协同。

---

## 🧹 第 0 步：关掉所有残留进程（环境清理）

在新开仿真前，请在您的 **PowerShell** 窗口中直接运行此命令，一键清除残留占用：

```powershell
wsl -d Ubuntu -e bash -c "sudo pkill -9 qemu 2>/dev/null; docker stop ros2-demo 2>/dev/null; echo '✅ 已清理'"
```

---

# 🌟 方案一：【极速推荐模式】纯 Docker 运行（只需 2 个终端，即刻测试导航）

此方案无需开启 OpenHarmony QEMU 虚拟机，无需安装 `hdc`。直接在 Docker 容器内拉起物理仿真、地图、导航算法与可视化窗口，非常适合用于机器人导航、避障以及算法的快速迭代。

### 📺 终端 A：拉起 Gazebo 物理仿真

1. 新开一个 **PowerShell** 窗口，输入并回车以进入 WSL：
   ```powershell
   wsl -d Ubuntu
   ```

2. 进入代码目录并进入 Docker 容器：
   ```bash
   cd /mnt/d/飞腾派/plan/2/oh_robot_sim
   ./ros-demo.sh
   ```

3. 进入 Docker 终端（看到 `root@docker-desktop:/#` 提示符）后，**复制并运行以下整段命令**：
   ```bash
   cd /root/oh_robot_sim
   source ~/.bashrc_ros 2>/dev/null
   source install/setup.bash
   export ROS_DOMAIN_ID=0
   export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
   
   # 1. 部署世界文件和地图到运行路径（确保加载最新医院病床与药架）
   cp /root/workspace/assets/worlds/sdf/hospital_ward.classic.world \
      /root/oh_robot_sim/install/asset_worlds/share/asset_worlds/sdf/
   cp /root/workspace/assets/maps/slam2d/hospital_ward.pgm \
      /root/oh_robot_sim/install/asset_maps/share/asset_maps/slam2d/
   cp /root/workspace/assets/maps/slam2d/hospital_ward.yaml \
      /root/oh_robot_sim/install/asset_maps/share/asset_maps/slam2d/
   cp /root/workspace/demos/launch/simhost.nav2.launch.py \
      /root/oh_robot_sim/install/demos/share/demos/launch/
   
   echo "✅ 医院场景文件部署成功！"
   
   # 2. 启动仿真三维世界（会自动打开一个含有病房、药架和药品盒的 Gazebo 窗口）
   export DISPLAY=:0
   ros2 launch demos simhost.nav2.launch.py
   ```

---

### 📺 终端 B：拉起 Nav2 导航算法 + RViz2 可视化界面

当终端 A 的 Gazebo 物理窗口成功弹出并完全载入后，执行本步骤：

1. **新开一个** **PowerShell** 窗口，输入并回车进入 WSL：
   ```powershell
   wsl -d Ubuntu
   ```

2. 进入正在运行的 Docker 容器：
   ```bash
   docker exec -it ros2-demo bash
   ```

3. **复制并粘贴以下整段命令**，直接在 Docker 内拉起 Nav2 导航堆和 RViz2 监控：
   ```bash
   source /opt/ros/humble/setup.bash
   source /root/oh_robot_sim/install/setup.bash
   export ROS_DOMAIN_ID=0
   export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
   export DISPLAY=:0
   
   # 1. 启动 Nav2 导航控制节点并载入医院病房地图
   ros2 launch nav2_bringup bringup_launch.py \
     map:=/root/oh_robot_sim/install/asset_maps/share/asset_maps/slam2d/hospital_ward.yaml \
     use_sim_time:=true &
   
   # 2. 等待 10 秒后启动 RViz2 导航显示监视器
   sleep 10
   rviz2 -d /opt/ros/humble/share/nav2_bringup/rviz/nav2_default_view.rviz &
   ```

> 🎉 **测试成功标志**：RViz2 窗口弹出，展示医院二维激光栅格地图。您可以在 RViz2 顶部点击 **"2D Pose Estimate"** 标定机器人的初始位置，然后点击 **"Nav2 Goal"** 给机器人发送导航目的地，观察机器人在三维 Gazebo 中平稳避障驶向目标点！

---

# 🛡️ 方案二：【分布式联调模式】宿主 Docker + QEMU 虚拟机（后续调试软总线时使用）

当您在 Windows 上安装好 OpenHarmony SDK 拥有 `hdc` 工具后，或者需要联调 **“PDA 与床头屏通信/接收签收数据”** 等分布式场景时，使用本方案。

### 📺 终端 1：启动 QEMU 模拟器 (OpenHarmony)
1. 新开 **PowerShell** -> `wsl -d Ubuntu`
2. 运行：
   ```bash
   cd /mnt/d/飞腾派/plan/2/ohedu-robosim-nav2demo
   sudo service libvirtd start
   sudo virsh net-start default 2>/dev/null
   sudo ./qemu_run_client.sh
   ```
   *等待 QEMU 窗口完全出现（OH 虚拟机 IP 通常为 `192.168.122.111`）。*

### 🐳 终端 2：启动 Docker 宿主仿真后端
1. 新开 **PowerShell** -> `wsl -d Ubuntu` -> 进入目录进入 Docker 容器：
   ```bash
   cd /mnt/d/飞腾派/plan/2/oh_robot_sim && ./ros-demo.sh
   ```
2. 在 Docker 中粘贴并运行以下配置通信并启动仿真：
   ```bash
   cd /root/oh_robot_sim
   source ~/.bashrc_ros 2>/dev/null
   source install/setup.bash
   export ROS_DOMAIN_ID=0
   export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
   
   # 配置 CycloneDDS 多机联调地址
   cat > /root/cyclonedds.xml << 'EOF'
   <?xml version="1.0" encoding="UTF-8" ?>
   <CycloneDDS xmlns="https://cdds.io/config">
     <Domain id="any">
       <Discovery>
         <Peers><Peer address="192.168.122.111"/></Peers>
       </Discovery>
     </Domain>
   </CycloneDDS>
   EOF
   export CYCLONEDDS_URI=file:///root/cyclonedds.xml
   
   # 部署场景文件
   cp /root/workspace/assets/worlds/sdf/hospital_ward.classic.world /root/oh_robot_sim/install/asset_worlds/share/asset_worlds/sdf/
   cp /root/workspace/assets/maps/slam2d/hospital_ward.pgm /root/oh_robot_sim/install/asset_maps/share/asset_maps/slam2d/
   cp /root/workspace/assets/maps/slam2d/hospital_ward.yaml /root/oh_robot_sim/install/asset_maps/share/asset_maps/slam2d/
   cp /root/workspace/demos/launch/simhost.nav2.launch.py /root/oh_robot_sim/install/demos/share/demos/launch/
   
   # 启动
   export DISPLAY=:0
   ros2 launch demos simhost.nav2.launch.py
   ```

### 📱 终端 3：HDC 连接并启动 OpenHarmony 导航端（原终端 C）
*(注意：需要确保您的运行环境已成功安装 hdc 工具。若未安装，请使用上面的方案一)*
1. 新开 **PowerShell** -> `wsl -d Ubuntu`
2. 运行 hdc 连接：
   ```bash
   cd /mnt/d/飞腾派/plan/2/ohedu-robosim-nav2demo
   hdc tconn 192.168.122.111:55555
   hdc shell
   ```
3. 在连接成功的 QEMU Shell 终端中运行：
   ```bash
   cd /data/
   source ros2ohos.env
   set +e
   cd ors
   source install/setup.sh
   export ROS_DOMAIN_ID=0
   ros2 launch demos simoh.nav2.launch.py map:=hospital_ward.yaml
   ```
