#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import sys
import os
import subprocess
import json
import traceback
import time
from pathlib import Path

# --- 用户可配置的提示词模式 ---
PROMPT_MODES = {
    "explain": """
请用最简单、最接地气、普通人一听就能明白的大白话，解释一下 '{query_text}' 到底是什么意思。
你就把我当成一个完全不懂这方面知识的小学生或老奶奶来解释。
如果可以的话，尽量用一个生活中的例子或者打个比方，帮助我理解。
解释的时候，力求准确，但千万别用那些文绉绉或者太专业的词儿。    
    """,
    "deep_explain": "请帮我用大白话深度解读以下内容：\n'{query_text}'",
    "critical_think": """
请针对 '{query_text}' 这个主题或说法，用最大白话、最容易懂的简体中文进行批判性思考。请尝试从下面几个方面帮我分析分析（挑你觉得最合适的几个方面说就行，不用每个都说）：

1.  **它到底在说啥？** (核心观点/主要信息是什么？)
2.  **这么说有啥依据吗？** (支撑它的理由或证据可靠吗？充分吗？)
3.  **有没有啥没明说但暗含的意思？** (背后可能藏着什么假设或前提？)
4.  **有没有别的看法或角度？** (换个角度看会怎么样？有没有不同的声音？)
5.  **可能会有啥好的或不好的影响？** (长远来看会怎么样？)
6.  **我们应该怎么更全面地看待这事儿/这个说法？**

请把你的分析一点一点说清楚，用简单的词，别整那些难懂的。    
    """,
    "translate": """
请仔细分析用户提供的文本内容：'{query_text}'

首先，判断该内容更像是一个独立的单词/短语（适合查词并深入学习），还是一个完整的句子/段落（适合翻译并学习其中词汇）。

**情况一：如果内容判断为【单词或短语】进行学习：**
请提供该单词/短语的详细解释。
- 如果是中文内容，请给出：
    1.  拼音。
    2.  主要的几种英文释义（注明词性，最多3种）。
    3.  为每种主要英文释义提供一个中文例句及其对应的英文翻译。
- 如果是英文内容，请给出：
    1.  国际音标 (IPA, 如果你能准确提供)。
    2.  主要的几种简体中文释义（注明词性，最多3种）。
    3.  为每种主要中文释义提供一个英文例句及其对应的简体中文翻译。
- 如果是其他语言的单词/短语，请尝试识别其语言，并给出：
    1.  其在该语言中的发音提示（如果可能，例如罗马音）。
    2.  主要的几种简体中文释义（注明词性或用途，最多3种）。
    3.  为每种主要中文释义提供一个该语言的例句及其对应的简体中文翻译。

请严格按照以下 Markdown 格式组织回答 (以英文单词为例，其他语言和中文词语则对应调整各项内容)：

**查询内容：**
{query_text}

---
**类型：** 单词/短语学习
---

**发音：**
* [例如：səˌrɛnˈdɪpəti / こんにちは (Konnichiwa) / [中文拼音] ]

---

**详细释义：**

1.  **含义：**
    * **词性/用途：** [词性1/用途说明]
    * **解释 ([目标语言，通常为中文或英文])：** [解释1]
    * **例句 ([源语言])：** [Example sentence 1 in original language]
    * **例句翻译 ([目标语言])：** [Translation of example 1]

2.  **含义：**
    * **词性/用途：** [词性2/用途说明]
    * **解释 ([目标语言])：** [解释2]
    * **例句 ([源语言])：** [Example sentence 2 in original language]
    * **例句翻译 ([目标语言])：** [Translation of example 2]

(如果还有其他重要释义，请继续，总数不超过3条)

**情况二：如果内容判断为【句子或段落】进行翻译和学习：**
请分析输入文本的语言。
- 如果输入的是中文，请将其翻译成流畅自然的英文。
- 如果输入的是英文或其他可识别的非中文语言，请将其翻译成通顺易懂的简体中文。

翻译完成后，请从【原文】中挑选出2-3个对于学习者来说（学习目标语言或了解原文）可能不熟悉或值得重点学习的核心词汇。为这些词汇提供：
-   它们在原文中的形式。
-   它们在【目标翻译语言】中的简明解释（如果是中文词被翻译成英文后的生词学习，请提供拼音和英文解释；如果是外文词被翻译成中文后的生词学习，请提供原文发音提示（如罗马音）和中文解释）。

请严格按照以下 Markdown 格式组织回答 (以下示例为非中文原文翻译成简体中文，其他情况请AI灵活调整标签和内容)：

**原文 (例如：[检测到的语言，如日语])：**
{query_text}

---
**类型：** 句子/段落翻译与词汇学习
---

**翻译 (简体中文)：**
[此处为翻译后的简体中文内容]

---

**核心词汇学习 (来自原文)：**
* **[原文词1，例如：難しい]** (发音提示: [例如：muzukashī]): [该词在简体中文中的解释或对应表达，例如：困难的，不容易的]
* **[原文词2]** (发音提示: [发音]): [中文解释]
* **[原文词3]** (发音提示: [发音]): [中文解释]

---
**重要指示：请AI务必先做出明确的“类型”判断，并在输出中明确标示出所选的类型和检测到的源语言（如果适用）。如果输入内容非常简短且难以明确区分，请优先尝试按“情况一：单词或短语学习”处理，并努力识别其原始语言。**
    """,
    "movie_summary": """
请查询电影《{query_text}》的详细信息，并严格按照以下 Markdown 格式进行排版输出：

**电影名称：** 《{query_text}》

---

**剧情简介 (100字以内)：**
[此处填写控制在100字以内的剧情简介，避免剧透关键情节]

---

**核心信息：**
* **导演：** [此处填写导演名]
* **主要演员：** [此处填写主要演员列表，用逗号分隔]
* **上映年份：** [此处填写上映年份，如XXXX年]
* **豆瓣评分：** [此处填写豆瓣评分，例如：8.5/10；如果暂无评分，请注明“暂无评分”或“信息待更新”]

---

**额外信息 (如果方便获取)：**
* **类型：** [此处填写电影类型，如：剧情 / 动作 / 科幻]
* **制片国家/地区：** [此处填写制片国家或地区]
* **片长：** [此处填写电影片长]

**请确保剧情简介简洁明了，不超过100字。如果某项核心信息确实无法找到，请在该项后注明“信息暂缺”。**    
    """,
    "custom_prompt": "{query_text}" # 用户输入的就是完整提示
}
DEFAULT_PROMPT_MODE = "explain"
SEPARATOR = "<SEP>"

