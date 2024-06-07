import json
import re
import traceback
from collections import UserList


class ChatMessage(dict):
    @property
    def role(self) -> str:
        return self["role"]

    @property
    def content(self) -> str:
        return self["content"]

    # def __hash__(self) -> int:
    #     return hash((self.role, self.content))

    # def __reduce__(self):
    #     return json.dumps(self.data)


class SystemMessage(ChatMessage):
    def __init__(self, content: str):
        super().__init__(role="system", content=content)


class UserMessage(ChatMessage):
    def __init__(self, content: str):
        super().__init__(role="user", content=content)


class AssistantMessage(ChatMessage):
    def __init__(self, content: str):
        super().__init__(role="assistant", content=content)


json_regex = re.compile(r"(?<!\\)[\[{\"}\]]")
closing = {"{": "}", "[": "]", '"': '"'}


def fix_truncated_json(content: str) -> dict:
    try:
        if content.endswith("}"):
            return json.loads(content)
        else:
            return json.loads(content + "}")
    except Exception:
        traceback.print_exc()

    in_quotes = False
    stack = []
    for m in json_regex.finditer(content):
        char = m.group(0)
        match char:
            case '"':
                in_quotes = not in_quotes
                if in_quotes:
                    stack.append(char)
                elif stack[-1] == '"':
                    stack.pop()
                else:
                    raise ValueError("Unbalanced quotes")
            case _ if in_quotes:
                continue
            case "[":
                stack.append(char)
            case "{":
                stack.append(char)
            case "]":
                if stack[-1] == "[":
                    stack.pop()
                else:
                    raise ValueError("Unbalanced brackets")
            case "}":
                if stack[-1] == "{":
                    stack.pop()
                else:
                    raise ValueError("Unbalanced brackets")

    # if not "textual-references-to-personal-information" in content:
    #     idx = max(m.span(0)[0] for m in re.finditer(r"(,)", content))
    #     content = content[:idx] + ', "output-was-trucated": true}'

    else:
        for c in reversed(stack):
            content += closing[c]
    return json.loads(content)


class HashableMessages(UserList[ChatMessage]):
    def __reduce__(self):
        return json.dumps(self.data)
