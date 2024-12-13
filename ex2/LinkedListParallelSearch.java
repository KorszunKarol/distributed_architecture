import java.util.LinkedList;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

public class LinkedListParallelSearch {
    private LinkedList<Integer> list;
    private int searchValue;
    private AtomicBoolean found;
    private AtomicInteger finderThread;

    public LinkedListParallelSearch(LinkedList<Integer> list, int searchValue) {
        this.list = list;
        this.searchValue = searchValue;
        this.found = new AtomicBoolean(false);
        this.finderThread = new AtomicInteger(-1);
    }

    class ForwardSearchThread extends Thread {
        @Override
        public void run() {
            for (int i = 0; i < list.size() / 2; i++) {
                if (found.get()) return;
                if (list.get(i) == searchValue) {
                    if (found.compareAndSet(false, true)) {
                        finderThread.set(1);
                    }
                    return;
                }
            }
        }
    }

    class BackwardSearchThread extends Thread {
        @Override
        public void run() {
            for (int i = list.size() - 1; i >= list.size() / 2; i--) {
                if (found.get()) return;
                if (list.get(i) == searchValue) {
                    if (found.compareAndSet(false, true)) {
                        finderThread.set(2);
                    }
                    return;
                }
            }
        }
    }

    public int search() throws InterruptedException {
        Thread forward = new ForwardSearchThread();
        Thread backward = new BackwardSearchThread();

        forward.start();
        backward.start();

        forward.join();
        backward.join();

        return finderThread.get();
    }
}
