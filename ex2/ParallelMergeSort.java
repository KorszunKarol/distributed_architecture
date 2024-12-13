public class ParallelMergeSort {
    private static class SortThread extends Thread {
        private int[] array;
        private int left;
        private int right;
        private int maxDepth;
        private int currentDepth;

        public SortThread(int[] array, int left, int right, int maxDepth, int currentDepth) {
            this.array = array;
            this.left = left;
            this.right = right;
            this.maxDepth = maxDepth;
            this.currentDepth = currentDepth;
        }

        @Override
        public void run() {
            if (left < right) {
                int mid = (left + right) / 2;

                if (currentDepth < maxDepth) {
                    SortThread leftThread = new SortThread(array, left, mid, maxDepth, currentDepth + 1);
                    SortThread rightThread = new SortThread(array, mid + 1, right, maxDepth, currentDepth + 1);

                    leftThread.start();
                    rightThread.start();

                    try {
                        leftThread.join();
                        rightThread.join();
                    } catch (InterruptedException e) {
                        e.printStackTrace();
                    }
                } else {
                    // Sequential sort for deeper levels
                    sequentialMergeSort(array, left, mid);
                    sequentialMergeSort(array, mid + 1, right);
                }

                merge(array, left, mid, right);
            }
        }
    }

    private static void sequentialMergeSort(int[] array, int left, int right) {
        if (left < right) {
            int mid = (left + right) / 2;
            sequentialMergeSort(array, left, mid);
            sequentialMergeSort(array, mid + 1, right);
            merge(array, left, mid, right);
        }
    }

    private static void merge(int[] array, int left, int mid, int right) {
        int[] temp = new int[right - left + 1];
        int i = left, j = mid + 1, k = 0;

        while (i <= mid && j <= right) {
            if (array[i] <= array[j]) {
                temp[k++] = array[i++];
            } else {
                temp[k++] = array[j++];
            }
        }

        while (i <= mid) {
            temp[k++] = array[i++];
        }

        while (j <= right) {
            temp[k++] = array[j++];
        }

        System.arraycopy(temp, 0, array, left, temp.length);
    }

    public static void parallelSort(int[] array) {
        int maxDepth = 2; // Controls the number of thread levels
        SortThread mainThread = new SortThread(array, 0, array.length - 1, maxDepth, 0);
        mainThread.start();
        try {
            mainThread.join();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }
}
