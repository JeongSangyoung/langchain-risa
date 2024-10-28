import os
from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv
from prompt import (
    PROMPT_MORPHEME, PROMPT_NORMAL, 
    PROMPT_CONCEPT, PROMPT_PROPERTY, 
    PROMPT_SIMPLE, PROMPT_FAMOUS
)

load_dotenv()

OPENAI_KEY = os.getenv('OPENAI_API')
from fastapi.responses import RedirectResponse
from langserve import add_routes

app = FastAPI(
    title="LangChain Server",
    version="1.0",
    description="A simple api server using Langchain's Runnable interfaces",
)
llm = ChatOpenAI(model='gpt-4o-mini', api_key=OPENAI_KEY)


@app.get("/morpheme")
def call_tokenizer(brand_name, description, category):
    prompt_morpheme = ChatPromptTemplate.from_template(PROMPT_MORPHEME)

    chain = prompt_morpheme | llm | { "result": StrOutputParser() }

    for chunk in chain.stream({
        "brand_name": brand_name,
        "description": description,
        "category": category,
    }):
        print(chunk)

add_routes(
    app,
           
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
