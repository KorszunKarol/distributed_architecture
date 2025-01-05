class DataStore:
    def __init__(self, ...):
        self._version_history = []
        self._version_log_file = f"{log_dir}/{node_id}_version_history.log"

    def log_version_update(self, version, operation):
        with open(self._version_log_file, 'a') as f:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} - Version {version}: {operation}\n")