"""Constants for Java code analysis."""

JAVA_COLLECTIONS: frozenset[str] = frozenset(
    {
        "ArrayList",
        "LinkedList",
        "Vector",
        "Stack",
        "HashSet",
        "LinkedHashSet",
        "TreeSet",
        "HashMap",
        "LinkedHashMap",
        "TreeMap",
        "Hashtable",
        "PriorityQueue",
        "ArrayDeque",
        "Queue",
        "Deque",
        "Map",
        "List",
        "Set",
        "Collection",
        "ConcurrentHashMap",
        "CopyOnWriteArrayList",
        "WeakHashMap",
    }
)
