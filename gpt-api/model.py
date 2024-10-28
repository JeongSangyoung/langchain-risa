import re
import os
import time
import json
import asyncio

import openai
from dotenv import load_dotenv
from openai import OpenAI

from prompt import Prompt, NamePrompt, RisaPROMPT

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API')

def modelConfig(model, meg, level, request_timeout):
    generate_configure = {}
    generate_configure["messages"] = meg
    generate_configure["temperature"] = level
    generate_configure["timeout"] = request_timeout
    generate_configure["response_format"] = {"type": "json_object"}
    if model == "gpt-3.5-turbo":
        generate_configure["model"] = "gpt-3.5-turbo-1106"
    elif model == "gpt-4":
        generate_configure["model"] = "gpt-4-1106-preview"
    elif model == "gpt-4o":
        generate_configure["model"] = "gpt-4o"
    elif model == "gpt-4o-mini":
        generate_configure["model"] = "gpt-4o-mini"
    else:
        generate_configure["model"] = "gpt-4o-mini"
    return generate_configure

class GPT:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def gptGenerateOptions(self, model: str, usage: str, description: str):
        request_timeout = 180
        prompt_formatted = Prompt.BRAND["prompt"].format(
            usage=usage,
            description=description,
            categories=Prompt.BRAND["category"],
        )

        meg = [{"role": "user", "content": prompt_formatted}]
        generate_config = modelConfig(model, meg, 1, request_timeout)
        del generate_config["temperature"]
        answer_res = self.client.chat.completions.create(**generate_config)
        answer = answer_res.choices[0].message.content
        return json.loads(answer)

    def gptGenerateNamesWithStream(
            self,
            usage: str,
            description: str,
            category: str,
            tone: list,
            seed: list,
            target: list,
            trend: list,
            language: list,
            brandNames: list,
            level: float,
            model: str,
    ):
        request_timeout = 180
        prompt_formatted = NamePrompt.NAIMY_PROMPT.format(
            usage=usage,
            description=description,
            category=category,
            tones=", ".join(tone),
            # seeds=", ".join(seed),
            targets=", ".join(target),
            trends=", ".join(trend),
            languages=", ".join(language),
            brandNames=", ".join(brandNames),
        )

        meg = [{"role": "user", "content": prompt_formatted}]
        generate_config = modelConfig(model, meg, 1, request_timeout)

        answer_stream = self.client.chat.completions.create(**generate_config, stream=True)

        for chunk in answer_stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

class RisaGPT:
    def __init__(self, chat_model="gpt-4o-mini"):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.chat_model = chat_model

    def create(self, content):
        meg = [{"role": "user", "content": content}]
        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=meg,
            temperature=0
        )
        return response.choices[0].message.content

    async def gpt_create(self, content):
        meg = [{"role": "user", "content": content}]
        max_retries = 10
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.chat_model, messages=meg, top_p=0.1
                )
                return response
            except openai.error.RateLimitError as e:
                print(f"Rate limit error: {e}. Retrying in 10 seconds...")
                await asyncio.sleep(10)
            except Exception as e:
                print(f"Unexpected error: {e}. Retrying in 10 seconds...")
                await asyncio.sleep(10)
        raise Exception(f"Failed to get response after {max_retries} attempts")

class RisaBrandGPT(RisaGPT):
    async def async_answer(self, prompt_list):
        tasks = [self.gpt_create(prompt) for prompt in prompt_list]
        responses = await asyncio.gather(*tasks)
        # responses가 객체일 수 있으니 속성으로 접근
        return [response.choices[0].message.content for response in responses]

    async def get_report(self, prompt_list):
        return await self.async_answer(prompt_list)