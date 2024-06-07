from abc import abstractmethod

from app.task.chat import ChatMessage, SystemMessage, UserMessage


class BasePromptSchema:
    def __init__(
        self,
        system: str,
        token_yes: str | None = None,
        token_no: str | None = None,
        **kwargs,
    ) -> None:
        self.system = system
        self.token_yes = token_yes
        self.token_no = token_no

    @abstractmethod
    def initial(self, text: str) -> list[ChatMessage]: ...

    # def __getattribute__(self, name: str):
    #     return self.get(name, None) or super().__getattribute__(name)

    def tokens(self) -> tuple[str, ...]:
        tokens = (tk for tk in (self.token_yes, self.token_no) if tk is not None)
        return tuple(tokens)

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class EnglishSchemaMixin:
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("token_yes", "Yes")
        kwargs.setdefault("token_no", "No")
        super().__init__(*args, **kwargs)


class GermanSchemaMixin:
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("token_yes", "Ja")
        kwargs.setdefault("token_no", "Nein")
        super().__init__(*args, **kwargs)


class SimplePromptSchema(BasePromptSchema):

    def __init__(
        self,
        system: str,
        prefix: str,
        suffix: str,
        token_yes: str | None = None,
        token_no: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(system, token_yes=token_yes, token_no=token_no, **kwargs)
        self.prefix = prefix
        self.suffix = suffix

    def initial(self, text: str) -> list[ChatMessage]:
        return [
            SystemMessage(self.system),
            UserMessage("\n".join([self.prefix, text.strip(), self.suffix])),
        ]


class EnglishSimpleSchema(EnglishSchemaMixin, SimplePromptSchema):
    pass


class GermanSimpleSchema(GermanSchemaMixin, SimplePromptSchema):
    pass


class AdvancedPromptSchema(BasePromptSchema):
    def __init__(
        self,
        system: str,
        text_contains_pi: str,
        text_contains_pi_yes: str,
        description_of_pi: str,
        details_of_pi_as_json: str,
        token_yes: str | None = None,
        token_no: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(system, token_yes=token_yes, token_no=token_no, **kwargs)
        self.text_contains_pi = text_contains_pi
        self.text_contains_pi_yes = text_contains_pi_yes
        self.description_of_pi = description_of_pi
        self.details_of_pi_as_json = details_of_pi_as_json

    def initial(self, text: str) -> list[ChatMessage]:
        return [
            SystemMessage(self.system),
            UserMessage(text.strip()),
            UserMessage(self.text_contains_pi),
        ]


class EnglishAdvancedSchema(EnglishSchemaMixin, AdvancedPromptSchema):
    pass


class GermanAdvancedSchema(GermanSchemaMixin, AdvancedPromptSchema):
    pass
