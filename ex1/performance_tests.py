import subprocess
import time
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import os
import signal
import psutil
import socket
import json
import re
from collections import defaultdict
import threading

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def log_output(process, name):
    for line in iter(process.stdout.readline, b''):
        print(f"{name} output: {line.decode().strip()}")

def run_simulation(num_slaves, duration):
    port = find_free_port()
    print(f"Starting master process on port {port}...")
    master_process = subprocess.Popen(['python', 'master.py', str(port)],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      bufsize=1,
                                      universal_newlines=True)

    # Start a thread to log master output
    threading.Thread(target=log_output, args=(master_process, "Master"), daemon=True).start()

    # Wait for the master process to start listening
    for _ in range(30):  # Wait up to 30 seconds
        if is_port_in_use(port):
            print(f"Master process is now listening on port {port}")
            break
        time.sleep(1)
    else:
        print(f"Error: Master process failed to start listening on port {port}")
        master_process.terminate()
        return

    if master_process.poll() is not None:
        print("Error: Master process terminated unexpectedly.")
        return

    print(f"Starting {num_slaves} slave processes...")
    slave_processes = []
    for i in range(num_slaves):
        behavior = 'read-write' if i % 2 == 0 else 'read-only'
        slave_process = subprocess.Popen(['python', 'slave.py', str(port), behavior],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         bufsize=1,
                                         universal_newlines=True)
        slave_processes.append(slave_process)
        # Start a thread to log slave output
        threading.Thread(target=log_output, args=(slave_process, f"Slave {i}"), daemon=True).start()

    # Send ready signal to start the simulation
    send_ready_signal(port)

    print(f"Letting simulation run for {duration} seconds...")
    start_time = time.time()
    while time.time() - start_time < duration:
        time.sleep(2)
        print(f"Simulation running for {int(time.time() - start_time)} seconds...")
        if master_process.poll() is not None:
            print("Error: Master process terminated unexpectedly during simulation.")
            break
        for i, slave_process in enumerate(slave_processes):
            if slave_process.poll() is not None:
                print(f"Error: Slave process {i} terminated unexpectedly during simulation.")

    print("Terminating all processes...")
    terminate_processes(master_process, slave_processes)

    print("Collecting output from all processes...")
    collect_process_output(master_process, slave_processes)

