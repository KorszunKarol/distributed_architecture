import java.util.LinkedList;

public class LinkedListSearchTest {
    public static void main(String[] args) {
        // Create and populate LinkedList
        LinkedList<Integer> list = new LinkedList<>();
        for (int i = 0; i < 100; i++) {
            list.add(i);
        }

        try {
            // Test case 1: Number at beginning
            LinkedListParallelSearch search1 = new LinkedListParallelSearch(list, 5);
            System.out.println("Searching for 5. Found by thread: " + search1.search());

            // Test case 2: Number at end
            LinkedListParallelSearch search2 = new LinkedListParallelSearch(list, 95);
            System.out.println("Searching for 95. Found by thread: " + search2.search());

            // Test case 3: Number not in list
            LinkedListParallelSearch search3 = new LinkedListParallelSearch(list, 1000);
            System.out.println("Searching for 1000. Found by thread: " + search3.search());
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }
}
