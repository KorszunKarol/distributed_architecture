import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class ArrayParallelSearchTest {
    static class TestResult {
        int arraySize;
        int threadCount;
        double averageTime;
        List<Double> individualTimes;

        TestResult(int arraySize, int threadCount) {
            this.arraySize = arraySize;
            this.threadCount = threadCount;
            this.individualTimes = new ArrayList<>();
        }

        void calculateAverage() {
            this.averageTime = individualTimes.stream()
                .mapToDouble(Double::doubleValue)
                .average()
                .orElse(0.0);
        }

        String toCSV() {
            StringBuilder sb = new StringBuilder();
            sb.append(arraySize).append(",")
              .append(threadCount).append(",")
              .append(String.format("%.3f", averageTime));
            for (Double time : individualTimes) {
                sb.append(",").append(String.format("%.3f", time));
            }
            return sb.toString();
        }
    }

    public static void main(String[] args) {
        // Test parameters
        int[] arraySizes = {1000, 10000, 100000, 1000000};
        int[] threadCounts = {1, 2, 4, 8, 16};
        int iterations = 20;  // Increased from 5 to 20 iterations
        List<TestResult> allResults = new ArrayList<>();

        System.out.println("Starting Performance Tests (Array Copy)");
        System.out.println("======================================");

        // Run tests for each combination
        for (int size : arraySizes) {
            for (int threads : threadCounts) {
                TestResult result = new TestResult(size, threads);

                // Create test array
                int[] array = new int[size];
                for (int i = 0; i < array.length; i++) {
                    array[i] = i;
                }

                System.out.printf("\nTesting array size: %d with %d threads\n", size, threads);

                // Run multiple iterations
                for (int iter = 0; iter < iterations; iter++) {
                    System.out.printf("Iteration %d/%d: ", iter + 1, iterations);

                    // Perform search and measure time
                    long startTime = System.nanoTime();
                    int searchResult = ArrayParallelSearch.parallelSearch(size/2, array, threads);
                    long endTime = System.nanoTime();

                    double timeMs = (endTime - startTime) / 1_000_000.0;
                    result.individualTimes.add(timeMs);

                    System.out.printf("Time: %.3f ms\n", timeMs);
                }

                result.calculateAverage();
                allResults.add(result);

                System.out.printf("Average time: %.3f ms\n", result.averageTime);
            }
        }

        // Save results to CSV
        try {
            saveResultsToCSV(allResults, "array_copy_search_results.csv");
            System.out.println("\nResults saved to array_copy_search_results.csv");
        } catch (IOException e) {
            System.err.println("Error saving results: " + e.getMessage());
        }
    }

    private static void saveResultsToCSV(List<TestResult> results, String filename) throws IOException {
        try (FileWriter writer = new FileWriter(filename)) {
            // Write header
            writer.write("ArraySize,ThreadCount,AverageTime,Time1,Time2,Time3,Time4,Time5\n");

            // Write results
            for (TestResult result : results) {
                writer.write(result.toCSV() + "\n");
            }
        }
    }
}
