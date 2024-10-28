import json
import asyncio
import requests
import reflex as rx

def displayCard(item: list[str, str, str, list[str]], pending, idx, page=0, count=9):
    brand_kr = item[0]
    brand_en = item[1]
    content = item[2]
    tech = item[3]
    end_cnt = page * count + count
    return rx.cond(
        idx < end_cnt,
        rx.cond(
            pending,
            rx.card(
                rx.flex(
                    rx.spinner(size="3"),
                    justify="center",
                    align="center",
                    height="100%",
                ),
                height="210px",
            ),
            rx.card(
                rx.flex(
                    rx.heading(brand_kr, size="4"),
                    rx.text(
                        f"({brand_en})",
                        color="grey",
                        font_weight="500",
                    ),
                    rx.text(
                        content,
                        font_size="15px",
                        margin_top="8px",
                        color="#111111",
                        text_align="center",
                    ),

                    rx.flex(
                        rx.foreach(
                            tech,
                            lambda y: rx.box(
                                y,
                                color="#1b7bcf",
                                font_size="12px",
                                background="#1b7bcf1a",
                                padding="4px 8px",
                                font_weight="500",
                            )
                        ),
                        spacing="2",
                        margin_top="12px",
                    ),
                    direction="column",
                    align="center",
                ),
                padding="12px",
                min_height="210px"
            ),
        )
    )

class NaimyState(rx.State):
    username: str = "tester"
    auth_complete: bool = False
    login_error: str = ""

    description: str = ""
    running: bool = False
    progress: int = 0
    usage: str = "제품・서비스명"
    model: str = "gpt-4o-mini"
    results: list[list[str, str, str, list[str]]] = []

    history_results: list[list[str, str, str, list[str]]] = []

    pending_cards: list[bool] = [True for _ in range(9)]
    options: list[str, list[str], list[str], list[str], list[str]] = [] # 카테고리, 톤, 타겟, 트렌드, 랭귀지
    first_start: bool = False

    page: int = 0
    history_view_count: int = 8

    prev_username = ""

    def initState(self):
        self.page = 0

    def login(self):
        success, db = self.getDB()
        if success:
            self.auth_complete = True
            self.history_results = db
            if self.username != self.prev_username:
                self.prev_username = self.username
                self.results.clear()
                self.usage = "제품・서비스명"
                self.model = "gpt-4o-mini"
                self.description = ""
                self.page = 0
                self.first_start = False
                self.options.clear()
                self.pending_cards = [True for _ in range(9)]
        else:
            self.login_error = db
    
    def logout(self):
        self.auth_complete = False

    def getDB(self):
        url = 'http://127.0.0.1:5001'
        data = {
            "username": self.username,
            "page": 0,
        }
        response = requests.post(url + '/db/get', json=data)
        if response.status_code == 200:
            return (True, response.json())
        return (False, response.json()["error"])

    def addDB(self, data):
        url = 'http://127.0.0.1:5001'
        body = {
            "username": self.username,
            "items": data,
        }
        requests.post(url + '/db/add', json=body)

    def paginate(self):
        self.page += 1

    def keyDownLogin(self, k):
        if k == 'Enter':
            self.login()

    def keyDownGens(self, k):
        if k == 'Enter':
            if self.progress >= 100:
                self.progress = 0
            if self.running:
                self.running = False
            self.first_start = True
            return NaimyState.streamTask()

    def toggleRunning(self):
        if self.progress >= 100:
            self.progress = 0
        if self.running:
            self.running = False
        self.first_start = True
        return NaimyState.streamTask()

    @rx.background
    async def streamTask(self):
        async with self:
            self.pending_cards = [True for _ in range(9)]
            self.results.clear()
            self.options.clear()
        async with self:
            self.running = True
        async with self:
            self.progress += 5
        
        async with self:
            success, db = self.getDB()
            self.history_results = db
            if success:
                history_names = [h[0] for h in db]
            else:
                history_names = []

        url = 'http://127.0.0.1:5001'
        data = {
            "description": self.description,
            "usage": self.usage,
            "model": self.model
        }
        with requests.post(url + '/options', json=data) as response:
            res = response.json()

        async with self:
            self.options = [res["category"], res["tones"], res["targets"], res["trends"], res["languages"]]
            self.progress += 5
        
        data = {
            "description": self.description,
            "usage": self.usage,
            "model": self.model,
            "category": res["category"],
            "tones": res["tones"],
            "targets": res["targets"],
            "trends": res["trends"],
            "languages": res["languages"],
            "brandNames": history_names,
        }

        temp_result = []
        with requests.post(url + '/generate', json=data, stream=True) as response:
            buffer = ""
            start = False
            open_bracket_start = False
            close_bracket_cnt = 0
            card_idx = 0
            for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
                if not chunk: continue
                if not start and chunk == '[':
                    start = True
                    continue

                if start and not open_bracket_start and chunk == '[':
                    open_bracket_start = True
                
                if open_bracket_start:
                    buffer += chunk
                    if chunk == ']':
                        close_bracket_cnt += 1

                if close_bracket_cnt == 2:
                    open_bracket_start = False
                    close_bracket_cnt = 0
                    async with self:
                        b = json.loads(buffer)
                        self.results.append(b)
                        temp_result.append(b)
                    async with self:
                        self.progress += 10
                        self.pending_cards[card_idx] = False
                    card_idx += 1
                    buffer = ""

        async with self:
            self.running = False
            self.addDB(temp_result)

