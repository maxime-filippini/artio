class MissingTypeHintInWorkflowComponentError(Exception):
    pass


class NonAnnotatedArgumentInWorkflowComponentError(Exception):
    def __init__(self, arg: str) -> None:
        super().__init__(arg)


class ArgumentDependsOnNonExistentComponentError(Exception):
    pass


class ArgumentMissingSourceInformation(Exception):
    pass


class InputRequiresInputModelError(Exception):
    pass


class UnknownWorkflowInputError(Exception):
    pass


class InvalidWorkflowInputModelError(TypeError):
    pass


class InvalidWorkflowRunInputsError(TypeError):
    pass
