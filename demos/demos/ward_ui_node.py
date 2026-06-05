#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext

class WardUINode(Node):
    def __init__(self, ui_app):
        super().__init__('ward_ui_node')
        self.ui_app = ui_app
        
        # Publishers
        self.cmd_pub = self.create_publisher(String, '/pda_command', 10)
        self.sign_pub = self.create_publisher(String, '/pda_sign_confirm', 10)
        
        # Subscribers
        self.create_subscription(String, '/softbus_status', self.softbus_callback, 10)
        self.create_subscription(String, '/robot_status', self.robot_status_callback, 10)
        
    def softbus_callback(self, msg):
        self.ui_app.update_bed_screen(msg.data)
        
    def robot_status_callback(self, msg):
        self.ui_app.append_log(msg.data)
        
    def send_command(self, cmd):
        msg = String()
        msg.data = cmd
        self.cmd_pub.publish(msg)
        
    def send_sign_confirm(self):
        msg = String()
        msg.data = "confirm"
        self.sign_pub.publish(msg)

class WardUIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("智慧康养数字病房 - 分布式交互终端")
        self.root.geometry("900x600")
        
        # ROS2 Node will be attached later
        self.ros_node = None
        
        # Main layout
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left Panel (Virtual PDA)
        self.pda_frame = ttk.LabelFrame(self.main_paned, text="📱 虚拟 PDA 端", width=400)
        self.main_paned.add(self.pda_frame, weight=1)
        
        self.setup_pda_ui()
        
        # Right Panel (Bed Screen)
        self.bed_frame = ttk.LabelFrame(self.main_paned, text="📺 虚拟床头屏端", width=400)
        self.main_paned.add(self.bed_frame, weight=1)
        
        self.setup_bed_ui()
        
        # Bottom Panel (Robot Log)
        self.log_frame = ttk.LabelFrame(self.root, text="🤖 智能执行体实时状态日志")
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=8, bg="black", fg="lime", font=("Consolas", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def setup_pda_ui(self):
        # Nurse Info
        info_lbl = ttk.Label(self.pda_frame, text="🧑 护士身份: 张三 (工号: 1001)\n状态: 待命", font=("Arial", 11, "bold"))
        info_lbl.pack(pady=10)
        
        ttk.Separator(self.pda_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(self.pda_frame, text="📍 移动 PDA 至病床 (模拟靠近触发软总线):").pack(pady=5)
        
        btn_frame = ttk.Frame(self.pda_frame)
        btn_frame.pack(fill=tk.X, padx=20)
        
        for i in range(1, 9):
            row = (i - 1) // 2
            col = (i - 1) % 2
            btn = ttk.Button(btn_frame, text=f"前往 {i}号床", command=lambda x=str(i): self.send_cmd(x))
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        
        leave_btn = ttk.Button(self.pda_frame, text="🚶 撤出病房 (>2m) 断开连接", command=lambda: self.send_cmd("0"))
        leave_btn.pack(fill=tk.X, padx=25, pady=10)
        
        ttk.Separator(self.pda_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=5)
        
        # Sign-off Button
        self.sign_btn = tk.Button(self.pda_frame, text="✅ 确认药品签收\n(提交医嘱执行单)", 
                                  bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), 
                                  height=2, command=self.send_sign)
        self.sign_btn.pack(fill=tk.X, padx=25, pady=15)

    def setup_bed_ui(self):
        self.bed_status_lbl = tk.Label(self.bed_frame, text="未连接\n(等待 PDA 靠近以完成无感鉴权)", 
                                       font=("Arial", 14), fg="gray", justify=tk.CENTER)
        self.bed_status_lbl.pack(expand=True)
        
        self.patient_info_frame = ttk.Frame(self.bed_frame)
        # We don't pack it initially since it's unconnected
        
        self.name_lbl = ttk.Label(self.patient_info_frame, text="", font=("Arial", 18, "bold"), foreground="blue")
        self.name_lbl.pack(pady=10)
        
        self.order_lbl = ttk.Label(self.patient_info_frame, text="", font=("Arial", 12))
        self.order_lbl.pack(pady=5)
        
        self.status_tag = tk.Label(self.patient_info_frame, text="医嘱执行中...", bg="orange", fg="white", font=("Arial", 12, "bold"))
        self.status_tag.pack(pady=20, ipadx=10, ipady=5)

    def update_bed_screen(self, status):
        # Update UI in main thread
        self.root.after(0, self._update_bed_screen_ui, status)
        
    def _update_bed_screen_ui(self, status):
        if status == 'disconnected':
            self.patient_info_frame.pack_forget()
            self.bed_status_lbl.config(text="未连接\n(等待 PDA 靠近以完成无感鉴权)", fg="gray")
            self.bed_status_lbl.pack(expand=True)
            self.status_tag.config(text="医嘱执行中...", bg="orange")
        elif status.startswith('connected:'):
            bed_id = status.split(':')[1]
            self.bed_status_lbl.pack_forget()
            
            # Simulated db lookup
            patient = "张三 (男, 35岁)" if "W1_1" in bed_id else "李四 (男, 42岁)"
            medicine = "阿司匹林肠溶片 100mg" if "W1_1" in bed_id else "布洛芬缓释胶囊 300mg"
            
            self.name_lbl.config(text=f"病患: {patient} | {bed_id}")
            self.order_lbl.config(text=f"所需药品: {medicine}")
            
            self.patient_info_frame.pack(expand=True, fill=tk.BOTH, padx=20)

    def append_log(self, text):
        self.root.after(0, self._append_log_ui, text)
        
    def _append_log_ui(self, text):
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        
        if "签收成功" in text:
            self.status_tag.config(text="✅ 医嘱执行成功，记录已保存", bg="green")

    def send_cmd(self, cmd):
        if self.ros_node:
            self.ros_node.send_command(cmd)
            self.append_log(f"\n>> 模拟移动 PDA 至指令点 [{cmd}] ...")
            
    def send_sign(self):
        if self.ros_node:
            self.ros_node.send_sign_confirm()
            self.append_log("\n>> [PDA] 护士已点击【确认签收】按钮，提交签收单。")

def ros_spin_thread(node):
    rclpy.spin(node)

def main(args=None):
    rclpy.init(args=args)
    
    root = tk.Tk()
    
    # Configure styling
    style = ttk.Style()
    style.theme_use('clam')
    
    app = WardUIApp(root)
    node = WardUINode(app)
    app.ros_node = node
    
    # Start ROS spinning in a separate thread
    spin_thread = threading.Thread(target=ros_spin_thread, args=(node,), daemon=True)
    spin_thread.start()
    
    # Start Tkinter main loop
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
