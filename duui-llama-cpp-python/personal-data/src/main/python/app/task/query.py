import json
import traceback
from abc import abstractmethod

from app.task.chat import AssistantMessage, ChatMessage, UserMessage, fix_truncated_json
from app.task.schema import AdvancedPromptSchema, BasePromptSchema, SimplePromptSchema
from pydantic import BaseModel


class QueryRunner[T_response: BaseModel]:
    @abstractmethod
    def query(self, messages: list[ChatMessage], **kwargs) -> str: ...

    @abstractmethod
    def run(self, schema: BasePromptSchema, text: str) -> T_response: ...

    @abstractmethod
    def token_to_ids(self, token: str) -> tuple[int, ...]: ...

    def logit_bias(self, schema: BasePromptSchema) -> dict[int, float]:
        return {
            tk: 10.0 for token in schema.tokens() for tk in self.token_to_ids(token)
        }

    def get_response_text(self, response) -> str:
        if hasattr(response, "choices"):
            response_text: str = response.choices[0].message.content.strip()
        else:
            response_text: str = response["choices"][0]["message"]["content"].strip()
        return response_text


class SimpleResponse(BaseModel):
    description: str


class SimpleQueryRunner(QueryRunner[SimpleResponse]):
    def run(self, schema: SimplePromptSchema, text: str):
        try:
            response_text = self.query(
                schema.initial(text),
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
            return SimpleResponse(description=response_text)
        except Exception as e:
            raise e


class AdvancedResponse(BaseModel):
    contains_personal_information: bool
    description: str
    details: dict


class AdvancedQueryRunner(QueryRunner[AdvancedResponse]):
    def run(self, schema: AdvancedPromptSchema, text: str):
        try:
            messages = schema.initial(text)

            response_text: str = self.query(
                messages,
                logit_bias=self.logit_bias(schema),
                max_tokens=64,
                # logprobs=True,
                # top_logprobs=8,
                temperature=0.0,
            )

            if schema.token_yes.lower() not in response_text.lower():
                return AdvancedResponse(
                    contains_personal_information=False,
                    description=response_text,
                    details={},
                )

            messages += [
                AssistantMessage(schema.text_contains_pi_yes),
                UserMessage(schema.description_of_pi),
            ]
            description_content = self.query(
                messages,
                max_tokens=512,
            )

            messages += [
                AssistantMessage(description_content),
                UserMessage(schema.details_of_pi_as_json),
            ]
            references_content = self.query(
                messages,
                max_tokens=512,
                response_format={"type": "json_object"},
            )

            try:
                references_content = json.loads(references_content)
            except Exception:
                traceback.print_exc()
                try:
                    references_content = fix_truncated_json(references_content)
                except Exception as e:
                    raise ValueError(
                        "Failed to parse JSON from detailed response"
                    ) from e

            return AdvancedResponse(
                contains_personal_information=True,
                description=description_content,
                details=references_content,
            )
        except Exception as e:
            raise e
