import sys
import signal
import threading
import time
import multiprocessing
from flask import Flask, request, jsonify
from datetime import datetime
import uuid

from common import prompts, config
from py_agent.robot_agent import RobotAgent

from typing import Dict, List

from servers.utils import run_isolated_shell


app = Flask(__name__)

_agent = RobotAgent(config.llm, config.server_params, prompts.SYSTEM_PROMPT)
_agent.start()

_demo_messages: Dict[str, List[Dict]] = {}

# 全局事件，用于通知所有监控线程退出
shutdown_event = threading.Event()
sproc: List[multiprocessing.Process] = []


def handle_sigint(signum, frame):
    if shutdown_event.is_set():
        print("waitting for termination...")
        return
    print("\nSIGINT received. Terminating sub-processes...")
    
    shutdown_event.set()
    
    global sproc
    for p in sproc:
        if p.is_alive():
            print(f"terminating {p.pid}...")
            p.terminate()
            p.join(timeout=3)
            if p.is_alive():
                p.kill()
                print(f"killed {p.pid}")
    sproc.clear()
    _agent.stop()
    sys.exit(0)


def main_worker(msg: str, id: str):
    global _agent
    # if msg.find("小车") == -1 and msg.find("car") == -1:
    #     stdout, stderr, ret = run_isolated_shell("ros2 launch servo2c mtc_run.launch.py")
    #     print("stdout:", stdout)
    #     print("stderr:", stderr)
    #     print("return:", ret)
    #     _demo_messages[id] = [{"message": "finish!", "timestamp": datetime.now().isoformat()}]
    # else:
    #     # car agent
    #     _agent.submit_message(prompts.MSG + msg)
    _agent.submit_message(prompts.MSG + msg)


def monitor_process(process: multiprocessing.Process, timeout_seconds=30):
    """监控进程，支持被外部事件中断"""
    try:
        # 等待进程结束，或被shutdown_event中断（超时取较小值）
        # 循环检查，避免join无限阻塞
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            if not process.is_alive():
                break  # 进程已正常结束
            if shutdown_event.is_set():
                print(f"Shutting down process {process.pid}")
                process.terminate()
                process.join(2)
                if process.is_alive():
                    process.kill()
                break
            time.sleep(0.5)  # 短轮询，平衡响应速度和资源消耗
        
        # 超时处理
        if process.is_alive() and not shutdown_event.is_set():
            print(f"Process {process.pid} timeout, trying to terminate...")
            process.terminate()
            process.join(5)
            if process.is_alive():
                print(f"Process {process.pid} still alive, force killing...")
                process.kill()
    except Exception as e:
        print(f"monitor thread error: {e}")
    finally:
        if process in sproc:
            sproc.remove(process)
        print(f"monitor thread exited (process {process.pid})")


# def monitor_process(process: multiprocessing.Process, timeout_seconds=30):
#     process.join(timeout_seconds)
#     if process.is_alive():
#         print(f"Process {process.pid} timeout, trying to terminate...")
#         process.terminate()
#         process.join(2)
#         if process.is_alive():
#             print(f"Process {process.pid} still alive, force killing...")
#             process.kill()
#     if process in sproc:
#         sproc.remove(process)


@app.route('/api/demo', methods=['POST'])
def handle_demo():
    data = request.json
    
    # 验证必需字段
    if not data or 'message' not in data:
        return jsonify({"error": "Missing 'message' field"}), 400
    
    # 生成唯一ID
    message_id = str(uuid.uuid4())
    
    # 存储消息
    _demo_messages[message_id] = [{"message": "Received: " + data['message'], "timestamp": datetime.now().isoformat()}]
    
    # p = multiprocessing.Process(target=main_worker, args=(data["message"], message_id))
    # sproc.append(p)
    # p.start()
    main_worker(data["message"], message_id)

    # monitor_thread = threading.Thread(target=monitor_process, args=(p, 120), daemon=False)
    # monitor_thread.start()
    # _agent.submit_message(prompts.MSG + data["message"])

    # 返回确认
    return jsonify({
        "id": message_id,
        "message": f"Message received and stored with ID: {message_id}"
    }), 200

@app.route('/api/msgs', methods=['GET'])
def get_messages():
    message_id = request.args.get('id')
    
    if not message_id:
        return jsonify({"error": "Missing 'id' parameter"}), 400
    
    if message_id not in _demo_messages:
        return jsonify({"error": "Message ID not found"}), 404
    
    return jsonify(_demo_messages[message_id]), 200


# @app.route('/api/delivery/notification', methods=['POST'])
# def handle_notification():
#     # 获取 JSON 数据
#     data = request.json

#     # 验证必需字段
#     required_fields = ['platform', 'location', 'phone', 'image_url', 'timestamp', 'original_sms']
#     if not all(field in data for field in required_fields):
#         return jsonify({"error": f"Missing required fields: {','.join(required_fields)}"}), 400

#     try:
#         # 打印接收到的数据（实际使用时可以替换为数据库存储或其他处理）
#         print("\n" + "=" * 50)
#         print(f"[{datetime.now().isoformat()}] 收到外卖通知:")
#         print(f"平台: {data['platform']}")
#         print(f"位置: {data['location']}")
#         print(f"电话: {data['phone']}")
#         print(f"图片URL: {data['image_url']}")
#         print(f"时间戳: {data['timestamp']}")
#         print(f"原始短信: {data['original_sms']}")
#         print("=" * 50)

#         # 这里可以添加其他处理逻辑，如：
#         # 1. 保存到数据库
#         # 2. 发送给其他服务
#         # 3. 触发通知等

#         _agent.submit_message(prompts.MSG + data['original_sms'])

#         return jsonify({
#             "status": "success",
#             "message": "Notification processed. Thank you kiwi agent :)",
#             # "received_data": data
#         }), 200

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


def main():
    signal.signal(signal.SIGINT, handle_sigint)
    app.run(host='0.0.0.0', port=8000, debug=True)


if __name__ == '__main__':
    main()
