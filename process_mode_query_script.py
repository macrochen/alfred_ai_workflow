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
    "explain": "'{query_text}' 是什么意思？请用大白话给我解释一下。",
    "translate_en": "请将 '{query_text}' 翻译成英文。",
    "movie_summary": "请提供电影 '{query_text}' 的故事简介。",
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