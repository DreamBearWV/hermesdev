# system_tools.py
import subprocess

def get_system_status_data():
    """讀取樹莓派系統進程與 Docker 狀態"""
    status_report = {}
    
    # 1. 讀取 RAM 與 CPU 佔用最高的前 10 個進程
    try:
        ps_output = subprocess.check_output(
            "ps aux --sort=-%mem | head -n 11", 
            shell=True, 
            text=True
        )
        status_report["top_memory_processes"] = ps_output.strip()
    except Exception as e:
        status_report["top_memory_processes"] = f"無法讀取進程: {str(e)}"

    # 2. 讀取 Docker 容器狀態 (透過掛載的 docker.sock)
    try:
        docker_output = subprocess.check_output(
            "curl -s --unix-socket /var/run/docker.sock http://localhost/containers/json?all=1", 
            shell=True, 
            text=True
        )
        status_report["docker_containers_raw"] = docker_output.strip()
    except Exception as e:
        status_report["docker_containers_raw"] = f"無法讀取 Docker Socket: {str(e)}"

    # 3. 讀取系統記憶體與硬碟使用率
    try:
        df_output = subprocess.check_output("df -h /", shell=True, text=True)
        free_output = subprocess.check_output("free -h", shell=True, text=True)
        status_report["disk_usage"] = df_output.strip()
        status_report["memory_usage"] = free_output.strip()
    except Exception as e:
        status_report["hardware_metrics"] = f"無法讀取硬體指標: {str(e)}"

    return status_report