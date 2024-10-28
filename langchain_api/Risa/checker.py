import os
from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langserve import add_routes

from dotenv import load_dotenv
load_dotenv()
OPENAI_KEY = os.getenv('OPENAI_API')

app = FastAPI(
    title="test_langserve_server"
)


llm = ChatOpenAI(model='gpt-4o-mini', api_key=OPENAI_KEY)
prompt = ChatPromptTemplate.from_template("tell me a joke about {topic}")
add_routes(
    app,
    prompt | llm,
    path="/joke",
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)