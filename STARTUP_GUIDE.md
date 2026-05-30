# 🏥 智慧康养数字病房 - 启动教程

> ⚠️ **请严格按顺序执行，直接复制粘贴每一段命令即可。**

---

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

## 二、每次启动流程

> 如果刚做完上面的编译，可以跳过步骤 1，直接从步骤 2 开始。

### 📺 终端 A：启动 Gazebo 仿真 + Nav2 导航

#### 步骤 1：打开 PowerShell → WSL → Docker

```powershell
wsl -d Ubuntu
```

```bash
cd /mnt/d/飞腾派/plan/2/oh_robot_sim
./ros-demo.sh
```

#### 步骤 2：加载环境并启动

```bash
cd /root/workspace
source /opt/ros/humble/setup.bash
source install/setup.bash
export DISPLAY=:0
ros2 launch demos gzsim.nav2.launch.py
```

> ✅ **成功标志**：Gazebo 3D 窗口弹出（医院病房 + 蓝色病床），RViz2 地图窗口弹出。
>
> ⚠️ **这个终端不要关！**

---

### 📺 终端 B：视觉识别节点

**新开 PowerShell 窗口**：

```powershell
wsl -d Ubuntu
```

```bash
docker exec -it ros2-demo bash
```

```bash
cd /root/workspace
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run demos vision_recognition_node
```

---

### 📺 终端 C：软总线模拟器

**新开 PowerShell 窗口**：

```powershell
wsl -d Ubuntu
```

```bash
docker exec -it ros2-demo bash
```

```bash
cd /root/workspace
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run demos pda_softbus_monitor
```

---

### 📺 终端 D：机器人执行体

**新开 PowerShell 窗口**：

```powershell
wsl -d Ubuntu
```

```bash
docker exec -it ros2-demo bash
```

```bash
cd /root/workspace
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run demos robot_executor
```

---

### 📺 终端 E：任务调度台

**新开 PowerShell 窗口**：

```powershell
wsl -d Ubuntu
```

```bash
docker exec -it ros2-demo bash
```

```bash
cd /root/workspace
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run demos ward_task_server
```

---

## 三、开始演示

当所有终端都启动成功后：

1. 在**终端 E** 中输入 `1` 并回车
2. 观察终端 C 报告：护士 PDA 靠近病床
3. 观察终端 D：机器人收到取药任务，开始自主导航
4. Gazebo 中观察小车移动

---

## 四、常见问题

| 问题                        | 解决办法                                                     |
| --------------------------- | ------------------------------------------------------------ |
| `ros2: command not found`   | 忘了执行 `source /opt/ros/humble/setup.bash`                 |
| `Package 'demos' not found` | 忘了执行 `source install/setup.bash`                         |
| Gazebo 窗口没弹出           | 忘了执行 `export DISPLAY=:0`                                 |
| `docker exec` 报容器不存在  | 终端 A 的容器没启动，先回终端 A 执行 `./ros-demo.sh`         |
| 编译报 `ament_cmake` 找不到 | 忘了执行 `source /opt/ros/humble/setup.bash`                 |
| 编译报 `MUJOCO_LIB` 找不到  | 加上 `--packages-skip mujoco_ros2_control mujoco_ros2_simulation mujoco_ros2_control_demos moveit2c` |

---

## 五、快速记忆口诀

每次进容器后，先念这个"三连"咒语：

```bash
cd /root/workspace
source /opt/ros/humble/setup.bash
source install/setup.bash
```

念完才能跑 `ros2` 命令！
