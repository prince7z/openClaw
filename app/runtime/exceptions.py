class OpenClawRuntimeError(Exception):
    """Base exception for all runtime errors."""
    pass

class ContainerError(OpenClawRuntimeError):
    """Raised when a Docker container operation fails."""
    pass

class WorkspaceError(OpenClawRuntimeError):
    """Raised when a workspace operation fails."""
    pass

class PreviewError(OpenClawRuntimeError):
    """Raised when a preview provider operation fails."""
    pass

class ProcessError(OpenClawRuntimeError):
    """Raised when a process execution management operation fails."""
    pass
