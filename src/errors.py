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


class AuraException(Exception):
    def __init__(self, *args: object):
        super().__init__(args)

    pass


class AlreadyInitializedException(AuraException):
    def __init__(self, message="The setup is already initialized."):
        self.message = message
        super().__init__(self.message)


class RequireInitializedException(AuraException):
    def __init__(self, message="The setup needs to be initialized. Run the init command."):
        self.message = message
        super().__init__(self.message)


class CannotRunOnThisEnviromentException(AuraException):
    def __init__(self, message="You cannot run this command on this enviroment."):
        self.message = message
        super().__init__(self.message)


class RequireDatabaseServiceException(AuraException):
    def __init__(self, message="The database service needs to be running and healthy."):
        self.message = message
        super().__init__(self.message)


class EnviromentAlreadyExistException(AuraException):
    def __init__(self, message="This environment already exist!"):
        self.message = message
        super().__init__(self.message)


class EnviromentNotExistException(AuraException):
    def __init__(self, message="This environment does not exist!"):
        self.message = message
        super().__init__(self.message)
