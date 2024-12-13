import socket
import json
import time
import logging
import argparse
import sys

# Configure logging
logging.basicConfig(
    filename='slave.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Slave')

def send_message(sock, message):
    try:
        sock.sendall(json.dumps(message).encode())
        data = sock.recv(1024)
        return json.loads(data.decode())
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        return None

def acquire_lock(sock):
    while True:
        response = send_message(sock, {'operation': 'ACQUIRE'})
        if response is None:
            logger.error("Failed to acquire lock. No response from server.")
            return False
        if response['status'] == 'GRANTED':
            return True
        elif response['status'] == 'QUEUED':
            logger.info(f"Queued for lock at position {response['position']}")
            time.sleep(0.1)  # Wait a bit before checking again
            response = send_message(sock, {'operation': 'CHECK_LOCK'})
            if response is None:
                logger.error("Failed to check lock status. No response from server.")
                return False
            if response['status'] == 'GRANTED':
                return True

def release_lock(sock):
    response = send_message(sock, {'operation': 'RELEASE'})
    if response is None:
        logger.error("Failed to release lock. No response from server.")

def read_value(sock):
    response = send_message(sock, {'operation': 'READ'})
    if response is None:
        logger.error("Failed to read value. No response from server.")
        return None
    return response['value']

def update_value(sock, value):
    response = send_message(sock, {'operation': 'UPDATE', 'value': value})
    if response is None:
        logger.error("Failed to update value. No response from server.")

def read_write_behavior(sock):
    for i in range(10):
        if not acquire_lock(sock):
            logger.error("Failed to acquire lock. Exiting.")
            return
        value = read_value(sock)
        if value is None:
            logger.error("Failed to read value. Exiting.")
            return
        logger.info(f"Read value: {value}")
        new_value = value + 1
        update_value(sock, new_value)
        logger.info(f"Updated value to: {new_value}")
        release_lock(sock)
        logger.info(f"Iteration {i+1} completed")
        time.sleep(1)

def read_only_behavior(sock):
    for i in range(10):
        if not acquire_lock(sock):
            logger.error("Failed to acquire lock. Exiting.")
            return
        value = read_value(sock)
        if value is None:
            logger.error("Failed to read value. Exiting.")
            return
        logger.info(f"Read value: {value}")
        release_lock(sock)
        logger.info(f"Iteration {i+1} completed")
        time.sleep(1)

def main(master_port, behavior):
    logger.info(f"Starting slave with behavior: {behavior}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(('localhost', master_port))
        if behavior == 'read-write':
            read_write_behavior(sock)
        elif behavior == 'read-only':
            read_only_behavior(sock)
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        sock.close()
    logger.info("Slave finished execution")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Slave Server")
    parser.add_argument("master_port", type=int, help="Port of the master server")
    parser.add_argument("behavior", choices=['read-write', 'read-only'], help="Behavior of the slave")
    args = parser.parse_args()
    main(args.master_port, args.behavior)