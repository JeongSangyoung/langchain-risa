import json
import asyncio
import requests
import reflex as rx

def format_to_markdown(response):
    body = response
    # 기본 정보 추출    
    brand_name = body.split("BrandName: ")[1].split("\n")[0].strip()
    category = body.split("Category: ")[1].split("\n")[0].strip()

    # 간이 결과 추출
    simple_results = body.split("간이 결과")[1].split("상세 결과")[0].strip()
    simple_results = simple_results.replace("\n", "<br>").strip()

    # 상세 결과 추출
    detailed_results = body.split("상세 결과")[1].strip()
    detailed_results = detailed_results.replace("\n", "<br>").strip()

    # Markdown 포맷팅
    markdown_text = f"""
**Brand Name**: {brand_name}  
**Category**: {category}

### 간이 결과
{simple_results}

### 상세 결과
{detailed_results}
    """
    
    return markdown_text.strip()


class RisaState(rx.State):
    input_brandname: str
    input_category: str

    message: str

    running: bool = False

    def initState(self):
        print('')

    def runs(self):
        if self.running:
            self.running = False
        return RisaState.streamTask()

    @rx.background
    async def streamTask(self):
        async with self:
            self.running = True
        async with self:
            await asyncio.sleep(0.7)
        try:

            async with self:
                url = 'http://127.0.0.1:5001/risa'
                data = {
                    'brand_name': self.input_brandname,
                    'category': self.input_category
                }

                response = requests.post(url, json=data)
                response.encoding = 'utf-8'

                self.message = format_to_markdown(response.text)
            
            async with self:
                self.running = False
        except Exception as e:
            print('ERr!', e)
            async with self:
                self.message = str(e)
                self.running = False


@rx.page(route="/risa", title="리사", on_load=RisaState.initState)
def risa() -> rx.Component:
    return rx.flex(
        rx.container(
            rx.flex(
                rx.text('브랜드명 :', width='120px'),
                rx.input(
                    value=RisaState.input_brandname,
                    on_change=RisaState.set_input_brandname,
                    placeholder="Brand name",
                    size="3",
                    width="300px"
                ),
                align="center"
            ),
            rx.flex(
                rx.text('카테고리 :', width='120px'),
                rx.input(
                    value=RisaState.input_category,
                    on_change=RisaState.set_input_category,
                    placeholder="Category",
                    size="3",
                    width="300px"
                ),
                align="center",
                margin_top="16px",
                margin_bottom="16px",
            ),
            
            rx.flex(
                rx.button(
                    rx.cond(
                        ~RisaState.running, 
                        rx.text("형태소분석 TEST"),
                        rx.spinner(size="3"),
                    ),
                    disabled=rx.cond(RisaState.running, True, False),
                    on_click=RisaState.runs,
                    _hover={
                        "cursor": "pointer"
                    },
                    size="3",
                    color_scheme="teal",
                ),
                rx.button(
                    rx.cond(
                        ~RisaState.running, 
                        rx.text("보통명칭 TEST"),
                        rx.spinner(size="3"),
                    ),
                    disabled=rx.cond(RisaState.running, True, False),
                    on_click=RisaState.runs,
                    _hover={
                        "cursor": "pointer"
                    },
                    size="3",
                    color_scheme="tomato",
                ),
                gap="12px",
            ),


            rx.cond(
                RisaState.message,
                rx.card(
                    rx.html(RisaState.message),
                    margin_top='48px'
                ),
            )
        ),
        background_color=rx.color("brown", 8),
        min_height="100vh",
        align="center",
        padding_top="64px",
        padding_bottom="64px"
    )
