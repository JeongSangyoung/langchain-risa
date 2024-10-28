import os
import asyncio

from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langserve import add_routes

from dotenv import load_dotenv
from prompt import (
    PROMPT_MORPHEME, PROMPT_NORMAL, 
    PROMPT_CONCEPT, PROMPT_PROPERTY, 
    PROMPT_SIMPLE, PROMPT_FAMOUS
)

load_dotenv()

OPENAI_KEY = os.getenv('OPENAI_API')


app = FastAPI(
    title="test_langserve_server",
    version="0.0.1",
    description="간단맨"
)
llm = ChatOpenAI(model='gpt-4o-mini', api_key=OPENAI_KEY)

add_routes(
    app,
    llm,
    path="/openai"
)

brand_name = "딸배헌터"
description = "정의로운 영웅",
category = "IT, 인터넷",

def call_tokenizer(brand_name, description, category):
    prompt_morpheme = ChatPromptTemplate.from_template(PROMPT_MORPHEME)

    chain = prompt_morpheme | llm | { "result": StrOutputParser() }

    for chunk in chain.stream({
        "brand_name": brand_name,
        "description": description,
        "category": category,
    }):
        print(chunk)
    

async def call_expert(expert_name, morpheme, brand_name, category):
    if expert_name == '보통명칭':
        prompt_expert = ChatPromptTemplate.from_template(PROMPT_NORMAL)
    elif expert_name == '관념분석':
        prompt_expert = ChatPromptTemplate.from_template(PROMPT_CONCEPT)
    elif expert_name == '성질분석':
        prompt_expert = ChatPromptTemplate.from_template(PROMPT_PROPERTY)
    elif expert_name == '간단명칭':
        prompt_expert = ChatPromptTemplate.from_template(PROMPT_SIMPLE)
    elif expert_name == '유명명칭':
        prompt_expert = ChatPromptTemplate.from_template(PROMPT_FAMOUS)

    chain = prompt_expert | llm | { "result": StrOutputParser() }

    async for event in chain.stream({
        "brand_name": brand_name,
        "description": description,
        "category": category,
    }, version='v2'):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            print(event, end="|", flush=True)
            
    return chain.invoke({
        "brand_name": brand_name,
        "morpheme": morpheme,
        "category": category,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)