import os
import subprocess

script_dir = os.path.dirname(__file__)

def start_isolated_shell(command, bashrc_path="/root/.bashrc"):
    """Non-block function for running a shell"""
    minimal_env = {
        'PATH': '/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin',
        'HOME': os.path.expanduser('~'),
        'PWD': os.getcwd(),
    }
    
    ros2_source_path = os.path.join(script_dir, "..", "..", "..", "install", "setup.bash")
    full_command = f"source {bashrc_path}; source {ros2_source_path}; echo $PATH; {command}"
    
    process = subprocess.Popen(
        ['/bin/bash', '-i', '-c', full_command],
        env=minimal_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return process


def run_isolated_shell(command, bashrc_path="~/.bashrc"):
    process = start_isolated_shell(command, bashrc_path)
    stdout, stderr = process.communicate()
    return stdout.decode(), stderr.decode(), process.returncode