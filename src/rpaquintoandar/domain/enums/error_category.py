from enum import StrEnum


class ErrorCategory(StrEnum):
    NETWORK = "network"
    TIMEOUT = "timeout"
    SELECTOR = "selector"
    PARSE = "parse"
    DATABASE = "database"
    API = "api"
    UNKNOWN = "unknown"
