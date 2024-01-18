class ComposeException(Exception):
    pass


class ComposeFileNotFoundException(ComposeException):
    pass


class ServiceAlreadyExistsException(ComposeException):
    pass


class ServiceDoesNotExistException(ComposeException):
    pass


class EnvException(Exception):
    pass


class EnvVarAlreadyExistsException(EnvException):
    pass


class EnvVarDoesNotExistException(EnvException):
    pass


class DatabaseException(Exception):
    pass


class OperationOnDatabaseDeniedException(DatabaseException):
    pass


class DatabaseAlreadyExistsException(DatabaseException):
    pass
