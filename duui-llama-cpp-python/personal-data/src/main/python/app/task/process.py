from dataclasses import dataclass
from typing import Final

from app.task.chat import ChatMessage
from app.task.model import LlamaRequest, TaskSpecificResponse
from app.task.query import AdvancedQueryRunner, QueryRunner, SimpleQueryRunner
from app.task.schema import (
    EnglishAdvancedSchema,
    EnglishSimpleSchema,
    GermanAdvancedSchema,
    GermanSimpleSchema,
)
from fastapi import Depends
from llama_cpp import Llama
from llama_cpp.server.app import get_llama_proxy

SystemPromptEnglish: Final[str] = (
    """You are an assistant for the anonymization of text data.
You receive texts from different sources and in different formats and languages.
Under no circumstances may these texts contain information that could be used to identify the author of the text, e.g. names, addresses, telephone numbers or e-mail addresses."""
)

SimpleAnonymizationSchemaEnglish: Final[EnglishSimpleSchema] = EnglishSimpleSchema(
    system=SystemPromptEnglish,
    prefix="Given the following text:",
    suffix="Tell me the location in the text where a person is identified by a name.",
)

AdvancedInstructionsEnglish: Final[str] = (
    """First answer "Yes" or "No", depending on whether the text contains personal information.

If the text contains personal information:

1. briefly describe what type of personal information is contained in the text.
2. provide a list of text passages or references to text passages that contain the personal information."""
)

AdvancedAnonymizationSchemeEnglish: Final[EnglishAdvancedSchema] = (
    EnglishAdvancedSchema(
        system=f"""{SystemPromptEnglish}\n\n{AdvancedInstructionsEnglish}""",
        text_contains_pi="Does the text above contain personal information?",
        text_contains_pi_yes="Yes, the text contains personal information.",
        description_of_pi="Provide a description of the personal information in the text above.",
        details_of_pi_as_json="Provide a list of references to the personal information in the text above as JSON.",
    )
)

SystemPromptGerman: Final[str] = (
    """Du bist ein Assistent für die Anonymisierung von Textdaten.
Du erhälst Texte aus verschiedenen Quellen und in verschiedenen Formaten oder Sprachen.
Diese Texte dürfen auf keinen Fall personenbezogene Daten oder Informationen enthalten, die zur Identifizierung des Verfassers des Textes verwendet werden könnten; z. B. Namen, Adressen, Telefonnummern oder E-Mail-Adressen."""
)

SimpleAnonymizationSchemaGerman: Final[GermanSimpleSchema] = GermanSimpleSchema(
    system=SystemPromptGerman,
    prefix="Gegeben den Text:",
    suffix="Nenne mir die Stelle in dem Text, an der eine Person durch einen Namen identifiziert wird.",
)

AdvancedInstructionsGerman: Final[str] = (
    """Antworte zunächst mit "Ja" oder "Nein", je nachdem, ob der Text personenbezogene Daten oder Informationen enthält.

Wenn der Text personenbezogene Daten oder Informationen enthält:

1. Beschreibe kurz, welche Art von persönlichen Informationen in dem Text enthalten sind.
2. Gebe eine Liste von Textpassagen oder Verweisen auf Textpassagen an, welche die persönlichen Informationen enthalten."""
)

AdvancedAnonymizationSchemeGerman: Final[GermanAdvancedSchema] = GermanAdvancedSchema(
    system=f"""{SystemPromptGerman}\n\n{AdvancedInstructionsGerman}""",
    text_contains_pi="Enthält der Text personenbezogene Daten oder Informationen?",
    text_contains_pi_yes="Ja, der Text enthält personenbezogene Daten oder Informationen.",
    description_of_pi="Beschreibe kurz, welche Art von persönlichen Informationen in dem Text enthalten sind.",
    details_of_pi_as_json="Gebe eine Liste von Textpassagen oder Verweisen auf Textpassagen an, welche die persönlichen Informationen enthalten, im JSON-Format.",
)

token_lookup: dict[str, dict[str, tuple[int, ...]]] = {}


def llama_token_lookup(llama: Llama) -> dict[str, tuple[int, ...]]:
    global token_lookup

    key = llama.model_path
    if key in token_lookup:
        return token_lookup[key]
    tokens = {
        tk: tuple(
            llama.tokenize(
                tk.encode(),
                add_bos=False,
                special=False,
            )
        )
        for tk in (
            "Ja",
            "ja",
            "Nein",
            "nein",
            "no",
            "No",
            "Yes",
            "yes",
        )
    }
    token_lookup[key] = tokens
    return tokens


@dataclass
class LlamaQuery(QueryRunner):
    llama: Llama

    def query(self, messages: list[ChatMessage], **kwargs) -> str:
        return self.get_response_text(
            self.llama.create_chat_completion(
                messages=messages,
                **kwargs,
            )
        )

    def token_to_ids(self, token: str) -> tuple[int, ...]:
        return llama_token_lookup(self.llama).get(token, ())


class SimpleLlamaQueryRunner(LlamaQuery, SimpleQueryRunner):
    pass


class AdvancedLlamaQueryRunner(LlamaQuery, AdvancedQueryRunner):
    pass


async def task_specific_process(
    body: LlamaRequest,
    llama_proxy=Depends(get_llama_proxy),
) -> TaskSpecificResponse:
    match body.language, body.variant:
        case "en", "simple":
            query = SimpleLlamaQueryRunner(llama_proxy(body.model))
            response = query.run(SimpleAnonymizationSchemaEnglish, body.text)
            return TaskSpecificResponse(response=response)
        case "en", "advanced":
            query = AdvancedLlamaQueryRunner(llama_proxy(body.model))
            response = query.run(AdvancedAnonymizationSchemeEnglish, body.text)
            return TaskSpecificResponse(response=response)
        case "de", "simple":
            query = SimpleLlamaQueryRunner(llama_proxy(body.model))
            response = query.run(SimpleAnonymizationSchemaGerman, body.text)
            return TaskSpecificResponse(response=response)
        case "de", "advanced":
            query = AdvancedLlamaQueryRunner(llama_proxy(body.model))
            response = query.run(AdvancedAnonymizationSchemeGerman, body.text)
            return TaskSpecificResponse(response=response)
        case _:
            raise ValueError(
                "Unsupported variant or language! Supported languages: 'en', 'de'; Supported variants: 'simple', 'advanced'"
            )
