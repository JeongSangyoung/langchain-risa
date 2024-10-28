import os
import json
import uuid

from flask import Flask, Response, request, stream_with_context

from model import GPT, RisaBrandGPT
from prompt import RisaPROMPT

app = Flask(__name__)

gpt = GPT()
risa_gpt = RisaBrandGPT()
prompt = RisaPROMPT()

@app.route('/', methods=["GET", "POST"])
def home():
    return {"Content-Type": "text/plain"}

@app.route('/options', methods=["POST"])
def generate_options():
    try:
        if request.is_json:
            request_data = request.get_json()
            model = request_data.get("model", "")
            usage = request_data.get("usage", "")
            description = request_data.get("description", "")
        else:
            model = request.form.get("model", "")
            usage = request.form.get("usage", "")
            description = request.form.get("description", "")
        options = gpt.gptGenerateOptions(model, usage, description)
        return Response(
            response=json.dumps(options), status=200, mimetype="application/json"
        )

    except Exception as e:
        print('err', e)
        return Response(
            response=e, status=500, mimetype="application/json"
        )

@app.route('/generate', methods=["POST"])
def generate_names():
    try:
        if request.is_json:
            request_data = request.get_json()
            model = request_data.get("model", "")
            usage = request_data.get("usage", "")
            category = request_data.get("category", "")
            tones = request_data.get("tones", "")
            targets = request_data.get("targets", "")
            trends = request_data.get("trends", "")
            languages = request_data.get("languages", "")
            description = request_data.get("description", "")
            brandNames = request_data.get("brandNames", [])
        else:
            model = request.form.get("model", "")
            usage = request.form.get("usage", "")
            category = request.form.get("category", "")
            tones = request.form.get("tones", "")
            targets = request.form.get("targets", "")
            trends = request.form.get("trends", "")
            languages = request.form.get("languages", "")
            description = request.form.get("description", "")
            brandNames = request.form.get("brandNames", [])
        return Response(
            stream_with_context(
                gpt.gptGenerateNamesWithStream(
                    usage=usage,
                    description=description,
                    category=category,
                    tone=tones,
                    seed=[],
                    target=targets,
                    trend=trends,
                    language=languages,
                    level=1,
                    brandNames=brandNames,
                    model=model,
                )
            )
        )

    except Exception as e:
        pass


@app.route('/db/get', methods=["POST"])
def read_json_id_map():
    try:
        with open('./id_map.json', 'r+', encoding='utf-8') as file:
            id_map = json.load(file)

        request_data = request.get_json()
        username = request_data.get("username", "")

        if username not in id_map:
            uid = str(uuid.uuid4())
            id_map[username] = uid

            with open(f'./DB/{uid}.json', 'w', encoding='utf-8') as userfile:
                json.dump([], userfile)

            with open('./id_map.json', 'w', encoding='utf-8') as file:
                id_map.update({username: uid})
                json.dump(id_map, file, indent=4)

            file.close()
            userfile.close()
            return Response(response=json.dumps([]), status=200, mimetype='application/json')
        
        with open(f'./DB/{id_map[username]}.json', 'r', encoding='utf-8') as userfile:
            data = json.load(userfile)
        return Response(response=json.dumps(data), status=200, mimetype='application/json')
    except Exception as e:
        print(e)
        return Response(response=json.dumps({"error": str(e)}), status=500, mimetype='application/json')

@app.route('/db/add', methods=["POST"])
def write_json_db():
    try:
        with open('./id_map.json', 'r+', encoding='utf-8') as file:
            id_map = json.load(file)
        
        request_data = request.get_json()
        username = request_data.get("username", "")
        items = request_data.get("items", "")

        if username not in id_map:
            raise("유저 없음")

        with open(f'./DB/{id_map[username]}.json', 'r', encoding='utf-8') as userfile1:
            result_list = json.load(userfile1)
        userfile1.close()
        new_db = items + result_list

        with open(f'./DB/{id_map[username]}.json', 'w', encoding='utf-8') as userfile2:
            json.dump(new_db, userfile2)

        userfile2.close()
        file.close()

        return Response(response="", status=200, mimetype='application/json')
        

    except Exception as e:
        print(e)
        return Response(response=json.dumps({"error": str(e)}), status=500, mimetype='application/json')

