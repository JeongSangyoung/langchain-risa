#!/bin/bash

# 가상 환경 활성화
source .venv/bin/activate

# gpt_api 디렉토리로 이동하여 앱 실행
cd gpt_api
nohup python app.py &

# llm_api 디렉토리로 이동하여 앱 실행
cd ../llm_api
nohup python app.py &

# UI 디렉토리로 이동하여 앱 실행
cd ../UI
nohup reflex run --env prod &