def authentication():
    return rx.container(
        rx.flex(
            rx.button(
                "검색식 생성 바로가기",
                color_scheme="plum",
                margin_bottom="20px",
                on_click=rx.redirect(
                    "/"
                ),
                cursor="pointer",
            ),
            rx.button(
                "상표명 생성 AI 로 바로가기",
                color_scheme="plum",
                margin_bottom="20px",
                on_click=rx.redirect(
                    "/llm"
                ),
                cursor="pointer",
            ),
            spacing="2",
        ),
        rx.heading("네이미 생성 최적화", margin_bottom="20px"),
        rx.card(
            rx.heading("유저명 입력하세요."),
            rx.input(
                value=NaimyState.username,
                on_change=NaimyState.set_username,
                on_key_down=NaimyState.keyDownLogin,
                placeholder="유저명",
                margin_top="20px",
                width="200px",
            ),
            rx.button(
                "제출",
                on_click=NaimyState.login,
                _hover={
                    "cursor": "pointer"
                },
                size="3",
                margin_top="20px",
                color_scheme="tomato",
            ),
        )
    )

def main():
    return rx.container(
        rx.flex(
            rx.button(
                "검색식 생성 바로가기",
                color_scheme="plum",
                margin_bottom="20px",
                on_click=rx.redirect(
                    "/"
                ),
                cursor="pointer",
            ),
            rx.button(
                "상표명 생성 AI 로 바로가기",
                color_scheme="plum",
                margin_bottom="20px",
                on_click=rx.redirect(
                    "/llm"
                ),
                cursor="pointer",
            ),
            spacing="2",
        ),
        rx.heading("네이미 생성 최적화", margin_bottom="20px"),
        rx.select.root(
            rx.select.trigger(),
            rx.select.content(
                rx.select.group(
                    rx.select.item("GPT-3.5", value="gpt-3.5"),
                    rx.select.item("GPT-4o-mini", value="gpt-4o-mini"),
                    rx.select.item("GPT-4o", value="gpt-4o"),
                    rx.select.item("GPT-4", value="gpt-4", disabled=True),
                ),
            ),
            default_value="gpt-4o-mini",
            value=NaimyState.model,
            on_change=NaimyState.set_model,
        ),
        rx.radio(
            ["제품・서비스명", "상호명", "회사・법인명"],
            direction="row",
            spacing="5",
            size="3",
            margin_top="20px",
            default_value="제품・서비스명",
            on_change=NaimyState.set_usage,
        ),
        rx.input(
            value=NaimyState.description,
            on_change=NaimyState.set_description,
            on_key_down=NaimyState.keyDownGens,
            placeholder="Description",
            margin_top="20px",
            width="500px",
        ),
        rx.flex(
            rx.button(
                rx.cond(
                    ~NaimyState.running,
                    rx.text("Generate"),
                    rx.spinner(size="3"),
                ),
                disabled=rx.cond(NaimyState.running, True, False),
                on_click=NaimyState.toggleRunning,
                _hover={
                    "cursor": "pointer"
                },
                size="3",
                color_scheme="tomato",
            ),
            rx.button(
                "log out",
                on_click=NaimyState.logout,
                color_scheme="gray",
                _hover={
                    "cursor": "pointer"
                },
                size="3",
            ),
            margin_top="20px",
            width="500px",
            justify="between",
            align="center"
        ),

        rx.cond(
            NaimyState.running,
            rx.progress(
                value=NaimyState.progress,
                max=100,
                radius="full",
                color_scheme="indigo",
                margin_top="32px",
            ),
        ),

        rx.cond(
            NaimyState.first_start,
            rx.card(
                rx.cond(
                    NaimyState.options,
                    rx.box(
                        rx.heading("Auto options", size="3"),
                        rx.text(f'category: {NaimyState.options[0]}', margin_top="8px"),
                        rx.text(f'tones: {NaimyState.options[1]}', margin_top="4px"),
                        rx.text(f'targets: {NaimyState.options[2]}', margin_top="4px"),
                        rx.text(f'trends: {NaimyState.options[3]}', margin_top="4px"),
                        rx.text(f'languages: {NaimyState.options[4]}', margin_top="4px"),
                        padding="8px",
                    ),
                    rx.flex(
                        rx.spinner(size="3"),
                        width="100%",
                        justify="center",
                        align="center",
                        height="220px",
                    )
                ),
                width="100%",
                height="220px",
                margin_top="48px",
            ),
            rx.card(
                rx.flex(
                    rx.heading("쉽고 빠른 상표명 생성"),
                    align="center",
                    justify="center",
                    width="100%",
                    height="100%",
                ),
                height="220px",
                width="100%",
                margin_top="48px",
            )
        ),

        rx.cond(
            NaimyState.first_start,
            rx.grid(
                rx.foreach(
                    NaimyState.pending_cards,
                    lambda x, idx: displayCard(
                        NaimyState.results[idx],
                        NaimyState.pending_cards[idx],
                        idx,
                    )
                ),
                flex_wrap="wrap",
                margin_top="48px",
                columns="3",
                spacing="3"
            ),
        ),

        rx.cond(
            NaimyState.history_results,
            rx.box(
                rx.heading("History - 과거기록", margin_top="48px"),
                rx.grid(
                    rx.foreach(
                        NaimyState.history_results,
                        lambda x, idx: displayCard(
                            x, False, idx, NaimyState.page, NaimyState.history_view_count)
                    ),
                    flex_wrap="wrap",
                    margin_top="36px",
                    columns="4",
                    spacing="3"
                ),
                rx.button(
                    "More",
                    width="100%",
                    cursor="pointer",
                    margin_top="20px",
                    height="48px",
                    on_click=NaimyState.paginate
                )
            )
        ),
        size="4",
    )

@rx.page(route="/naimy", title="네이미 생성 최적화", on_load=NaimyState.initState)
def naimy() -> rx.Component:
    return rx.flex(
        rx.cond(
            ~NaimyState.auth_complete,
            authentication(),
            main(),
        ),
        background_color=rx.color("purple", 8),
        min_height="100vh",
        align="center",
        padding_top="64px",
        padding_bottom="64px"
    )
