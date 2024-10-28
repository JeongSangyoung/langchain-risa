import asyncio
import reflex as rx
import itertools
from copy import deepcopy

from engine.main import tokenize, create_token_db, addFile, checkVersion, updateCurVersion

def splitCombinations(word: str) -> list[list[str]]:
    length = len(word)
    results = []
    for i in range(1, length):
        for combo in itertools.combinations(range(1, length), i):
            split_word = [word[:combo[0]]]
            split_word += [word[combo[j]:combo[j+1]] for j in range(len(combo)-1)]
            split_word.append(word[combo[-1]:])
            results.append(split_word)
    results.append([word])
    return reversed(results)

def setTokens(token, convert_dict) -> list[str]:
    if token in convert_dict:
        values = convert_dict[token]
        return values
    else:
        return []
        
def includeCheck(empty_data, root_id, position, token):
    if root_id not in empty_data:
        return False
    
    if len(empty_data[root_id]) <= position:
        return False
    
    if token in empty_data[root_id][position]:
        return True
    return False

def editChecker(empty_data, root_id, position, token, add=True):
    if root_id not in empty_data:
        return
    
    if len(empty_data[root_id]) <= position:
        return
    
    if add:
        if token not in empty_data[root_id][position]:
            empty_data[root_id][position].append(token)
    else:
        if token in empty_data[root_id][position]:
            empty_data[root_id][position].remove(token)

def stringsToIndices(array_2d, value_to_key):
    return [[value_to_key[string] for string in sublist] for sublist in array_2d]

def convertToEmptyLists(data):
    transformed_data = {}
    combmap_data = {}
    for key, value in data.items():
        new_value = []
        for sublist in value:
            new_sublist = [[] for _ in sublist]
            new_value.append(new_sublist)
        transformed_data[key] = new_value
        combmap_data[key] = [[] for _ in range(len(value))]
    return transformed_data, combmap_data

def displaySubTokens(key_id, comb_idx, combs: list[int]):
    return rx.card(
        rx.flex(
            rx.foreach(
                State.comb_map[key_id][comb_idx],
                lambda t: rx.text(t, font_weight="500"),
            ),
            flex_wrap="wrap",
            spacing="2",
            margin_bottom="4px",
        ),
        rx.flex(
            rx.foreach(
                combs,
                lambda comb_id, cidx: rx.vstack(
                    rx.card(
                        rx.flex(
                            rx.heading(State.id_map[comb_id], size="3"),
                            rx.flex(
                                rx.cond(
                                    State.token_map.contains(State.id_map[comb_id]),
                                    rx.foreach(
                                        State.token_map[State.id_map[comb_id]],
                                        lambda token: rx.button(
                                            token,
                                            variant=rx.cond(
                                                State.check_map[key_id][comb_idx][cidx].contains(token),
                                                "",
                                                "outline"
                                            ),
                                            color=rx.cond(
                                                State.check_map[key_id][comb_idx][cidx].contains(token),
                                                "white",
                                                "#111111"
                                            ),
                                            size="2",
                                            font_weight="400",
                                            color_scheme="gray",
                                            cursor="pointer",
                                            on_click=State.onClickToken(key_id, comb_idx, cidx, token),
                                        ),
                                    ),
                                ),
                                flex_wrap="wrap",
                                spacing="2",
                            ),
                            spacing="3",
                            align="center"
                        ),
                    ),
                )
            ),
            direction="column",
        ),
    )
  
def displayRootCard(kvId: tuple[int, list[list[int]]]):
    key_id = kvId[0]
    combinations = kvId[1]

    return rx.card(
        rx.vstack(
            rx.flex(
                rx.heading(State.id_map[key_id], size="5"),
                # rx.icon(
                #     "plug-2",
                #     size=24,
                #     cursor="pointer",
                # ),
                justify="between",
                width="100%",
                align="center",
            ),
            rx.flex(
                rx.foreach(
                    combinations,
                    lambda comb, comb_idx: displaySubTokens(key_id, comb_idx, comb)
                ),
                direction="column",
                width="100%",
                spacing="3",
            ),
        ),
        width="100%",
        padding="12px",
    )


