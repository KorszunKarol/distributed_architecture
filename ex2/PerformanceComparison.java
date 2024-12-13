import java.util.Arrays;
import java.util.Random;

public class PerformanceComparison {
    public static void main(String[] args) {
        int[] sizes = {1000, 10000, 100000, 1000000};

        for (int size : sizes) {
            int[] array = generateRandomArray(size);
            int[] arrayCopy = array.clone();

            // Test parallel sort
            long startTime = System.nanoTime();
            ParallelMergeSort.parallelSort(array);
            long parallelTime = System.nanoTime() - startTime;

            // Test sequential sort
            startTime = System.nanoTime();
            Arrays.sort(arrayCopy);
            long sequentialTime = System.nanoTime() - startTime;

            System.out.println("Array size: " + size);
            System.out.println("Parallel sort time: " + parallelTime / 1_000_000.0 + " ms");
            System.out.println("Sequential sort time: " + sequentialTime / 1_000_000.0 + " ms");
            System.out.println("Speedup: " + (double)sequentialTime / parallelTime);
            System.out.println();
        }
    }

    private static int[] generateRandomArray(int size) {
        Random random = new Random();
        int[] array = new int[size];
        for (int i = 0; i < size; i++) {
            array[i] = random.nextInt();
        }
        return array;
    }
}