# --- 常量和 API 配置 ---
API_KEY = os.getenv('GEMINI_API_KEY_ALFRED') # 从 Alfred 工作流环境变量获取
MODEL_NAME = "gemini-1.5-flash-latest" # 确保模型支持流式
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com"

# Alfred 工作流缓存目录
alfred_workflow_bundleid = os.getenv('alfred_workflow_bundleid', 'default.bundle.id')
ALFRED_WORKFLOW_CACHE = os.getenv('alfred_workflow_cache', os.path.expanduser(f'~/Library/Caches/com.runningwithcrayons.Alfred/Workflow Data/{alfred_workflow_bundleid}'))
Path(ALFRED_WORKFLOW_CACHE).mkdir(parents=True, exist_ok=True)

STREAM_FILE = os.path.join(ALFRED_WORKFLOW_CACHE, "gemini_stream.txt")
PID_FILE = os.path.join(ALFRED_WORKFLOW_CACHE, "gemini_pid.txt")
ACCUMULATED_TEXT_FILE = os.path.join(ALFRED_WORKFLOW_CACHE, "gemini_accumulated.txt")
MODE_AND_QUERY_FILE = os.path.join(ALFRED_WORKFLOW_CACHE, "gemini_mode_query.json") # 保存模式和原始查询

# --- 辅助函数 ---
def read_file_content(filepath, default=""):
    try:
        with open(filepath, 'r', encoding='utf-8') as f: return f.read()
    except FileNotFoundError: return default