class State(rx.State):
    inputs: str
    pendding: bool = False
    root_tokens: list[str] = None
    convert_dict: dict[str, list[str]] = None
    threshold_ed: float = 0.6
    threshold_len: int = 2
    request_key: str
    request_trans: str
    cur_version: str

    display_title: str

    search_expression: str

    open_slot: bool = False

    before_len: int = 2
    before_ed: float = 0.6
    before_switch: bool = False
    before_cnt: int = 10

    switch_checked: bool = False

    running: bool = False
    progress: int

    max_count: int = 10

    token_map: dict[str, list[str]]
    id_map: dict[int, str]
    id_map_reverse: dict[str, int]
    root_match: dict[int, list[list[int]]]
    check_map: dict[int, list[list[list[str]]]]
    comb_map: dict[int, list[list[str]]]

    def initState(self):
        self.open_slot = False
        self.search_expression = ''
        self.request_key = ''
        self.request_trans = ''
        self.check_map = {}
        self.convert_dict = None
        self.root_tokens = None
        self.max_count = 10

        self.token_map = {}
        self.comb_map = {}
        self.root_match = {}
        self.id_map = {}
        self.id_map_reverse = {}

        self.progress = 0
        self.running = False
        self.display_title = ''

    def toggleRunning(self):
        if self.progress >= 100:
            self.progress = 0
        if self.running:
            self.running = False
        return State.streamTask()

    @rx.background
    async def streamTask(self):
        async with self:
            self.running = True

        async with self:
            self.progress += 10
            s, cv = checkVersion()
            self.cur_version = cv

        async with self:
            if not s or \
                self.root_tokens == None or self.convert_dict == None or \
                self.before_len != self.threshold_len or \
                self.before_ed != self.threshold_ed or \
                self.before_cnt != self.max_count or \
                self.before_switch != self.switch_checked:

                result = create_token_db(self.threshold_len, self.threshold_ed, self.switch_checked, self.max_count)
                self.progress += 30

                self.convert_dict = result
                self.renewRootTokens()
                self.before_ed = self.threshold_ed
                self.before_len = self.threshold_len
                self.before_switch = self.switch_checked
                self.before_switch = self.max_count
                updateCurVersion()
                self.progress += 20
            else:
                self.progress += 50

        await asyncio.sleep(0.7)
        async with self:
            self.token_map = {}
            self.check_map = {}
            self.id_map = {}
            self.id_map_reverse = {}
            self.root_match = {}
            self.comb_map = {}

            self.progress += 10
            input_tokens = tokenize(self.inputs, self.root_tokens) # ['삼성', '바이오', '로직스']

            self.display_title = " + ".join([title for title in input_tokens])

            for idx, token in enumerate(input_tokens):
                self.id_map[idx] = token
                self.token_map[token] = setTokens(token, result)

            start_idx = len(input_tokens)
            for root_token in input_tokens:
                for candidate in splitCombinations(root_token):
                    for tiny_token in candidate:
                        if tiny_token in self.token_map:
                            continue
                        if tiny_token in result:
                            values = result[tiny_token]
                        else:
                            values = []
                        self.token_map[tiny_token] = values
                        if tiny_token not in self.id_map.values():
                            self.id_map[start_idx] = tiny_token
                            start_idx += 1
            self.id_map_reverse = {v: k for k, v in self.id_map.items()}
            self.progress += 10
            for root_token in input_tokens:
                self.root_match[self.id_map_reverse[root_token]] = \
                    stringsToIndices(splitCombinations(root_token), self.id_map_reverse)
            transformed_data = convertToEmptyLists(self.root_match)
            self.check_map = transformed_data[0]
            self.comb_map = transformed_data[1]
            self.progress += 20

            # print('====root_match=====')
            # print(self.root_match)
            # print()
            # print('====check_map======')
            # print(self.check_map)
            # print()
            # print('====token_map=====')
            # print(self.token_map)
            # print()
            # print('====comb_map=====')
            # print(self.comb_map)

        await asyncio.sleep(0.7)

        async with self:
            self.running = False

    def renewRootTokens(self):
        self.root_tokens = sorted(list(self.convert_dict.keys()), key=len, reverse=True)

    def onClickToken(self, key_id, comb_idx, cidx, token):
        if token in self.check_map[int(key_id)][comb_idx][cidx]:
            self.check_map[int(key_id)][comb_idx][cidx].remove(token)
        else:
            self.check_map[int(key_id)][comb_idx][cidx].append(token)
        
        if [] in self.check_map[int(key_id)][comb_idx]:
            self.comb_map[int(key_id)][comb_idx] = []
            return
        combs = [''.join(combination) for combination in itertools.product(*self.check_map[int(key_id)][comb_idx])]
        self.comb_map[int(key_id)][comb_idx] = combs

    def checkToken(self, key_id, comb_idx, cidx, token):
        if token not in self.check_map[int(key_id)][comb_idx][cidx]:
            return False
        return True

    def keyDown(self, k):
        if k == 'Enter':
            if self.progress >= 100:
                self.progress = 0
            if self.running:
                self.running = False
            return State.streamTask()
    
    def reqAdd(self):
        if self.request_key == '' or self.request_trans == '':
            return
        addFile(f'add//{self.request_key.lower()}//{self.request_trans.lower()}')
        self.request_key = ''
        self.request_trans = ''

    def reqRemove(self):
        if self.request_key == '' or self.request_trans == '':
            return
        addFile(f'remove//{self.request_key.lower()}//{self.request_trans.lower()}')
        self.request_key = ''
        self.request_trans = ''

    def changeSlot(self):
        self.open_slot = not(self.open_slot)

    def setThresholdLen(self, value: list[int]):
        self.threshold_len = value[0]

    def setThresholdEd(self, value: list[float]):
        self.threshold_ed = value[0]

    def changeChecked(self, checked: bool):
        self.switch_checked = checked

