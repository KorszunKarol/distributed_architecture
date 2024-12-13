import socket
import sys
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Server')

def acquire_lock(sock):
    msg = {'operation': 'ACQUIRE'}
    sock.sendall(json.dumps(msg).encode())
    data = sock.recv(1024)
    response = json.loads(data.decode())
    return response['status'] == 'GRANTED'

def release_lock(sock):
    msg = {'operation': 'RELEASE'}
    sock.sendall(json.dumps(msg).encode())
    sock.recv(1024)

def read_value(sock):
    msg = {'operation': 'READ'}
    sock.sendall(json.dumps(msg).encode())
    data = sock.recv(1024)
    response = json.loads(data.decode())
    return response['value']

def update_value(sock, value):
    msg = {'operation': 'UPDATE', 'value': value}
    sock.sendall(json.dumps(msg).encode())
    sock.recv(1024)

def read_write_behavior(sock):
    for i in range(10):
        while not acquire_lock(sock):
            time.sleep(0.1)
        value = read_value(sock)
        logger.info(f"Read value: {value}")
        new_value = value + 1
        update_value(sock, new_value)
        logger.info(f"Updated value to: {new_value}")
        release_lock(sock)
        logger.info(f"Iteration {i+1} completed")
        time.sleep(1)

def read_only_behavior(sock):
    for i in range(10):
        while not acquire_lock(sock):
            time.sleep(0.1)
        value = read_value(sock)
        logger.info(f"Read value: {value}")
        release_lock(sock)
        logger.info(f"Iteration {i+1} completed")
        time.sleep(1)

def main():
    behavior = sys.argv[1]
    logger.info(f"Starting server with behavior: {behavior}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 5000))
    if behavior == 'read-write':
        read_write_behavior(sock)
    elif behavior == 'read-only':
        read_only_behavior(sock)
    sock.close()
    logger.info("Server finished execution")

if __name__ == "__main__":
    main()