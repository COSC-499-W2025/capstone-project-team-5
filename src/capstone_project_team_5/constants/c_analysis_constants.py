"""
Constants for C/C++ file analysis.

This module contains patterns and keywords for analyzing C/C++ source code
and extracting meaningful statistics for resume bullet generation.
"""

# === C/C++ FILE EXTENSIONS ===
C_FILE_EXTENSIONS = {".c", ".h"}
CPP_FILE_EXTENSIONS = {".cpp", ".hpp", ".cc", ".cxx", ".hh", ".hxx", ".C", ".H"}
ALL_C_EXTENSIONS = C_FILE_EXTENSIONS | CPP_FILE_EXTENSIONS

# === C/C++ KEYWORDS ===
C_KEYWORDS = {
    "auto",
    "break",
    "case",
    "char",
    "const",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extern",
    "float",
    "for",
    "goto",
    "if",
    "inline",
    "int",
    "long",
    "register",
    "restrict",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "struct",
    "switch",
    "typedef",
    "union",
    "unsigned",
    "void",
    "volatile",
    "while",
}

CPP_KEYWORDS = C_KEYWORDS | {
    "alignas",
    "alignof",
    "and",
    "and_eq",
    "asm",
    "bitand",
    "bitor",
    "bool",
    "catch",
    "class",
    "compl",
    "concept",
    "const_cast",
    "constexpr",
    "consteval",
    "constinit",
    "co_await",
    "co_return",
    "co_yield",
    "decltype",
    "delete",
    "dynamic_cast",
    "explicit",
    "export",
    "friend",
    "mutable",
    "namespace",
    "new",
    "noexcept",
    "not",
    "not_eq",
    "nullptr",
    "operator",
    "or",
    "or_eq",
    "private",
    "protected",
    "public",
    "reinterpret_cast",
    "requires",
    "static_assert",
    "static_cast",
    "template",
    "this",
    "thread_local",
    "throw",
    "try",
    "typeid",
    "typename",
    "using",
    "virtual",
    "wchar_t",
    "xor",
    "xor_eq",
}

# === COMPLEXITY INDICATORS ===
# Keywords that indicate algorithmic complexity
COMPLEXITY_KEYWORDS = {
    "for",
    "while",
    "do",
    "if",
    "else",
    "switch",
    "case",
    "goto",
    "break",
    "continue",
    "return",
}

# === STANDARD LIBRARY HEADERS ===
C_STANDARD_HEADERS = {
    "assert.h",
    "ctype.h",
    "errno.h",
    "float.h",
    "limits.h",
    "locale.h",
    "math.h",
    "setjmp.h",
    "signal.h",
    "stdarg.h",
    "stddef.h",
    "stdio.h",
    "stdlib.h",
    "string.h",
    "time.h",
    "complex.h",
    "fenv.h",
    "inttypes.h",
    "iso646.h",
    "stdbool.h",
    "stdint.h",
    "tgmath.h",
    "wchar.h",
    "wctype.h",
}

CPP_STANDARD_HEADERS = {
    "algorithm",
    "array",
    "atomic",
    "bitset",
    "chrono",
    "codecvt",
    "complex",
    "condition_variable",
    "deque",
    "exception",
    "forward_list",
    "fstream",
    "functional",
    "future",
    "initializer_list",
    "iomanip",
    "ios",
    "iosfwd",
    "iostream",
    "istream",
    "iterator",
    "limits",
    "list",
    "locale",
    "map",
    "memory",
    "mutex",
    "new",
    "numeric",
    "ostream",
    "queue",
    "random",
    "ratio",
    "regex",
    "set",
    "sstream",
    "stack",
    "stdexcept",
    "streambuf",
    "string",
    "system_error",
    "thread",
    "tuple",
    "type_traits",
    "typeindex",
    "typeinfo",
    "unordered_map",
    "unordered_set",
    "utility",
    "valarray",
    "vector",
}

# === COMMON LIBRARIES AND FRAMEWORKS ===
COMMON_C_LIBRARIES = {
    "pthread.h": "Multi-threading (POSIX threads)",
    "openssl": "Cryptography (OpenSSL)",
    "curl": "HTTP/networking (libcurl)",
    "sqlite3.h": "Database (SQLite)",
    "gtk": "GUI (GTK)",
    "ncurses.h": "Terminal UI (ncurses)",
    "pcap.h": "Packet capture (libpcap)",
    "zlib.h": "Compression (zlib)",
    "png.h": "Image processing (libpng)",
    "readline": "Command-line editing (readline)",
}

