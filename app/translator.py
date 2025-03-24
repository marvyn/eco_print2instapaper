import logging
import time
from typing import Optional

import openai
from tenacity import retry, stop_after_attempt, wait_exponential


class Translator:
    def __init__(
        self, api_key: str, api_base: Optional[str] = None, model: str = "gpt-4o-mini"
    ):
        self.client = openai.OpenAI(api_key=api_key, base_url=api_base)
        self.model = model
        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry_error_callback=lambda _: None,
    )
    def translate(self, text: str) -> str:
        """翻译文本，支持自动重试"""
        if not text:
            return ""

        self.logger.info(f"Translating: {text}")

        try:
            response = self.client.chat.completions.create(
                model=self.model,  # 使用正确的模型名称
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional translator. Translate the following English text to Simplified Chinese. The text is from The Economist. Maintain the original meaning and style.",
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0.3,
                timeout=30,  # 添加超时设置
            )
            if (
                response
                and response.choices
                and response.choices[0].message
                and response.choices[0].message.content
            ):
                return response.choices[0].message.content.strip()
            return text
        except openai.APITimeoutError:
            self.logger.error("翻译超时，请检查网络连接")
            return f"{text} (翻译超时)"
        except openai.RateLimitError:
            self.logger.error("API 调用频率超限")
            return f"{text} (API 限流)"
        except Exception as e:
            self.logger.error(f"翻译失败: {str(e)}")
            return f"{text} (翻译失败)"

    def translate_article(self, article: dict) -> dict:
        """翻译文章的标题和副标题"""
        translated = article.copy()
        try:
            # 添加延迟避免频繁调用
            time.sleep(1)
            translated["title_zh"] = self.translate(article["title"])

            if article["subtitle"]:
                time.sleep(1)
                translated["subtitle_zh"] = self.translate(article["subtitle"])
            else:
                translated["subtitle_zh"] = ""

            return translated
        except Exception as e:
            self.logger.error(f"文章翻译失败: {str(e)}")
            # 发生错误时返回原文
            return {
                **article,
                "title_zh": f"{article['title']} (翻译失败)",
                "subtitle_zh": f"{article.get('subtitle', '')} (翻译失败)",
            }
