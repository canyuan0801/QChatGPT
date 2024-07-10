from __future__ import annotations

import typing
import enum
import pydantic

import mirai


class FunctionCall(pydantic.BaseModel):
    name: str

    arguments: str


class ToolCall(pydantic.BaseModel):
    id: str

    type: str

    function: FunctionCall


class ImageURLContentObject(pydantic.BaseModel):
    url: str

    def __str__(self):
        return self.url[:128] + ('...' if len(self.url) > 128 else '')


class ContentElement(pydantic.BaseModel):

    type: str
    """内容类型"""

    text: typing.Optional[str] = None

    image_url: typing.Optional[ImageURLContentObject] = None

    def __str__(self):
        if self.type == 'text':
            return self.text
        elif self.type == 'image_url':
            return f'[图片]({self.image_url})'
        else:
            return '未知内容'

    @classmethod
    def from_text(cls, text: str):
        return cls(type='text', text=text)

    @classmethod
    def from_image_url(cls, image_url: str):
        return cls(type='image_url', image_url=ImageURLContentObject(url=image_url))


class Message(pydantic.BaseModel):
    """消息"""

    role: str  # user, system, assistant, tool, command, plugin
    """消息的角色"""

    name: typing.Optional[str] = None
    """名称，仅函数调用返回时设置"""

    content: typing.Optional[list[ContentElement]] | typing.Optional[str] = None
    """内容"""

    tool_calls: typing.Optional[list[ToolCall]] = None
    """工具调用"""

    tool_call_id: typing.Optional[str] = None

    def readable_str(self) -> str:
        if self.content is not None:
            return str(self.role) + ": " + str(self.get_content_mirai_message_chain())
        elif self.tool_calls is not None:
            return f'调用工具: {self.tool_calls[0].id}'
        else:
            return '未知消息'

    def get_content_mirai_message_chain(self, prefix_text: str="") -> mirai.MessageChain | None:
        """将内容转换为 Mirai MessageChain 对象
        
        Args:
            prefix_text (str): 首个文字组件的前缀文本
        """

        if self.content is None:
            return None
        elif isinstance(self.content, str):
            return mirai.MessageChain([mirai.Plain(prefix_text+self.content)])
        elif isinstance(self.content, list):
            mc = []
            for ce in self.content:
                if ce.type == 'text':
                    mc.append(mirai.Plain(ce.text))
                elif ce.type == 'image_url':
                    if ce.image_url.url.startswith("http"):
                        mc.append(mirai.Image(url=ce.image_url.url))
                    else:  # base64
                        
                        b64_str = ce.image_url.url

                        if b64_str.startswith("data:"):
                            b64_str = b64_str.split(",")[1]

                        mc.append(mirai.Image(base64=b64_str))
            
            # 找第一个文字组件
            if prefix_text:
                for i, c in enumerate(mc):
                    if isinstance(c, mirai.Plain):
                        mc[i] = mirai.Plain(prefix_text+c.text)
                        break
                else:
                    mc.insert(0, mirai.Plain(prefix_text))

            return mirai.MessageChain(mc)