@app.route('/risa', methods=["POST"])
async def risa():
    try:
        result = {"gpt": {}}
        request_data = request.get_json()
        brand_name  = request_data.get("brand_name", "")
        category = request_data.get("category", "")

        result = {"gpt": {}}

        morpheme_prompt = prompt.morpheme([brand_name, category])

        # GPT 비동기 작업을 동기 작업으로 변환
        gpt_morpheme = risa_gpt.create(morpheme_prompt)

        result["gpt"]["morpheme"] = eval(gpt_morpheme)
        gpt_morpheme = eval(gpt_morpheme)

        means_sentence = ""
        for morpheme, mean in gpt_morpheme["detail"].items():
            means_sentence += f"{morpheme} : {mean}\n"
        morphemes_sentence = ", ".join(gpt_morpheme["morpheme"])
        gpt_prompt_question = [brand_name, morphemes_sentence, means_sentence, category]

        # GPT 프롬프트 생성
        prompt_list = [
            prompt.normal(gpt_prompt_question),
            prompt.concept(gpt_prompt_question),
            prompt.property(gpt_prompt_question),
            prompt.simple(gpt_prompt_question),
            prompt.frist_name(gpt_prompt_question),
            prompt.place(gpt_prompt_question),
            prompt.famous(gpt_prompt_question),
        ]

        # GPT 보고서 생성
        gpt_report = await risa_gpt.get_report(prompt_list)

        mapping = {
            "normal": "보통명칭",
            "concept": "관념분석",
            "property": "성질분석",
            "simple": "간단한 명칭",
            "frist_name": "흔한 성, 명칭",
            "place": "유명한 지명",
            "famous": "그 외 유명한 상표",
        }

        gpt_log = result["gpt"].copy()

        gpt_log["report"] = {}
        for val, rgpt in zip(mapping.values(), gpt_report):
            try:
                gpt_log["report"][val] = eval(rgpt)
            except:
                gpt_log["report"][val] = rgpt

        try:
            result["gpt"]["report"] = [eval(i) for i in gpt_report]
        except:
            result["gpt"]["report"] = gpt_report

        rgpt = result["gpt"]
        gpt_new_report = {}
        for report, tag in zip(
            rgpt["report"], ["normal", "concept", "property", "simple", "frist_name", "place", "famous"]
        ):
            gpt_new_report[tag] = report

        gpt_report = {"analyze": {"주요부": set(), "부가어": set()}}

        for key, val in gpt_new_report.items():
            gpt_report[key] = {}
            if key != "property":
                for word, bool in val["result"].items():
                    if bool:
                        gpt_report[key][word] = val["detail"][word]
                        gpt_report["analyze"]["부가어"].add(word)
            else:
                for word, property_list in val["result"].items():
                    if len(property_list) > 0:
                        gpt_report[key][word] = val["detail"][word]
                        gpt_report["analyze"]["부가어"].add(word)

        for i in rgpt["morpheme"]["morpheme"]:
            if not i in gpt_report["analyze"]["부가어"]:
                gpt_report["analyze"]["주요부"].add(i)
        gpt_report["analyze"]["부가어"] = list(gpt_report["analyze"]["부가어"])
        gpt_report["analyze"]["주요부"] = list(gpt_report["analyze"]["주요부"])

        report_text = ""
        if len(gpt_report["analyze"]["주요부"]) == 0:
            main_list = []
            fail_list = []
            detail_report = []
            for key, val in gpt_report.items():
                if key == "analyze":
                    pass
                else:
                    temp = []
                    temp.append(f"[{mapping[key]}]")
                    if val:
                        fail_list.append(mapping[key])
                        for word, reason in val.items():
                            temp.append(f"{word} : {reason}")
                    else:
                        temp.append("해당없음")
                    detail_report.append("\n".join(temp))
            fail = ", ".join(fail_list)
            detail = "\n\n".join(detail_report)
            report_text += f"이 상표는 [{fail}] 사항에 부적합 판정을 받아 상표 출원 가능성이 매우 낮습니다.\n\n{detail}"
        else:
            main_list = []
            fail_list = []
            detail_report = []
            for key, val in gpt_report.items():
                if key == "analyze":
                    main_list += val["주요부"]
                else:
                    temp = []
                    temp.append(f"[{mapping[key]}]")
                    if val:
                        fail_list.append(mapping[key])
                        for word, reason in val.items():
                            temp.append(f"{word} : {reason}")
                    else:
                        temp.append("해당없음")
                    detail_report.append("\n".join(temp))

        main = ", ".join(main_list)
        fail = ", ".join(fail_list)
        detail = "\n\n".join(detail_report)
        report_text += f"이 상표는 식별력 있는 [{main}]의 단어가 있어 상표 출원 가능성이 있어 보입니다.\n\n{detail}"

        gpt_report["brand_name"] = brand_name
        gpt_report["category"] = category

        detail_report = f"""
    ---------------상세 결과----------------
    단어 분리 : "{", ".join(gpt_log["morpheme"]["morpheme"])}"\n
    """
        for key, val in gpt_log["report"].items():
            detail_report += f"[{key}]\n"
            for word, word_val in val["detail"].items():
                detail_report += f"{word} : {word_val}\n"
            detail_report += "\n"

        response_body = f"BrandName: {brand_name}\nCategory: {category}\n\n----------------간이 결과---------------- \n{report_text}\n\n{detail_report}"
        return Response(response=response_body, status=200, mimetype='application/text')
    except Exception as e:
        print(e)
        return Response(response=json.dumps({"error": str(e)}), status=500, mimetype='application/json')

if __name__ == '__main__':
    app.run(port=5001, debug=True)