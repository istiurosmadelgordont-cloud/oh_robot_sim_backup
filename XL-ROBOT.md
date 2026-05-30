# 真实本体：对接曦胧机器人文档

以 Ubuntu 宿主机为例，clone 本项目后，请准备好 ROS2 环境，执行下面的脚本下载基本素材（仅第一次下载本仓需要执行）：

```bash
./scripts/download_mujoco.sh
./scripts/extract_assets.sh
```

编译项目：

```bash
colcon build
```

> 要为 OpenHarmony 设备编译，请参见文档教程：[Docs/docker-build](https://gitcode.com/openharmony-robot/docs/blob/main/device-dev/docker-build.md)；
>
> 如果您只需要跑在 Ubuntu 宿主机上，则不需要阅读上述教程。

## 0. 曦胧底盘网络配置

将底盘网络置于您可以访问到的局域网下。本仓库的默认值是 `http://192.168.6.8`。您需要按照您的实际情况在 `drivers/xl_chassis/xl_chassis/chassis.py` 配置您的曦胧底盘所在的 IPv4 地址。



## 1. 曦胧底盘基本接口

执行：

```bash
source install/setup.bash
ros2 launch xl_chassis chassis_nomap.launch.py
```

启动包含 `/odom`（底盘里程计）、`/scan`（雷达数据）、`/cmd_vel`（底盘控制）的话题，可以自由使用这些话题来达成目的。

## 2. 曦胧底盘自主探索 SLAM 建图（无需人工干预建图）

默认此时底盘、ROS2 节点均未建图，我们需要做以下操作：

1. 启动曦胧机器人底盘、主体飞腾开发板；

2. 开一个与机器人同一局域网下的终端窗口（已经准备好了 ROS2 环境），启动 ROS2 基本接口节点：

   ```bash
   ros2 launch xl_chassis chassis_nomap.launch.py
   ```

3. 再开一个与上一步环境相同的终端窗口，启动自主探索算法节点：

   ```bash
   ros2 launch xl_chassis explore.nav2.launch.py
   ```

4. （可选）再开一个相同环境的终端，启动 rviz2 来监控自主探索的情况和进度：

   ```bash
   # 需要有显示器的桌面环境
   # 下面的 rviz 文件路径前缀需要换成你所在环境安装 ROS2 的目录
   rviz2 -d /opt/ros/humble/share/nav2_bringup/rviz/nav2_default_view.rviz
   ```

自主建图完毕后，保存地图到文件（或者直接使用 SLAM 的在线地图）：

```bash
# map_name 不需要包含后缀名
ros2 run nav2_map_server map_saver_cli -f <map_name>
```



## 3. 对接曦胧底盘 ROS2 Navigation2 导航接口

默认此时底盘、ROS2 节点均建好图，并且获得地图文件。启动这个节点即可开始导航：

```bash
ros2 launch xl_chassis chassis.launch.py map:=<map_yaml_file_path>
```

注意还需要向 `/initpose` 发布机器人初始位置。这个位置管理逻辑应该有您来具体完成。我们提供一个示例，它会在启动后向 `/initpose` 发布 `(0,0,0)`（x、y、yaw）：

```bash
ros2 launch xl_chassis simoh.nav2.launch.py
```



