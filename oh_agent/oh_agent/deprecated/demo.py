import time
import signal
import subprocess
import multiprocessing
from servers.utils import start_isolated_shell, run_isolated_shell

base_process: multiprocessing.Process | None = None # 全局变量存储子进程引用，供信号处理函数使用
base_proc: subprocess.Popen | None = None  # 存储子进程内部启动的Popen对象


def log_base_proc():
    base_proc: subprocess.Popen = start_isolated_shell("ros2 launch servo2c mtc_stub_start.launch.py")
    stdout, stderr = base_proc.communicate()
    print("stderr:", stderr)
    print("stdout:", stdout)
    print("return:", base_proc.returncode)


def handle_sigint(signum, frame):
    print("\nSIGINT received. Terminating sub-processes...")
    
    # 1. 终止子进程内部启动的Popen进程（如果存在）
    if base_proc and base_proc.poll() is None:
        base_proc.terminate()  # 发送SIGTERM
        print("Sent SIGTERM to base_proc. Waiting...")
        try:
            base_proc.wait(timeout=5)
            print("base_proc terminated")
        except subprocess.TimeoutExpired:
            base_proc.kill()
            print("base_proc is killed")
    
    # 2. 终止multiprocessing创建的子进程
    if base_process and base_process.is_alive():
        base_process.terminate()
        base_process.join(timeout=5)
        print("main terminated")
    
    # 退出主进程
    exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_sigint)
    
    # # 启动子进程
    # base_process = multiprocessing.Process(target=log_base_proc)
    # base_process.start()
    
    # print("Waiting for base_proc to start...")
    # time.sleep(10)
    
    try:
        stdout, stderr, ret = run_isolated_shell("ros2 launch servo2c mtc_run.launch.py")
        print("stdout:", stdout)
        print("stderr:", stderr)
        print("return:", ret)
    except Exception as e:
        print(f"Error: {e}")
        handle_sigint(signal.SIGINT, None)  # 出错时主动触发终止流程
    
    # base_process.join()

