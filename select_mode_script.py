#!/usr/bin/env python3
import sys
import json

PROMPT_DEFINITIONS = [
    {"id": "explain", "title": "解释词义", "subtitle": "用大白话解释..."},
    {"id": "translate_en", "title": "翻译成英文", "subtitle": "将内容翻译成英文..."},
    {"id": "translate_zh", "title": "翻译成中文", "subtitle": "将内容翻译成中文..."},
    {"id": "movie_summary", "title": "电影简介", "subtitle": "提供电影剧情简介..."},
    {"id": "custom_prompt", "title": "自定义提示", "subtitle": "直接发送您的输入..."}
]

# 定义一个 Keyword，用于在选择模式后，让用户输入具体查询
# 这个 Keyword 用户通常不会直接输入，而是由上一步的 Script Filter 自动触发
QUERY_INPUT_KEYWORD = "_askai" 

def main():
    items = []
    for mode in PROMPT_DEFINITIONS:
        items.append({
            "uid": mode["id"], 
            "title": mode["title"], 
            "subtitle": mode["subtitle"],
            "arg": mode["id"], # arg 就是选中的模式ID
            "variables": { # 将模式的友好名称也保存一下，用于下一个界面的提示
                "selected_mode_title_internal": mode["title"]
            },
            "valid": True
        })
    print(json.dumps({"items": items}))

if __name__ == "__main__":
    main()