def write_file_content(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as f: f.write(content)
def append_file_content(filepath, content_to_append): # 不再使用，因为是替换整个累积文本
    pass
def delete_file_if_exists(filepath):
    if os.path.exists(filepath): os.remove(filepath)
def is_process_running(pid):
    if not pid: return False
    try: os.kill(int(pid), 0)
    except OSError: return False
    else: return True
def assistant_signature(): return ""

# --- Gemini API 流式响应解析 (与之前类似) ---
def parse_gemini_sse_stream_for_new_text(new_stream_chunk_raw):
    new_text = ""
    lines = new_stream_chunk_raw.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith("data: "):
            json_str = line[len("data: "):].strip()
            if not json_str or json_str == "[DONE]": continue
            try:
                chunk = json.loads(json_str)
                if chunk.get("candidates") and chunk["candidates"][0].get("content") and chunk["candidates"][0]["content"].get("parts"):
                    new_text += "".join(part.get("text", "") for part in chunk["candidates"][0]["content"]["parts"])
            except json.JSONDecodeError: pass
    return new_text

def check_stream_ended_from_chunk(new_stream_chunk_raw):
    lines = new_stream_chunk_raw.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith("data: "):
            json_str = line[len("data: "):].strip()
            if not json_str: continue
            try:
                chunk = json.loads(json_str)
                if chunk.get("candidates") and chunk["candidates"][0].get("finishReason") in ["STOP", "MAX_TOKENS", "SAFETY", "RECITATION", "OTHER"]:
                    return True
            except json.JSONDecodeError: pass
        elif line.startswith("{"):
             try:
                error_data = json.loads(line)
                if error_data.get("error"): return True
             except: pass
    return False

# --- 主逻辑 ---
def main():
    # 从 Alfred 环境变量获取状态 (rerun 时传递)
    is_streaming_now = os.getenv('streaming_now_alfred') == 'true'
    # user_query_original 不再通过 variables 传递，而是从文件读取
    last_stream_file_size = int(os.getenv('last_stream_file_size_alfred', '0'))
    
    selected_mode_id = os.getenv('chosen_mode_id', DEFAULT_PROMPT_MODE) # <--- **新增/修正这一行**

    # 初始调用时，sys.argv[1] 是用户的 "模式<SEP>查询" 或纯查询 (用默认模式)
    # 在 Text View 的 Script Input 中提交时，sys.argv[1] 是新的用户输入 (可能也需要模式)
    actual_user_query = sys.argv[1] if len(sys.argv) > 1 else ""

    output_for_text_view = {"variables": {}} # Alfred 变量

    # --- 解析模式和查询 ---
    prompt_text = ""

    if not is_streaming_now: # 只在初始调用时解析模式和查询
        
        if not actual_user_query.strip():
            output_for_text_view["response"] = "ERROR: 查询内容不能为空。"
            print(json.dumps(output_for_text_view))
            return
        
        if selected_mode_id not in PROMPT_MODES: # 理论上不会到这里，因为上面有处理
            output_for_text_view["response"] = f"ERROR: 未知的提示词模式 '{selected_mode_id}'。"
            print(json.dumps(output_for_text_view))
            return
            
        prompt_template = PROMPT_MODES[selected_mode_id]
        prompt_text = prompt_template.format(query_text=actual_user_query)
        
        # 保存模式和查询，供 rerun 时构建 payload (如果需要重新构建请求)
        # 或者，如果API支持续写，可能不需要重新构建完整请求
        # 这里我们假设每次 rerun 只是读取流，初始请求已包含所有信息
        write_file_content(MODE_AND_QUERY_FILE, json.dumps({"mode": selected_mode_id, "query": actual_user_query, "prompt": prompt_text}))

    else: # 是 rerun 调用
        saved_mode_query = json.loads(read_file_content(MODE_AND_QUERY_FILE, "{}"))
        prompt_text = saved_mode_query.get("prompt", "错误：无法恢复之前的提示。") # Rerun 时理论上不需要重新生成 prompt
                                                                            # 因为 curl 已经在后台用初始 prompt 请求了

    # --- 处理 API Key ---
    if not API_KEY:
        output_for_text_view["response"] = "ERROR: GEMINI_API_KEY_ALFRED not set."
        print(json.dumps(output_for_text_view))
        return

    # --- 流式处理逻辑 ---
    if not is_streaming_now and actual_user_query: # 初始调用，且有有效查询
        delete_file_if_exists(STREAM_FILE)
        delete_file_if_exists(PID_FILE)
        write_file_content(ACCUMULATED_TEXT_FILE, "")

        request_payload = {
            "contents": [{"parts": [{"text": prompt_text}], "role": "user"}],
            "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.7}
        }
        # 使用 streamGenerateContent 端点
        api_url = f"{GEMINI_API_ENDPOINT}/v1beta/models/{MODEL_NAME}:streamGenerateContent?key={API_KEY}&alt=sse"
        
        clash_proxy_url = os.getenv('CLASH_PROXY_URL')
        curl_command_base = ["curl", "-s", "-N", "-X", "POST", "-H", "Content-Type: application/json"]
        if clash_proxy_url:
            curl_command_base.extend(["-x", clash_proxy_url])
        curl_command = curl_command_base + [api_url, "--data", json.dumps(request_payload), "--output", STREAM_FILE]

        try:
            process = subprocess.Popen(curl_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            write_file_content(PID_FILE, str(process.pid))
        except Exception as e_popen:
            output_for_text_view["response"] = f"ERROR starting curl: {e_popen}"
            print(json.dumps(output_for_text_view))
            return

        output_for_text_view["response"] = assistant_signature() + "思考中..."
        output_for_text_view["rerun"] = 0.2
        output_for_text_view["variables"]["streaming_now_alfred"] = "true"
        # 保存原始的 actual_user_query 和 selected_mode_id 可能比保存完整 prompt 好
        output_for_text_view["variables"]["user_query_original_alfred"] = actual_user_query 
        output_for_text_view["variables"]["mode_id_original_alfred"] = selected_mode_id
        output_for_text_view["variables"]["last_stream_file_size_alfred"] = "0"
        output_for_text_view["behaviour"] = {"response": "replace", "scroll": "end"}

    elif is_streaming_now: # Rerun 调用
        # 从环境变量恢复上次保存的状态
        # last_stream_file_size 已经从环境变量获取了

        current_stream_file_size = 0
        try:
            current_stream_file_size = os.path.getsize(STREAM_FILE)
        except FileNotFoundError: pass

        new_content_raw = ""
        if current_stream_file_size > last_stream_file_size:
            with open(STREAM_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_stream_file_size)
                new_content_raw = f.read()
        
        new_text_chunk = parse_gemini_sse_stream_for_new_text(new_content_raw)
        accumulated_text = read_file_content(ACCUMULATED_TEXT_FILE)
        
        if new_text_chunk:
            accumulated_text += new_text_chunk
            write_file_content(ACCUMULATED_TEXT_FILE, accumulated_text)

        pid = read_file_content(PID_FILE).strip()
        process_is_alive = is_process_running(pid)
        stream_has_ended_by_marker = check_stream_ended_from_chunk(new_content_raw)
        
        display_text = assistant_signature() + accumulated_text
        
        output_for_text_view["response"] = display_text # Text View 的内容
        
        # 构建下一次 rerun 的 variables
        current_variables = {
            "streaming_now_alfred": "true",
            "user_query_original_alfred": actual_user_query, # 使用已从env恢复的变量
            "mode_id_original_alfred": selected_mode_id,       # 使用已从env恢复的变量
            "last_stream_file_size_alfred": str(current_stream_file_size)
        }
        output_for_text_view["variables"] = current_variables
        output_for_text_view["behaviour"] = {"response": "replace", "scroll": "end"}

        if stream_has_ended_by_marker or not process_is_alive:
            output_for_text_view["variables"]["streaming_now_alfred"] = "false"
            delete_file_if_exists(STREAM_FILE)
            delete_file_if_exists(PID_FILE)
            if not process_is_alive and not stream_has_ended_by_marker:
                 output_for_text_view["response"] += "\n[连接中断或进程意外结束]"
        else:
            output_for_text_view["rerun"] = 0.2 # Alfred 5.x Text View JSON 顶层可以有 rerun
            if process_is_alive : output_for_text_view["response"] += "..."
    else:
        output_for_text_view["response"] = "请输入您的问题 (例如 '解释 资本主义' 或通过模式选择)..."
        output_for_text_view["variables"]["streaming_now_alfred"] = "false"

    print(json.dumps(output_for_text_view))

if __name__ == '__main__':
    try:
        main()
    except Exception as e_main:
        error_output = {
            "response": f"脚本发生严重错误:\n{type(e_main).__name__}: {str(e_main)}\n\nTraceback:\n{traceback.format_exc()}",
            "variables": {"streaming_now_alfred": "false"}
        }
        print(json.dumps(error_output))
        delete_file_if_exists(STREAM_FILE)
        delete_file_if_exists(PID_FILE)
        # delete_file_if_exists(MODE_AND_QUERY_FILE)