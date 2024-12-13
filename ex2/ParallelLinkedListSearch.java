import java.util.LinkedList;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.logging.Logger;
import java.util.logging.Level;

public class ParallelLinkedListSearch {
    private static final Logger LOGGER = Logger.getLogger(ParallelLinkedListSearch.class.getName());
    private LinkedList<Integer> list;
    private int target;
    private AtomicBoolean found;
    private AtomicInteger foundIndex;
    private AtomicInteger winningThread;
    private int numThreads;

    public ParallelLinkedListSearch(LinkedList<Integer> list, int target, int numThreads) {
        this.list = list;
        this.target = target;
        this.found = new AtomicBoolean(false);
        this.foundIndex = new AtomicInteger(-1);
        this.winningThread = new AtomicInteger(-1);
        this.numThreads = numThreads;
    }

    public void search() {
        LOGGER.info("Starting parallel search for target: " + target + " with " + numThreads + " threads");
        Thread[] threads = new Thread[numThreads];
        int segmentSize = list.size() / numThreads;

        for (int i = 0; i < numThreads; i++) {
            final int threadIndex = i;
            final int start = i * segmentSize;
            final int end = (i == numThreads - 1) ? list.size() : (i + 1) * segmentSize;

            threads[i] = new Thread(() -> searchSegment(start, end, threadIndex), "SearchThread-" + i);
            threads[i].start();
        }

        try {
            for (Thread thread : threads) {
                thread.join(10000); // 10 seconds timeout
            }
            for (Thread thread : threads) {
                if (thread.isAlive()) {
                    LOGGER.warning("Search timed out after 10 seconds");
                    break;
                }
            }
        } catch (InterruptedException e) {
            LOGGER.log(Level.SEVERE, "Search interrupted", e);
        }

        if (found.get()) {
            LOGGER.info("Number " + target + " found at index " + foundIndex.get() +
                        " by thread " + winningThread.get());
        } else {
            LOGGER.info("Number " + target + " not found in the list.");
        }
    }

    private void searchSegment(int start, int end, int threadIndex) {
        LOGGER.info("Thread " + threadIndex + " searching from index " + start + " to " + end);
        for (int i = start; i < end; i++) {
            if (found.get()) {
                LOGGER.info("Thread " + threadIndex + " terminated early");
                return;
            }
            if (list.get(i) == target) {
                if (found.compareAndSet(false, true)) {
                    foundIndex.set(i);
                    winningThread.set(threadIndex);
                    LOGGER.info("Thread " + threadIndex + " found target at index " + i);
                }
                return;
            }
            if (i % 10000 == 0) {
                LOGGER.fine("Thread " + threadIndex + " at index " + i);
            }
        }
        LOGGER.info("Thread " + threadIndex + " completed without finding target");
    }

    public static void main(String[] args) {
        LOGGER.setLevel(Level.FINE);

        LOGGER.info("Starting the program...");

        LinkedList<Integer> list = new LinkedList<>();
        LOGGER.info("Creating a list with 1,000,000 elements...");
        for (int i = 0; i < 100_000; i++) {
            list.add(i);
        }
        LOGGER.info("List created.");

        int target = 57_000;
        int numThreads = 8;
        LOGGER.info("Searching for " + target + " using " + numThreads + " threads...");
        ParallelLinkedListSearch searcher = new ParallelLinkedListSearch(list, target, numThreads);
        searcher.search();

        LOGGER.info("Search completed.");

        LOGGER.info("Program finished.");
    }
}