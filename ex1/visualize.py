import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re
from collections import defaultdict
import os

# Create a directory to store the plots
os.makedirs('plots', exist_ok=True)

def parse_log(filename):
    data = {
        'timestamp': [],
        'level': [],
        'message': []
    }
    with open(filename, 'r') as f:
        for line in f:
            match = re.match(r'(\S+ \S+) - (\S+) - (.*)', line)
            if match:
                timestamp, level, message = match.groups()
                data['timestamp'].append(pd.to_datetime(timestamp))
                data['level'].append(level)
                data['message'].append(message)
    return pd.DataFrame(data)

def extract_metrics(df):
    metrics = defaultdict(list)
    for _, row in df.iterrows():
        if 'Lock acquired by server' in row['message']:
            metrics['lock_acquire_times'].append(row['timestamp'])
            server_id = int(row['message'].split()[-1])
            metrics['lock_acquire_server'].append(server_id)
        elif 'Lock released' in row['message']:
            metrics['lock_release_times'].append(row['timestamp'])
        elif 'read value' in row['message']:
            metrics['read_times'].append(row['timestamp'])
            value = int(row['message'].split()[-1])
            metrics['read_values'].append(value)
            server_id = int(row['message'].split()[1])
            metrics['read_server'].append(server_id)
        elif 'updated value' in row['message']:
            metrics['update_times'].append(row['timestamp'])
            value = int(row['message'].split()[-1])
            metrics['update_values'].append(value)
            server_id = int(row['message'].split()[1])
            metrics['update_server'].append(server_id)
    return metrics

def plot_lock_acquisitions(metrics):
    plt.figure(figsize=(12, 6))
    sns.histplot(metrics['lock_acquire_times'], bins=30, label='Lock Acquisitions', color='blue', kde=False)
    sns.histplot(metrics['lock_release_times'], bins=30, label='Lock Releases', color='green', kde=False)
    plt.xlabel('Time')
    plt.ylabel('Count')
    plt.title('Lock Acquisitions and Releases Over Time')
    plt.legend()
    plt.savefig('plots/lock_acquisitions.png')
    plt.close()

def plot_read_write_operations(metrics):
    plt.figure(figsize=(12, 6))
    plt.scatter(metrics['read_times'], metrics['read_values'], label='Read Operations', alpha=0.6)
    plt.scatter(metrics['update_times'], metrics['update_values'], label='Write Operations', alpha=0.6)
    plt.xlabel('Time')
    plt.ylabel('Value')
    plt.title('Read and Write Operations Over Time')
    plt.legend()
    plt.savefig('plots/read_write_operations.png')
    plt.close()

def plot_server_activity(metrics):
    plt.figure(figsize=(12, 6))
    for server_id in set(metrics['lock_acquire_server']):
        server_acquires = [t for t, s in zip(metrics['lock_acquire_times'], metrics['lock_acquire_server']) if s == server_id]
        plt.scatter([t for t in server_acquires], [server_id] * len(server_acquires), label=f'Server {server_id}')
    plt.xlabel('Time')
    plt.ylabel('Server ID')
    plt.title('Lock Acquisition Activity by Server')
    plt.legend()
    plt.savefig('plots/server_activity.png')
    plt.close()

def plot_value_progression(metrics):
    plt.figure(figsize=(12, 6))
    plt.plot(metrics['update_times'], metrics['update_values'], marker='o')
    plt.xlabel('Time')
    plt.ylabel('Shared Variable Value')
    plt.title('Progression of Shared Variable Value')
    plt.savefig('plots/value_progression.png')
    plt.close()

def check_state_consistency(master_metrics, slave_metrics):
    master_updates = list(zip(master_metrics['update_times'], master_metrics['update_values']))
    slave_reads = list(zip(slave_metrics['read_times'], slave_metrics['read_values']))

    inconsistencies = []
    for read_time, read_value in slave_reads:
        expected_value = next((value for time, value in master_updates if time < read_time), None)
        if expected_value is not None and expected_value != read_value:
            inconsistencies.append((read_time, expected_value, read_value))

    if inconsistencies:
        print("State inconsistencies detected:")
        for time, expected, actual in inconsistencies:
            print(f"At {time}: Expected {expected}, but read {actual}")
    else:
        print("No state inconsistencies detected.")

def main():
    master_df = parse_log('master.log')
    slave_df = parse_log('slave.log')

    master_metrics = extract_metrics(master_df)
    slave_metrics = extract_metrics(slave_df)

    print("Generating visualizations...")
    plot_lock_acquisitions(master_metrics)
    plot_read_write_operations(master_metrics)
    plot_server_activity(master_metrics)
    plot_value_progression(master_metrics)
    print("Visualizations saved in the 'plots' directory.")

    print("Checking state consistency...")
    check_state_consistency(master_metrics, slave_metrics)

if __name__ == "__main__":
    main()