def send_ready_signal(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(('localhost', port))
        message = json.dumps({'operation': 'SET_READY'})
        sock.sendall(message.encode())
        response = sock.recv(1024)
        sock.close()
        return json.loads(response.decode()).get('status') == 'OK'
    except Exception as e:
        print(f"Failed to send ready signal: {e}")
        return False

def terminate_processes(master_process, slave_processes):
    try:
        parent = psutil.Process(master_process.pid)
        for child in parent.children(recursive=True):
            child.terminate()
        parent.terminate()
    except psutil.NoSuchProcess:
        print("Master process already terminated.")

    for slave_process in slave_processes:
        try:
            slave_process.terminate()
        except psutil.NoSuchProcess:
            print(f"Slave process {slave_process.pid} already terminated.")

    # Wait for all processes to finish
    try:
        master_process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        print("Master process did not terminate in time. Forcing termination.")
        master_process.kill()

    for i, slave_process in enumerate(slave_processes):
        try:
            slave_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print(f"Slave process {i} did not terminate in time. Forcing termination.")
            slave_process.kill()

def collect_process_output(master_process, slave_processes):
    master_stdout, master_stderr = master_process.communicate()
    print("Master stdout:", master_stdout.decode())
    print("Master stderr:", master_stderr.decode())

    for i, slave_process in enumerate(slave_processes):
        slave_stdout, slave_stderr = slave_process.communicate()
        print(f"Slave {i} stdout:", slave_stdout.decode())
        print(f"Slave {i} stderr:", slave_stderr.decode())

def parse_log(filename):
    if not os.path.exists(filename):
        print(f"Error: Log file {filename} not found.")
        return defaultdict(list)

    data = defaultdict(list)
    with open(filename, 'r') as f:
        for line in f:
            match = re.match(r'(\S+ \S+) - (\S+) - (.*)', line)
            if match:
                timestamp, _, message = match.groups()
                timestamp = pd.to_datetime(timestamp)
                if 'Lock acquired' in message:
                    data['lock_acquire'].append(timestamp)
                elif 'Lock released' in message:
                    data['lock_release'].append(timestamp)
                elif 'read value' in message:
                    data['read'].append(timestamp)
                elif 'updated value' in message:
                    data['write'].append(timestamp)
    return data

def calculate_metrics(data):
    metrics = {}

    # Calculate average time between lock acquisitions
    lock_acquire_times = pd.Series(data['lock_acquire'])
    metrics['avg_time_between_locks'] = lock_acquire_times.diff().mean().total_seconds()

    # Calculate average lock hold time
    lock_hold_times = pd.Series(data['lock_release']) - pd.Series(data['lock_acquire'])
    metrics['avg_lock_hold_time'] = lock_hold_times.mean().total_seconds()

    # Calculate read and write operation frequencies
    total_time = (data['lock_release'][-1] - data['lock_acquire'][0]).total_seconds()
    metrics['read_frequency'] = len(data['read']) / total_time
    metrics['write_frequency'] = len(data['write']) / total_time

    return metrics

def plot_lock_usage(data, num_slaves):
    plt.figure(figsize=(12, 6))
    sns.histplot(data['lock_acquire'], bins=30, kde=True, color='blue', label='Lock Acquisitions')
    sns.histplot(data['lock_release'], bins=30, kde=True, color='red', label='Lock Releases')
    plt.xlabel('Time')
    plt.ylabel('Frequency')
    plt.title(f'Lock Usage Over Time ({num_slaves} slaves)')
    plt.legend()
    plt.savefig(f'lock_usage_{num_slaves}_slaves.png')
    plt.close()

def plot_operation_timeline(data, num_slaves):
    plt.figure(figsize=(12, 6))
    plt.scatter(data['read'], [1] * len(data['read']), label='Read Operations', alpha=0.5)
    plt.scatter(data['write'], [2] * len(data['write']), label='Write Operations', alpha=0.5)
    plt.yticks([1, 2], ['Read', 'Write'])
    plt.xlabel('Time')
    plt.title(f'Timeline of Read and Write Operations ({num_slaves} slaves)')
    plt.legend()
    plt.savefig(f'operation_timeline_{num_slaves}_slaves.png')
    plt.close()

def run_tests():
    print("Running performance tests...")

    # Run simulations with different numbers of slaves
    slave_counts = [2, 5, 10, 100]
    metrics_results = []

    for num_slaves in slave_counts:
        print(f"Running simulation with {num_slaves} slaves...")
        run_simulation(num_slaves, duration=30)  # Increased duration for more data

        data = parse_log('master.log')

        if not data:
            print(f"No data collected for simulation with {num_slaves} slaves. Skipping metrics calculation and plotting.")
            continue

        # Calculate metrics
        metrics = calculate_metrics(data)
        metrics['num_slaves'] = num_slaves
        metrics_results.append(metrics)

        # Generate plots
        plot_lock_usage(data, num_slaves)
        plot_operation_timeline(data, num_slaves)

        print(f"Completed simulation with {num_slaves} slaves.")

        # Add a delay between simulations
        time.sleep(5)

    if not metrics_results:
        print("No metrics collected. Cannot generate summary plot.")
        return

    # Create a summary plot
    df = pd.DataFrame(metrics_results)
    df.set_index('num_slaves', inplace=True)

    plt.figure(figsize=(12, 8))
    df.plot(kind='bar', ax=plt.gca())
    plt.title('Performance Metrics vs Number of Slaves')
    plt.xlabel('Number of Slaves')
    plt.ylabel('Metric Value')
    plt.legend(title='Metrics')
    plt.tight_layout()
    plt.savefig('performance_summary.png')
    plt.close()

    print("Performance tests completed. Plots have been saved.")

if __name__ == "__main__":
    run_tests()