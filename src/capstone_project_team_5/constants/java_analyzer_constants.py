"""Constants for Java code analysis."""

# Common Java collections and data structures
JAVA_COLLECTIONS = {
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

# Loop statement types in Tree-sitter Java grammar
JAVA_LOOP_TYPES = {
    "for_statement",
    "while_statement",
    "enhanced_for_statement",
    "do_statement",
}

# Time complexity mappings based on loop depth
TIME_COMPLEXITY_BY_DEPTH = {
    0: "O(1)",
    1: "O(n)",
    2: "O(n²)",
    3: "O(n³)",
}


def get_time_complexity_from_depth(depth: int) -> str:
    """Convert loop nesting depth to complexity estimate.

    Args:
        depth: Maximum loop nesting depth found

    Returns:
        String representation of estimated time complexity
    """
    if depth in TIME_COMPLEXITY_BY_DEPTH:
        return TIME_COMPLEXITY_BY_DEPTH[depth]
    return f"O(n^{depth})"
