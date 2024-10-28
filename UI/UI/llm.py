import asyncio
import requests
import reflex as rx

def displayResult(result: tuple[str, list[str]]):
    title = result[0]
    options = result[1]
    items = result[2]
    return rx.card(
        rx.hstack(
            rx.heading(title, size="4", margin_bottom="4px"),
            rx.text(f'{options[0]}/{options[1]}/{options[2]}/{options[3]}', size="2"),
        ),
        rx.flex(
            rx.foreach(
                items,
                lambda x: rx.box(
                    x,
                    border="1px solid #111111",
                    padding="4px 8px",
                    borderRadius="4px",
                    background="#eeeeee",
                    font_weight="500",
                    font_size="14px",
                    color="#000000",
                ),
            ),
            spacing="2",
            flex_wrap="wrap",
        ),
    )

class LLmState(rx.State):
    inputs: str
    running: bool = False
    progress: int = 0

    results: list[tuple[str, list[int, float, int, float], list[str]]]

    opt_num_return_sequences: int = 10
    opt_temperature: float = 0.8
    opt_top_k: int = 200
    opt_top_p: float = 0.9

    device: str = "..."

    def initState(self):
        url = 'http://127.0.0.1:5000/isgpu'
        response = requests.get(url).json()
        if response['status']:
            self.device = response['data']
        
        self.opt_num_return_sequences = 10
        self.opt_temperature = 0.8
        self.opt_top_k = 200
        self.opt_top_p = 0.9
        self.progress = 0
        self.running = False

    @rx.background
    async def streamTask(self):
        async with self:
            self.running = True

        async with self:
            self.progress += 50

            url = 'http://127.0.0.1:5000/generate'
            data = {
                'word': self.inputs,
                'option_num': self.opt_num_return_sequences,
                'option_temperature': self.opt_temperature,
                'option_top_k': self.opt_top_k,
                'option_top_p': self.opt_top_p,
            }
        
        async with self:
            response = requests.post(url, data=data).json()
            status = response["status"]
            await asyncio.sleep(0.7)
            self.progress += 50
            if not status:
                raise

            data = response["data"]
            self.results.append((
                self.inputs, 
                [
                    self.opt_num_return_sequences,
                    self.opt_temperature,
                    self.opt_top_k,
                    self.opt_top_p,
                ],
                data
            ))

        await asyncio.sleep(0.7)
    
        async with self:
            self.running = False
            
    def keyDown(self, k):
        if k == 'Enter':
            if self.progress >= 100:
                self.progress = 0
            if self.running:
                self.running = False
            return LLmState.streamTask()
    
    def toggleRunning(self):
        if self.progress >= 100:
            self.progress = 0
        if self.running:
            self.running = False
        return LLmState.streamTask()

    def setOptNum(self, value: list[int]):
        self.opt_num_return_sequences = value[0]
    
    def setOptTemperature(self, value: list[float]):
        self.opt_temperature = value[0]
    
    def setOptTopK(self, value: list[int]):
        self.opt_top_k = value[0]

    def setOptTopP(self, value: list[float]):
        self.opt_top_p = value[0]

    def removeItems(self):
        self.results.clear()
    

@rx.page(route="/llm", title="상표명 생성 프로그램", on_load=LLmState.initState)
def llm() -> rx.Component:
    return rx.flex(
        rx.container(
            rx.flex(
                rx.button(
                    "검색식 생성 바로가기",
                    color_scheme="brown",
                    margin_bottom="20px",
                    on_click=rx.redirect(
                        "/"
                    ),
                    cursor="pointer",
                ),
                rx.button(
                    "네이미 최적화 바로가기",
                    color_scheme="brown",
                    margin_bottom="20px",
                    on_click=rx.redirect(
                        "/naimy"
                    ),
                    cursor="pointer",
                ),
                spacing="2",
            ),

            rx.hstack(
                rx.text("GPU"),
                rx.text(LLmState.device),
            ),
            rx.heading("시드단어 중심으로 상표명 생성하는 프로그램"),
            rx.hstack(
                rx.input(
                    value=LLmState.inputs,
                    on_change=LLmState.set_inputs,
                    on_key_down=LLmState.keyDown,
                    placeholder="시드단어 입력",
                    max_length=20,
                    size="3"
                ),
                rx.button(
                    rx.cond(
                        ~LLmState.running, 
                        rx.text("Generate"),
                        rx.spinner(size="3"),
                    ),
                    disabled=rx.cond(LLmState.running, True, False),
                    on_click=LLmState.toggleRunning,
                    _hover={
                        "cursor": "pointer"
                    },
                    size="3",
                ),
                margin_top="24px",
            ),
            rx.card(
                rx.heading(
                    "● 생성할 상표 갯수 : ",
                    LLmState.opt_num_return_sequences,
                    size="3",
                ),
                rx.slider(
                    default_value=10,
                    step=1,
                    min=5,
                    max=30,
                    on_change=LLmState.setOptNum,
                    variant="soft",
                    color_scheme="ruby",
                    margin_top="8px",
                ),

                rx.heading(
                    "● Temperature - 값이 높을수록 다양한 결과 생성 : ",
                    LLmState.opt_temperature,
                    size="3",
                    margin_top="16px",
                ),
                rx.slider(
                    default_value=0.8,
                    step=0.01,
                    min=0.01,
                    max=1.00,
                    on_change=LLmState.setOptTemperature,
                    variant="soft",
                    color_scheme="violet",
                    margin_top="8px",
                    radius="small",
                ),

                rx.heading(
                    "● top_k - 상위 k개 단어만 샘플링에 사용 : ",
                    LLmState.opt_top_k,
                    size="3",
                    margin_top="16px",
                ),
                rx.slider(
                    default_value=200,
                    step=10,
                    min=100,
                    max=500,
                    on_change=LLmState.setOptTopK,
                    variant="soft",
                    color_scheme="teal",
                    margin_top="8px",
                ),

                rx.heading(
                    "● top_p - 누적 확률이 p 이하인 단어들만 샘플링에 사용 : ",
                    LLmState.opt_top_p,
                    size="3",
                    margin_top="16px",
                ),
                rx.slider(
                    default_value=0.9,
                    step=0.01,
                    min=0.01,
                    max=1.00,
                    on_change=LLmState.setOptTopP,
                    variant="soft",
                    color_scheme="bronze",
                    margin_top="8px",
                    radius="small",
                    margin_bottom="12px",
                ),

                margin_top="32px",
                max_width="500px",
                width="100%"
            ),

            rx.cond(
                LLmState.running,
                rx.progress(
                    value=LLmState.progress,
                    max=100,
                    radius="full",
                    color_scheme="indigo",
                    margin_top="32px",
                ),
            ),

            rx.cond(
                LLmState.results,
                rx.box(
                    rx.flex(
                        rx.heading("결과"),
                        rx.icon(
                            "trash-2",
                        ),
                        justify="between",
                        margin_top="48px", 
                        margin_bottom="12px",
                        align="center",
                        cursor="pointer",
                        on_click=LLmState.removeItems
                    ),
                    rx.card(
                        rx.flex(
                            rx.foreach(
                                LLmState.results,
                                displayResult,
                            ),
                            spacing="2",
                            direction="column-reverse",
                        )
                    ),
                )
            )
        ),
        background_color=rx.color("tomato", 8),
        min_height="100vh",
        align="center",
        padding_top="64px",
        padding_bottom="64px"
    )
