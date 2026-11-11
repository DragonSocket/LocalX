class AppError(Exception):
    """Base exception for the application."""
    pass

class SystemDependencyError(AppError):
    """Raised when a required system dependency is missing or incompatible."""
    def __init__(self, dependency_name: str, message: str, required_version: str = None, detected_version: str = None):
        super().__init__(message)
        self.dependency_name = dependency_name
        self.required_version = required_version
        self.detected_version = detected_version

class ConfigParsingError(AppError):
    """Raised when the configuration file cannot be parsed."""
    pass

class ConfigValidationError(AppError):
    """Raised when the configuration fails validation."""
    pass

class HistoryLoadError(AppError):
    """Raised when loading history fails."""
    pass

class HistoryWriteError(AppError):
    """Raised when writing history fails."""
    pass

class NetworkConnectionError(AppError):
    """Raised when connection fails."""
    pass

class NetworkProcessError(AppError):
    """Raised when the network process crashes."""
    pass

class NetworkInvalidStateError(AppError):
    """Raised when an invalid network operation is attempted."""
    pass
