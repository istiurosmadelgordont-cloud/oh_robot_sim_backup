# 🏆 2026年操作系统设计赛（全国赛）— 参赛信息与完美部署教程

> [!IMPORTANT]
> **评委专家好！**
> 本项目为 **2026年全国操作系统设计赛 - OS功能挑战赛** 参赛作品。我们基于 OpenHarmony 分布式软总线与 ROS 2 仿真架构，设计并实现了一套具备高逼真物理环境与端侧协同交互的**智能病房机器人避障与药送仿真系统**。

## 👥 参赛队伍基本信息

- **选题编号**：proj15
- **项目名称**：智能病房避障与药送仿真系统
- **高校名称**：[广东石油化工学院]
- **队伍 ID**：[T2026116569911339]
- **队伍名称**：[purple_rain]

---

## 📂 核心演示与文档导航

1. **🎬 [功能演示视频（Baidu Netdisk 链接）](https://pan.baidu.com/)**
   * **提取码**：xxxx
   * *[请在此填写您的 10-30 分钟功能演示与成果讲解视频的百度网盘分享链接]*
   * 视频内详细展示了：高逼真 3D 医院场景（包含药架、30 个药品盒、8 张病床及床头屏）、雷达自主定位、高频 Nav2 导航避障与路径规划。
2. **📖 [项目核心技术架构设计说明](#-项目简介--系统架构)**
   * 本项目首创了面向 OpenHarmony (EDU) 生态的具身智能机器人模拟器框架，支持多模态语义解析、跨端分布式低延迟交互及 LeRobot 具身数据采集与训练。

---

# 🚀 完美启动与部署指南（复合机器人+视觉抓取版）

我们为您准备了**极速启动模式**（纯 Docker 运行，完美体验 Gazebo 物理仿真、Nav2 导航避障与机械臂视觉抓取），直接照着下面两步无脑复制即可！

## 一、首次编译（只需执行一次）

### 1. 打开 PowerShell，进入 WSL → Docker 容器

```powershell
wsl -d Ubuntu
```

```bash
cd /mnt/d/飞腾派/plan/2/oh_robot_sim
./ros-demo.sh
```

> 看到 `root@docker-desktop:/#` 就说明进入容器了。

### 2. 编译全部代码

```bash
cd /root/workspace
source /opt/ros/humble/setup.bash
rm -rf build/ install/ log/
colcon build --packages-skip mujoco_ros2_control mujoco_ros2_simulation mujoco_ros2_control_demos moveit2c
```

> ⏳ 大约需要 2~3 分钟。看到 `Summary: XX packages finished` 且 **0 packages failed** 就是成功。

---

## 二、启动演示流程（一键启动，仅需 2 个终端）

> 💡 **重磅升级**：为了方便评委专家演示，我们已将原本繁琐的 5 个终端命令整合为**一键启动**！
> **快速记忆口诀**：每次新开终端进入容器后，先念"三连"咒语加载环境：
> `cd /root/workspace && source /opt/ros/humble/setup.bash && source install/setup.bash`

### 📺 终端 A：一键拉起所有核心节点
这个终端将同时启动 Gazebo 物理世界、Nav2 导航、视觉识别节点、软总线模拟器以及机器人控制大脑！

1. 打开 PowerShell -> `wsl -d Ubuntu`
2. `cd /mnt/d/飞腾派/plan/2/oh_robot_sim && ./ros-demo.sh`
3. 启动全家桶（注意设 DISPLAY 变量）：
   ```bash
   cd /root/workspace
   source /opt/ros/humble/setup.bash
   source install/setup.bash
   export DISPLAY=:0
   ros2 launch demos proj15_all.launch.py
   ```
   *等待几秒，Gazebo 窗口会弹出，随后各个后台节点会自动依次启动就绪。*

### 📺 终端 B：赛事总控调度台（发号施令）
在此终端中模拟护士手持 PDA 靠近病床，触发任务。

1. 新开 PowerShell -> `wsl -d Ubuntu`
2. `docker exec -it ros2-demo bash`
3. 启动调度台：
   ```bash
   cd /root/workspace
   source /opt/ros/humble/setup.bash
   source install/setup.bash
   ros2 run demos ward_task_server
   ```

---

## 🎬 三、见证奇迹时刻

当所有终端都启动成功后：

1. 在 **终端 E (调度台)** 中，按下数字键 `1` 并回车（模拟护士携带 PDA 靠近 1 号病房）。
2. **终端 C (软总线)** 立刻报告发现护士 PDA，完成无感身份验证！
3. **终端 D (机器人大脑)** 接收到取药医嘱，小车在 Gazebo 物理世界中自主规划路径并驶向药房。
4. 到达药房后，背部的 Panda 机械臂自动举起，**终端 B (视觉节点)** 扫描目标二维码。
5. 视觉锁定后，机械臂前探，完成硬核的**物理抓取**动作！
6. 抓取成功后，小车满载荣誉自动驶回护士所在的病床完成交付。

---

# 🏗️ 项目简介 & 系统架构

## 📋 项目简介

Robot Sim 是首个面向 OpenHarmony (EDU) 生态的具身智能机器人模拟器框架，支持自然语言交互、端侧伺服遥控、物理仿真、数据采集及 VLA 模型管理。

核心定位：为 OpenHarmony 开发者提供低成本、高效率的具身智能研发工具，解决现有仿真生态与 OpenHarmony 割裂、端侧协同不足、模型迭代困难等问题。

## ✨ 核心特性

### 1. OpenHarmony 原生适配

*   整合 ROS2 Controllers、Robot State Nodes 等核心组件至 OpenHarmony OS
*   支持 OpenHarmony 端侧设备无缝接入仿真系统
*   基于 OpenHarmony 分布式软总线实现跨设备低延迟通信

### 2. 端侧伺服遥控

*   端侧设备化身「伺服遥控器」，通过触摸、姿态等自然交互操纵仿真机器人
*   LeRobot 数据采集，同步获取相机图像、关节状态等多源数据

### 3. 多模态具身任务支持

*   「自然语言 + Agent + MCP」语义解析链路，实现高层指令快速转化
*   兼容 Gazebo/MuJoCo 双仿真引擎，模拟真实物理环境

### 4. 全流程模型支持

*   对接 LeRobot 训练框架，支持 ACT/pi0 等 VLA 模型训练
*   提供模型推理部署接口，快速验证仿真到真实场景迁移效果

## 🏗️ 系统架构

<img src="media/dataflow.png" width="550px" />

| 层级 | 核心模块 | 功能说明 |
| --- | --- | --- |
| 交互层 | ArkTS 前端、端侧伺服遥控、Agent+MCP | 多模态指令输入、可视化交互、端侧协同控制 |
| 控制层 | ROS2 Controllers、Robot State Nodes | 关节轨迹规划、状态采集发布、控制信号生成 |
| 仿真层 | Gazebo/MuJoCo 仿真节点 | 物理仿真、机器人模型驱动、图像渲染 |
| 数据与模型层 | LeRobot Data Collector、VLA Train\&Inference | 多源数据采集、模型训练、推理部署 |

## 🛠️ 技术栈

| 领域 | 核心技术 / 工具 |
| --- | --- |
| 操作系统 | OpenHarmony 5.1.0, Ubuntu 22.04 |
| 机器人控制 | ROS2 |
| 前端开发 | ArkTS |
| 仿真引擎 | Gazebo、MuJoCo |
| Model 训练 | PyTorch、LeRobot |
| 通信协议 | gRPC、ROS2 DDS、HTTP |

---

## 📄 许可证

本项目基于 Apache License 2.0 开源，详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

感谢 OpenHarmony 社区提供的技术支持与生态保障。
