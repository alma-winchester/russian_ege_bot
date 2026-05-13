import requests
from bs4 import BeautifulSoup
import json
import re
import time

def clean_text(text):
    if not text: return ""
    return text.replace('\xad', '').replace('\xa0', ' ').strip()

url = "https://rus-ege.sdamgia.ru/test?theme=376&print=true"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}

res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.content, "html.parser")

tasks_data = []
prob_blocks = soup.find_all("div", class_="prob_main_tb")

if not prob_blocks:
    prob_blocks = soup.find_all("div", class_="pbody")

for i, block in enumerate(prob_blocks):
    parent = block.find_parent("td") or block
    info_line = parent.get_text()
    tid_match = re.search(r"№\s*(\d+)", info_line)
    tid = tid_match.group(1) if tid_match else f"unknown_{i}"

    q_text = clean_text(block.get_text(separator="\n"))

    ans_text = ""
    ans_tag = parent.find_next("div", class_="answer")
    if ans_tag:
        ans_text = clean_text(ans_tag.get_text().replace("Ответ:", ""))

    if q_text and len(q_text) > 20:
        tasks_data.append({"id": tid, "question": q_text, "answer": ans_text})

with open("ege_tasks_23.json", "w", encoding="utf-8") as f:
    json.dump(tasks_data, f, ensure_ascii=False, indent=4)


def escape_markdown(text):
    return text.replace('*', '').replace('_', '').replace('`', '')

with open('ege_tasks_23.json', 'r', encoding='utf-8') as f:
    tasks_data = json.load(f)

bot_tasks = []
for task in tasks_data:
    text = task['question']
    ans = task['answer']

    if ans and len(ans) > 1 and "Пояснение" not in text:
        bot_tasks.append({
            "id": task['id'],
            "text": escape_markdown(text),
            "answer": ans.strip().lower()
        })

with open('telegram_bot_tasks.json', 'w', encoding='utf-8') as f:
    json.dump(bot_tasks, f, ensure_ascii=False, indent=2)
