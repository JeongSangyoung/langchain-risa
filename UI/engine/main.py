import json
import os
import uuid
from datetime import datetime

# with open('./engine/dicts/word_matching_dict_perturb.json', 'r', encoding='utf-8') as file:
with open('./engine/dicts/word_matching_dict.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

words = list(data.keys())
langs = ['lat', 'cym', 'ita', 'spa', 'isl']


file_dir = f'{os.getcwd()}/engine/requestEdit'
today = datetime.now().strftime("%Y%m%d")
if not os.path.isdir(file_dir):
    os.mkdir(file_dir)

def readLine(line):
    try:
        act, key, token = line.split("//")
        return (True, (act, key, token))
    except Exception as e:
        return (False, None)

def readReqFiles(convert_dict):
    today = datetime.now().strftime("%Y%m%d")
    file_dir = f'{os.getcwd()}/engine/requestEdit'
    if not os.path.isdir(f"{file_dir}/{today}"):
        os.mkdir(f"{file_dir}/{today}")

    for dat in os.listdir(f'{file_dir}'):
        # today all read 
        for d in os.listdir(f"{file_dir}/{dat}"):
            with open(f"{file_dir}/{dat}/{d}", "r", encoding="utf-8") as file:
                line = file.readline().strip()
            if not line:
                continue
            s, t = readLine(line)
            if not s:
                continue
            act, key, token = t
            if act == 'add':
                if key not in convert_dict:
                    convert_dict[key] = token.split(',')
                else:
                    for tk in token.split(','):
                        if tk not in convert_dict[key]:
                            convert_dict[key].append(tk)
            elif act == 'remove':
                if key in convert_dict:
                    for tk in token.split(','):
                        tk = tk.strip()
                        if tk in convert_dict[key]:
                            convert_dict[key].remove(tk)

def addFile(content):
    uid = uuid.uuid4()
    today = datetime.now().strftime("%Y%m%d")
    file_dir = f'{os.getcwd()}/engine/requestEdit'
    if not os.path.isdir(f"{file_dir}/{today}"):
        os.mkdir(f"{file_dir}/{today}")
    
    with open(f"{file_dir}/{today}/{uid}.txt", "w", encoding="utf-8") as file:
        file.write(content)
    file.close()

    with open(f"{os.getcwd()}/engine/updateCheck.txt", "r+") as file:
        cur_v_line = file.readline()
        # 파일 읽기 위치를 처음으로 되돌리기
        file.seek(0)
        # 정수로 변환 후 증가
        cur_v = int(cur_v_line) if cur_v_line else 0
        cur_v += 1
        
        # 파일 덮어쓰기를 위해 파일을 비우기
        file.truncate(0)
        
        # 증가된 값 쓰기
        file.write(str(cur_v))

def checkVersion():
    uv = '-'
    cv = '+'
    with open(f"{os.getcwd()}/engine/updateCheck.txt", "r") as file1:
        uv = file1.readline()
    with open(f"{os.getcwd()}/engine/myVersion.txt", "r") as file2:
        cv = file2.readline()
    if uv == cv:
        return (True, cv)
    return (False, cv)

def updateCurVersion():
    with open(f"{os.getcwd()}/engine/updateCheck.txt", "r") as file1:
        uv = file1.readline()
    with open(f"{os.getcwd()}/engine/myVersion.txt", "r+") as file2:
        cv = file2.readline()
        file2.seek(0)
        cv = uv
        file2.truncate(0)
        file2.write(cv)

def create_token_db(threshold_len, threshold_ed, is_perturb, max_tokens=15):
    if is_perturb:
        with open(f'{os.getcwd()}/engine/dicts/convert_dict_perturb_{threshold_len}_{threshold_ed}.json',
                  'r', encoding='utf-8') as file:
            convert_dict = json.load(file)
        with open(f'{os.getcwd()}/engine/dicts/convert_dict_en_perturb_{threshold_len}_{threshold_ed}.json',
                  'r', encoding='utf-8') as file:
            convert_dict_en = json.load(file)
        convert_dict = convert_dict | convert_dict_en
    else:
        with open(f'{os.getcwd()}/engine/dicts/convert_dict_{threshold_len}_{threshold_ed}.json',
                   'r', encoding='utf-8') as file:
            convert_dict = json.load(file)
        with open(f'{os.getcwd()}/engine/dicts/convert_dict_en_{threshold_len}_{threshold_ed}.json',
                  'r', encoding='utf-8') as file:
            convert_dict_en = json.load(file)
        convert_dict = convert_dict | convert_dict_en

    readReqFiles(convert_dict)
    new_convert_dict = {}
    for ck, cv in convert_dict.items():
        if ck not in new_convert_dict:
            new_convert_dict[ck] = []
        temp_values = []
        temp_counts = []
        for cvk, cvv in cv.items():
            temp_values.append(cvk)
            temp_counts.append(cvv)
        
        combined = list(zip(temp_counts, temp_values))
        combined.sort(reverse=True, key=lambda x: x[0])
        new_convert_dict[ck] = [item[1] for item in combined][:max_tokens]
    return new_convert_dict

# tokenize word in to tokens based on convert dictionary
def tokenize(word, tokens):
    # print(tokens)
    result = []
    cnt = 0
    word = word.lower()
    word = word.replace(' ', '')
    while word:
        cnt += 1
        matched = False
        for token in tokens:
            if word.startswith(token):
                result.append(token)
                word = word[len(token):]
                matched = True
                break
        if not matched:
            result.append(word)
            break
        if cnt > 100:
            result.append(word)
            break
    return result