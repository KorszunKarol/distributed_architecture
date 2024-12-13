from collections import deque
import time

class QueueLock:
    def __init__(self):
        self.locked = False
        self.queue = deque()

    def acquire(self, server_id):
        if not self.locked and not self.queue:
            self.locked = True
            return True
        self.queue.append(server_id)
        return False

    def release(self):
        if self.queue:
            next_server = self.queue.popleft()
            return next_server
        self.locked = False
        return None

    def is_next(self, server_id):
        return self.queue and self.queue[0] == server_id

    def queue_position(self, server_id):
        try:
            return self.queue.index(server_id)
        except ValueError:
            return -1