@rx.page(route="/", title="검색식 생성 프로그램", on_load=State.initState)
def index() -> rx.Component:
    return rx.flex(
        rx.container(
            rx.flex(
                rx.vstack(
                    rx.flex(
                        rx.button(
                            "상표명 생성 AI 로 바로가기",
                            color_scheme="teal",
                            margin_bottom="20px",
                            on_click=rx.redirect(
                                "/llm"
                            ),
                            cursor="pointer",
                        ),
                        rx.button(
                            "네이미 최적화 바로가기",
                            color_scheme="teal",
                            margin_bottom="20px",
                            on_click=rx.redirect(
                                "/naimy"
                            ),
                            cursor="pointer",
                        ),
                        spacing="2",
                    ),
                    rx.box(
                        rx.heading("검색식 생성 프로그램", size="6"),
                        rx.text(f"db version: {State.cur_version}")
                    ),
                    rx.hstack(
                        rx.input(
                            value=State.inputs,
                            on_change=State.set_inputs,
                            on_key_down=State.keyDown,
                            placeholder="입력",
                            max_length=20,
                            size="3",
                        ),
                        rx.button(
                            rx.cond(
                                ~State.running, 
                                rx.text("Generate"),
                                rx.spinner(size="3"),
                            ),
                            disabled=rx.cond(State.running, True, False),
                            on_click=State.toggleRunning,
                            _hover={
                                "cursor": "pointer"
                            },
                            size="3",
                        ),
                    ),

                    rx.flex(
                        rx.input(
                            value=State.max_count,
                            on_change=State.set_max_count,
                            size="2",
                            width="32px",
                        ),
                        rx.heading("토큰 최대 개수", size="2"),
                        align="center",
                        spacing="2",
                    ),

                    rx.flex(
                        rx.switch(
                            checked=State.switch_checked,
                            on_change=State.changeChecked,
                            color_scheme="bronze",
                        ),
                        rx.heading("어휘 확장기법 적용", size="2"),
                        spacing="2",
                        align="center",
                    ),
                    rx.card(
                        rx.heading(
                            "● threshold_len : ",
                            State.threshold_len,
                            size="3",
                            margin_top="4px"
                        ),
                        rx.text("커질수록 많은 단어 포함, 정확도 하락", margin_top="4px", margin_bottom="12px"),
                        rx.slider(
                                default_value=2,
                                step=1,
                                min=1,
                                max=5,
                                on_change=State.setThresholdLen,
                                variant="soft",
                                color_scheme="ruby",
                            ),
                        rx.heading(
                            "●  threshold_ed : ",
                            State.threshold_ed,
                            size="3",
                            margin_top="20px",
                        ),
                        rx.text("작을수록 많은 단어 포함, 정확도 하락", margin_top="4px", margin_bottom="12px"),
                        rx.slider(
                            default_value=0.6,
                            step=0.1,
                            min=0.1,
                            max=0.9,
                            on_change=State.setThresholdEd,
                            radius="small",
                            color_scheme="violet",
                            variant="soft",
                        ),
                        width="308px",
                        padding="16px",
                        padding_bottom="20px",
                    ),
                    # rx.cond(
                    #     ~State.open_slot,
                    #     rx.button(
                    #         "DB 수정요청",
                    #         on_click=State.changeSlot,
                    #         color_scheme="iris"
                    #     ),
                    #     rx.card(
                    #         rx.box(
                    #             rx.input(
                    #                 value=State.request_key,
                    #                 on_change=State.set_request_key,
                    #                 placeholder="Token",
                    #                 width="140px",
                    #             ),
                    #             rx.input(
                    #                 value=State.request_trans,
                    #                 on_change=State.set_request_trans,
                    #                 placeholder="변환",
                    #                 margin_top="12px"
                    #             ),
                    #         ),
                    #         rx.flex(
                    #             rx.button(
                    #                 "추가요청",
                    #                 color_scheme="purple",
                    #                 on_click=State.reqAdd,
                    #             ),
                    #             rx.button(
                    #                 "삭제요청",
                    #                 color_scheme="red",
                    #                 on_click=State.reqRemove,
                    #             ),
                    #             margin_top="8px",
                    #             justify="between",
                    #         ),
                    #         width="308px"
                    #     ),
                    # ),
                ),
                spacing="2",
                justify="between",
                align="center"
            ),

            rx.cond(
                State.running,
                rx.progress(
                    value=State.progress,
                    max=100,
                    radius="full",
                    color_scheme="tomato",
                    margin_top="32px",
                ),
            ),

            rx.vstack(
                rx.heading(State.display_title, margin_top="32px"),
                rx.flex(
                    rx.foreach(
                        State.root_match,
                        displayRootCard,
                    ),
                    flex_wrap="wrap",
                    spacing="2",
                    direction="column",
                ),
                margin_top="32px"
            ),
        ),
        background_color=rx.color("grass", 8),
        min_height="100vh",
        align="center",
        padding_top="64px",
        padding_bottom="64px"
   )