COMMON_CPP_LIBRARIES = {
    "boost": "Boost C++ Libraries",
    "qt": "Qt Framework",
    "eigen": "Linear algebra (Eigen)",
    "opencv": "Computer vision (OpenCV)",
    "grpc": "RPC framework (gRPC)",
    "protobuf": "Protocol Buffers",
    "nlohmann": "JSON library (nlohmann/json)",
    "fmt": "Formatting library (fmt)",
    "spdlog": "Logging library (spdlog)",
    "catch": "Testing framework (Catch2)",
    "gtest": "Testing framework (Google Test)",
}

# === MEMORY MANAGEMENT PATTERNS ===
MEMORY_FUNCTIONS = {
    "malloc",
    "calloc",
    "realloc",
    "free",
    "new",
    "delete",
    "unique_ptr",
    "shared_ptr",
    "weak_ptr",
    "make_unique",
    "make_shared",
}

# === CONCURRENCY INDICATORS ===
CONCURRENCY_PATTERNS = {
    "pthread_create",
    "pthread_join",
    "pthread_mutex",
    "std::thread",
    "std::mutex",
    "std::atomic",
    "std::lock_guard",
    "std::unique_lock",
    "async",
    "future",
    "promise",
}

# === CODE QUALITY INDICATORS ===
DOCUMENTATION_MARKERS = {
    "/**",  # Doxygen style
    "///",  # Doxygen style
    "/*",  # Block comment
    "//",  # Line comment
}

ERROR_HANDLING_PATTERNS = {
    "try",
    "catch",
    "throw",
    "exception",
    "errno",
    "perror",
    "assert",
}

# === OOP PRINCIPLES (C++) ===
INHERITANCE_PATTERNS = {
    r"class\s+\w+\s*:\s*public",  # Public inheritance
    r"class\s+\w+\s*:\s*protected",  # Protected inheritance
    r"class\s+\w+\s*:\s*private",  # Private inheritance
}

POLYMORPHISM_INDICATORS = {
    "virtual",
    "override",
    "final",
    "pure virtual",
}

ENCAPSULATION_INDICATORS = {
    "private:",
    "protected:",
    "public:",
    "getter",
    "setter",
}

# === DESIGN PATTERNS ===
DESIGN_PATTERN_INDICATORS = {
    "Singleton": ["static.*instance", "private.*constructor"],
    "Factory": ["create", "make", "Factory"],
    "Observer": ["notify", "subscribe", "observer", "listener"],
    "Strategy": ["Strategy", "algorithm"],
    "Decorator": ["Decorator", "wrapper"],
    "Adapter": ["Adapter", "adapt"],
    "Builder": ["Builder", "build"],
}

# === DATA STRUCTURES ===
DATA_STRUCTURE_KEYWORDS = {
    "LinkedList",
    "Tree",
    "BinaryTree",
    "BST",
    "Graph",
    "HashMap",
    "HashTable",
    "Queue",
    "Stack",
    "Heap",
    "Trie",
    "AVL",
    "RedBlack",
}

# === ALGORITHM INDICATORS ===
ALGORITHM_PATTERNS = {
    "sort": ["quicksort", "mergesort", "heapsort", "bubblesort", "insertion"],
    "search": ["binary_search", "linear_search", "dfs", "bfs"],
    "graph": ["dijkstra", "bellman", "floyd", "kruskal", "prim"],
    "dynamic_programming": ["memoization", "tabulation", "dp"],
}

# === C++ MODERN FEATURES ===
MODERN_CPP_FEATURES = {
    "lambda": r"\[.*\]\s*\(.*\)\s*\{.*\}",
    "auto": r"\bauto\s+\w+\s*=",
    "constexpr": r"\bconstexpr\b",
    "move_semantics": ["std::move", "&&"],
    "smart_pointers": ["unique_ptr", "shared_ptr", "weak_ptr"],
    "templates": r"template\s*<",
    "raii": ["RAII", "destructor", "~"],
}

# === SOFTWARE ENGINEERING PRACTICES ===
TESTING_INDICATORS = {
    "TEST",
    "test_",
    "Test",
    "assert",
    "EXPECT_",
    "ASSERT_",
    "catch",
    "gtest",
}

OPTIMIZATION_KEYWORDS = {
    "inline",
    "constexpr",
    "noexcept",
    "register",
    "restrict",
    "__attribute__",
    "optimize",
}

# === FILE TYPE CLASSIFICATIONS ===
HEADER_EXTENSIONS = {".h", ".hpp", ".hh", ".hxx", ".H"}
SOURCE_EXTENSIONS = {".c", ".cpp", ".cc", ".cxx", ".C"}
