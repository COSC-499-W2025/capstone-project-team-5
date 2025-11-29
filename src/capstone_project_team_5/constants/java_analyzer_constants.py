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

# Directories to skip during Java file scanning
SKIP_DIRS: frozenset[str] = frozenset(
    {
        # Build outputs
        "target",  # Maven
        "build",  # Gradle
        "out",  # IntelliJ IDEA
        "bin",  # Eclipse
        "dist",  # Distribution
        "classes",  # Compiled classes
        # Build tool directories
        ".gradle",
        ".mvn",
        ".m2",
        # Dependencies
        "node_modules",
        "vendor",
        "lib",
        "libs",
        "dependencies",
        # Version control
        ".git",
        ".svn",
        ".hg",
        # IDEs
        ".idea",
        ".vscode",
        ".vs",
        ".settings",
        ".classpath",
        ".project",
        # Test/coverage reports
        "coverage",
        "test-results",
        "test-reports",
        "jacoco",
        # Cache/temp
        ".cache",
        "tmp",
        "temp",
        "__pycache__",
        ".pytest_cache",
        # Generated code
        "generated",
        "generated-sources",
        "generated-test-sources",
    }
)

# Common coding patterns to detect
CODING_PATTERNS: dict[str, list[str]] = {
    "Singleton": ["getInstance", "instance", "INSTANCE"],
    "Factory": ["create", "make", "newInstance", "build"],
    "Observer": ["notify", "subscribe", "addListener", "removeListener", "observer"],
    "Strategy": ["execute", "doAlgorithm", "strategy"],
    "Builder": ["build", "builder", "withProperty", "setProperty"],
    "Adapter": ["adapt", "adapter", "wrap", "wrapper"],
}

# Patterns for detecting specific algorithms in code
ALGORITHM_INDICATORS: dict[str, list[str]] = {
    "BFS": ["bfs", "breadthfirst", "breadth_first", "queue", "levelorder"],
    "DFS": ["dfs", "depthfirst", "depth_first", "stack", "preorder", "postorder", "inorder"],
}
