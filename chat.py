#!/usr/bin/env python3
# chat.py - DeepSeek API 接口封装
# 作者：基于 Siver 微信机器人代码111
# 达达的测试

import json
import traceback
from openai import OpenAI
import os
import tempfile
from pathlib import Path
import html
# 导入 svg_to_image 函数
from save3 import svg_to_image

#
# 配置文件路径
CONFIG_FILE = 'config.json'

def load_config():
    """从配置文件加载配置"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            config = json.load(file)
            print("配置文件加载成功")
            return config
    except Exception as e:
        print("打开配置文件失败，请检查配置文件！", e)
        return {}

def split_long_text(text, chunk_size=2000):
    """将长文本分割成多个小段"""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def deepseek_chat(message, model=None, stream=True, prompt=None, config=None, prompt_type=None):
    """
    调用 DeepSeek API 获取对话回复

    参数:
        message (str): 用户输入的消息
        model (str): 使用的模型标识，如果为None则使用配置中的model1
        stream (bool): 是否使用流式输出
        prompt (str): 系统提示词，如果为None则使用配置中的prompt
        config (dict): 配置字典，如果为None则从文件加载
        prompt_type (str): 提示词类型，可选值为'default'、'ds'或'hh'，默认为'default'

    返回:
        str: AI 返回的回复
    """
    if config is None:
        config = load_config()
    
    # 根据prompt_type选择不同的提示词
    if prompt is None:
        if prompt_type == 'ds':
            prompt = config.get('prompt_ds', "")
        elif prompt_type == 'zs':
            prompt = config.get('prompt_zs', "")
        else:
            prompt = config.get('prompt', "")
    
    # 如果未指定模型或提示词，则使用配置中的默认值
    if model is None:
        model = config.get('model1', "")
    
    # 初始化 OpenAI 客户端
    client = OpenAI(
        api_key=config.get('api_key', ""),
        base_url=config.get('base_url', "")
    )
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message},
            ],
            stream=stream
        )
    except Exception as e:
        print("调用 DeepSeek API 出错:", e)
        print(traceback.format_exc())
        return "API返回错误，请稍后再试"

    # 流式输出处理
    if stream:
        reasoning_content = ""  # 思维链内容
        content = ""  # 回复内容    
        for chunk in response: 
            if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                # 判断是否为思维链
                chunk_message = chunk.choices[0].delta.reasoning_content  # 获取思维链
                print(chunk_message, end="", flush=True)  # 打印思维链
                if chunk_message:
                    reasoning_content += chunk_message  # 累加思维链
            else:
                chunk_message = chunk.choices[0].delta.content  # 获取回复
                print(chunk_message, end="", flush=True)  # 打印回复
                if chunk_message: 
                    content += chunk_message  # 累加回复
                
        print("\n")
        return content.strip()  # 返回回复内容
    else:
        output = response.choices[0].message.content  # 获取回复内容
        #print(output)  # 打印回复
        return output  # 返回回复内容

def send_message(message, prompt_type="normal"):
    
    config = load_config()
    try:
        reply = deepseek_chat(message, config.get('model1', ""), config=config, prompt=prompt_type)
        
        # 处理长回复
        if len(reply) >= 18000:
            segments = split_long_text(reply)
            return segments
        else:
            return [reply]
    except Exception as e:
        print("发送消息时出错:", e)
        print(traceback.format_exc())
        return ["API返回错误，请稍后再试"]

# 简单的命令行测试
if __name__ == "__main__":
    print("Chat API 测试")

    response = send_message("为什么你要这样做？", prompt_type="truthful")
    print(response[0])

    # 将文本转换为SVG并保存
    svg_content = response[0]
    output_path = svg_to_image(svg_content, output_dir="output")

    # 打印保存的文件路径
    print("\n保存的文件:")
    print(f"图片已保存到: {output_path}")