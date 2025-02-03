import os
import subprocess
import time

class PortForwarder:
    def __init__(self):
        self.processes = []
        self.is_kubernetes = os.getenv("TEST_ENV") == "kubernetes"
        
    def start_port_forward(self, service, local_port, target_port):
        if not self.is_kubernetes:
            return  # Do nothing for docker-compose
            
        cmd = f"kubectl port-forward svc/{service} {local_port}:{target_port}"
        process = subprocess.Popen(cmd.split())
        self.processes.append(process)
        time.sleep(2)  # Give it time to establish connection
        
    def cleanup(self):
        for process in self.processes:
            process.terminate()
            
    def __del__(self):
        self.cleanup()