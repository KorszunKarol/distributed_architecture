public class SharedMemoryParallelSearch {
    private static volatile boolean found = false;
    private static volatile int foundIndex = -1;
    private static volatile int finderThread = -1;

    public static int parallelSearch(int toSearch, int[] array, int numThreads) {
        found = false;
        foundIndex = -1;
        finderThread = -1;

        Thread[] threads = new Thread[numThreads];
        int segmentSize = array.length / numThreads;

        for (int i = 0; i < numThreads; i++) {
            final int threadId = i;
            final int start = i * segmentSize;
            final int end = (i == numThreads - 1) ? array.length : (i + 1) * segmentSize;

            threads[i] = new Thread(() -> {
                for (int j = start; j < end && !found; j++) {
                    if (array[j] == toSearch) {
                        synchronized (SharedMemoryParallelSearch.class) {
                            if (!found) {
                                found = true;
                                foundIndex = j;
                                finderThread = threadId;
                            }
                        }
                        break;
                    }
                }
            });
            threads[i].start();
        }

        for (Thread thread : threads) {
            try {
                thread.join();
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }

        if (found) {
            System.out.println("Found by thread: " + finderThread);
            return foundIndex;
        }
        return -1;
    }
}
