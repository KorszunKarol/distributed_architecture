import matplotlib
matplotlib.use('Agg')  # Set the backend to non-interactive
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def plot_comparison():
    # Read the CSV files
    shared_df = pd.read_csv('shared_memory_search_results.csv')
    copy_df = pd.read_csv('array_copy_search_results.csv')

    # Calculate standard deviation for error bars
    def get_time_stats(df):
        time_cols = [col for col in df.columns if col.startswith('Time')]
        df['StdDev'] = df[time_cols].std(axis=1)
        # Remove the first time (warmup) from average calculation
        df['AverageTime'] = df[time_cols[1:]].mean(axis=1)  # Skip Time1
        return df

    shared_df = get_time_stats(shared_df)
    copy_df = get_time_stats(copy_df)

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle('Performance Comparison: Shared Memory vs Array Copy\n(with 95% confidence intervals)', fontsize=14)

    # Plot 1: Time vs Thread Count for different array sizes
    colors = plt.cm.tab10(np.linspace(0, 1, len(shared_df['ArraySize'].unique())))
    for idx, size in enumerate(shared_df['ArraySize'].unique()):
        color = colors[idx]
        # Plot shared memory
        shared_data = shared_df[shared_df['ArraySize'] == size]
        ax1.errorbar(shared_data['ThreadCount'], shared_data['AverageTime'],
                    yerr=1.96 * shared_data['StdDev'],
                    marker='o', linestyle='-', capsize=5, color=color,
                    label=f'Shared Memory (size={size})')

        # Plot array copy
        copy_data = copy_df[copy_df['ArraySize'] == size]
        ax1.errorbar(copy_data['ThreadCount'], copy_data['AverageTime'],
                    yerr=1.96 * copy_data['StdDev'],
                    marker='s', linestyle='--', capsize=5, color=color,
                    label=f'Array Copy (size={size})')

    ax1.set_xlabel('Number of Threads')
    ax1.set_ylabel('Average Time (ms)')
    ax1.set_title('Execution Time vs Thread Count')
    # ax1.set_yscale('log')  # Set log scale for y-axis
    ax1.grid(True, which="both", ls="-", alpha=0.2)  # Improved grid for log scale
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    # Plot 2: Time vs Array Size for different thread counts
    thread_counts = [1, 2, 4, 8, 16]
    colors = plt.cm.tab10(np.linspace(0, 1, len(thread_counts)))
    for idx, threads in enumerate(thread_counts):
        color = colors[idx]
        # Plot shared memory
        shared_data = shared_df[shared_df['ThreadCount'] == threads]
        ax2.errorbar(shared_data['ArraySize'], shared_data['AverageTime'],
                    yerr=1.96 * shared_data['StdDev'],
                    marker='o', linestyle='-', capsize=5, color=color,
                    label=f'Shared Memory ({threads} threads)')

        # Plot array copy
        copy_data = copy_df[copy_df['ThreadCount'] == threads]
        ax2.errorbar(copy_data['ArraySize'], copy_data['AverageTime'],
                    yerr=1.96 * copy_data['StdDev'],
                    marker='s', linestyle='--', capsize=5, color=color,
                    label=f'Array Copy ({threads} threads)')

    ax2.set_xlabel('Array Size')
    ax2.set_ylabel('Average Time (ms)')
    ax2.set_title('Execution Time vs Array Size')
    # ax2.set_xscale('log')
    # ax2.set_yscale('log')  # Set log scale for y-axis
    ax2.grid(True, which="both", ls="-", alpha=0.2)  # Improved grid for log scale
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    # Adjust layout and save
    plt.tight_layout()
    plt.savefig('search_comparison.png', bbox_inches='tight', dpi=300)
    plt.close()

    # Print statistical analysis
    print("\nStatistical Analysis:")
    for size in shared_df['ArraySize'].unique():
        print(f"\nArray Size: {size}")
        shared_size = shared_df[shared_df['ArraySize'] == size]
        copy_size = copy_df[copy_df['ArraySize'] == size]

        print("\nThread Count | Shared Memory (mean ± std) | Array Copy (mean ± std) | % Difference")
        print("-" * 80)
        for thread in thread_counts:
            sm_data = shared_size[shared_size['ThreadCount'] == thread]
            ac_data = copy_size[copy_size['ThreadCount'] == thread]

            if not sm_data.empty and not ac_data.empty:
                sm = sm_data['AverageTime'].iloc[0]
                sm_std = sm_data['StdDev'].iloc[0]
                ac = ac_data['AverageTime'].iloc[0]
                ac_std = ac_data['StdDev'].iloc[0]
                diff = ((ac - sm) / sm) * 100

                print(f"{thread:11d} | {sm:.3f} ± {sm_std:.3f} ms | {ac:.3f} ± {ac_std:.3f} ms | {diff:+.1f}%")

if __name__ == "__main__":
    plot_comparison()
    print("Plots have been saved to 'search_comparison.png'")
