import subprocess
import time
import sys
import random
import socket
import json
import os

def start_master(port):
    for attempt in range(10):  # Try 10 different ports
        try:
            # Ensure log file is clean
            if os.path.exists('master.log'):
                os.remove('master.log')
            process = subprocess.Popen(
                ['python', 'master.py', str(port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(1)  # Give the master a second to start
            if process.poll() is None:  # If the process is still running
                print(f"Master started on port {port}")
                return process, port
        except subprocess.CalledProcessError:
            pass
        port += 1
    raise Exception("Unable to start master server after 10 attempts")

def start_slave(master_port, behavior):
    # Ensure log file is clean
    if os.path.exists('slave.log'):
        os.remove('slave.log')
    process = subprocess.Popen(
        ['python', 'slave.py', str(master_port), behavior],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    print(f"Started {behavior} slave")
    return process

def start_random_slaves(master_port, n):
    processes = []
    for _ in range(n):
        behavior = random.choice(['read-write', 'read-only'])
        p = start_slave(master_port, behavior)
        processes.append(p)
    return processes

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
        print(f"Failed to connect to master on port {port}: {e}")
        return False

def main():
    print("Starting simulation...")
    print("Available commands:")
    print("  start master <port>")
    print("  start slave <behavior> (behavior: read-write or read-only)")
    print("  start random <n> (starts n slaves with random behaviors)")
    print("  ready (signals all servers to start)")
    print("  quit (ends the simulation)")

    processes = []
    master_port = None
    master_process = None

    while True:
        command = input("Enter command: ").strip().split()

        if not command:
            continue

        if command[0] == 'start':
            if len(command) < 3:
                print("Invalid command format.")
                continue

            if command[1] == 'master':
                if len(command) != 3:
                    print("Usage: start master <port>")
                    continue
                if master_port is not None:
                    print("Master is already running.")
                    continue
                try:
                    initial_port = int(command[2])
                    master_process, master_port = start_master(initial_port)
                    processes.append(master_process)
                except Exception as e:
                    print(f"Failed to start master: {e}")

            elif command[1] == 'slave':
                if len(command) != 3 or command[2] not in ['read-write', 'read-only']:
                    print("Usage: start slave <read-write|read-only>")
                    continue
                if master_port is None:
                    print("Start the master server first.")
                    continue
                behavior = command[2]
                p = start_slave(master_port, behavior)
                processes.append(p)

            elif command[1] == 'random':
                if len(command) != 3:
                    print("Usage: start random <n>")
                    continue
                if master_port is None:
                    print("Start the master server first.")
                    continue
                try:
                    n = int(command[2])
                    if n <= 0:
                        raise ValueError
                except ValueError:
                    print("Please enter a positive integer for the number of slaves.")
                    continue
                new_processes = start_random_slaves(master_port, n)
                processes.extend(new_processes)

            else:
                print("Unknown start command.")

        elif command[0] == 'ready':
            if master_port is None:
                print("Start the master server first.")
                continue
            print("Sending ready signal to master...")
            if send_ready_signal(master_port):
                print("Simulation started.")
            else:
                print("Failed to start simulation.")

        elif command[0] == 'quit':
            print("Terminating all processes...")
            for p in processes:
                p.terminate()
            print("All processes terminated.")
            break

        else:
            print("Unknown command.")

    # Wait for all processes to terminate
    for p in processes:
        p.wait()

if __name__ == "__main__":
    main()