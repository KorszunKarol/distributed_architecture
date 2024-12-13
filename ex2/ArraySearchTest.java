public class ArraySearchTest {
    public static void main(String[] args) {
        // Create test array
        int[] array = new int[1000];
        for (int i = 0; i < array.length; i++) {
            array[i] = i;
        }

        // Test with different thread counts
        System.out.println("Testing Array Parallel Search (with copy):");
        int[] threadCounts = {2, 4, 8};

        for (int threads : threadCounts) {
            System.out.println("\nSearching with " + threads + " threads:");

            // Search for existing number
            int result1 = ArrayParallelSearch.parallelSearch(500, array, threads);
            System.out.println("Searching for 500, found at index: " + result1);

            // Search for non-existing number
            int result2 = ArrayParallelSearch.parallelSearch(1001, array, threads);
            System.out.println("Searching for 1001, result: " + result2);
        }
    }
}
