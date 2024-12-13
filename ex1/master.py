import socket
import json
import threading
from lock import QueueLock
import sys
import logging
import time

# Configure logging
logging.basicConfig(
    filename='master.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Master')

shared_var = 0
lock = QueueLock()
servers = {}
ready = False

def handle_server(conn, server_id):
    global shared_var, ready
    logger.info(f"New connection from server {server_id}")
    while True:
        data = conn.recv(1024)
        if not data:
            break
        message = json.loads(data.decode())
        if message['operation'] == 'SET_READY':
            ready = True
            response = {'status': 'OK'}
            logger.info("Simulation started")
        elif not ready:
            response = {'status': 'WAIT'}
        else:
            logger.info(f"Received message from server {server_id}: {message}")
            if message['operation'] == 'ACQUIRE':
                if lock.acquire(server_id):
                    response = {'status': 'GRANTED'}
                    logger.info(f"Lock acquired by server {server_id}")
                else:
                    position = lock.queue_position(server_id)
                    response = {'status': 'QUEUED', 'position': position}
                    logger.info(f"Server {server_id} queued for lock at position {position}")
            elif message['operation'] == 'CHECK_LOCK':
                if lock.is_next(server_id):
                    lock.acquire(server_id)  # Actually acquire the lock
                    response = {'status': 'GRANTED'}
                    logger.info(f"Lock acquired by server {server_id}")
                else:
                    position = lock.queue_position(server_id)
                    response = {'status': 'QUEUED', 'position': position}
            elif message['operation'] == 'RELEASE':
                next_server = lock.release()
                response = {'status': 'OK', 'next_server': next_server}
                if next_server is not None:
                    logger.info(f"Lock released and granted to server {next_server}")
                else:
                    logger.info("Lock released and now available")
            elif message['operation'] == 'READ':
                response = {'value': shared_var}
                logger.info(f"Server {server_id} read value: {shared_var}")
            elif message['operation'] == 'UPDATE':
                shared_var = message['value']
                response = {'status': 'OK'}
                logger.info(f"Server {server_id} updated value to: {shared_var}")
        conn.sendall(json.dumps(response).encode())
    logger.info(f"Connection closed for server {server_id}")
    conn.close()

def accept_connections(server_socket):
    server_id = 0
    while True:
        conn, addr = server_socket.accept()
        servers[server_id] = conn
        threading.Thread(target=handle_server, args=(conn, server_id)).start()
        server_id += 1

def main(port):
    global ready
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for attempt in range(10):  # Try 10 different ports
        try:
            server.bind(('localhost', port))
            break
        except OSError:
            logger.warning(f"Port {port} is in use, trying next port.")
            port += 1
    else:
        logger.error("Unable to bind to a port after 10 attempts.")
        return

    server.listen()
    logger.info(f"Master server started on port {port}, waiting for connections...")
    print(f"Master server started on port {port}, waiting for connections...")

    accept_thread = threading.Thread(target=accept_connections, args=(server,))
    accept_thread.start()

    # Wait for the ready signal
    while not ready:
        time.sleep(0.1)

    logger.info("Simulation started")

    # Keep the main thread alive to accept user inputs or handle shutdown
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Master server shutting down.")
        print("Master server shutting down.")
        server.close()
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python master.py <port>")
        sys.exit(1)
    main(int(sys.argv[1]))