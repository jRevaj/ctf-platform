class CTFBaseException(Exception):
    """Base exception for all CTF-related errors"""
    pass


class DockerOperationError(CTFBaseException):
    """Raised when a Docker operation fails"""
    pass


class ContainerOperationError(CTFBaseException):
    """Raised when a container operation fails"""
    pass


class ContainerNotFoundError(ContainerOperationError):
    """Raised when a container is not found"""
    pass


class ContainerStateError(ContainerOperationError):
    """Raised when container is in invalid state for operation"""
    pass
