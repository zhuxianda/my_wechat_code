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
import datetime
# 导入 svg_to_image 函数
from save3 import svg_to_image

#
# 配置文件路径
CONFIG_FILE = 'config.json'
# 请求记录文件路径
REQUEST_LOG_FILE = 'request_log.json'

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

def print_request_info(request_data):
    """
    输出请求信息
    
    参数:
        request_data (dict): 请求数据字典，包含请求的各种信息
    """
    print("\n==== 请求信息 ====")
    print(f"请求时间: {request_data['timestamp']}")
    print(f"请求内容: {request_data['message']}")
    print(f"使用模型: {request_data['model']}")
    print(f"提示词类型: {request_data['prompt_type']}")
    if 'response' in request_data:
        print(f"响应长度: {len(request_data['response'])}")
    if 'history_messages' in request_data:
        print(f"历史消息数量: {len(request_data['history_messages'])}")
    if 'current_conversation' in request_data:
        print(f"当前对话: 用户提问 + AI回复")
    print("================\n")

def save_request_to_json(request_data):
    """
    将请求记录保存到JSON文件中（倒序存储）
    
    参数:
        request_data (dict): 请求数据字典，包含请求的各种信息
    
    返回:
        bool: 保存成功返回True，否则返回False
    """
    try:
        # 读取现有记录
        records = []
        if os.path.exists(REQUEST_LOG_FILE):
            with open(REQUEST_LOG_FILE, 'r', encoding='utf-8') as file:
                try:
                    records = json.load(file)
                except json.JSONDecodeError:
                    # 如果文件为空或格式不正确，使用空列表
                    records = []
        
        # 在列表开头添加新记录（倒序存储）
        records.insert(0, request_data)
        
        # 写入文件
        with open(REQUEST_LOG_FILE, 'w', encoding='utf-8') as file:
            json.dump(records, file, ensure_ascii=False, indent=2)
        
        print(f"请求记录已保存到 {REQUEST_LOG_FILE}")
        return True
    except Exception as e:
        print(f"保存请求记录时出错: {e}")
        print(traceback.format_exc())
        return False

def deepseek_chat(message, model=None, stream=True, prompt=None, config=None, prompt_type=None, history_messages=None):
    """
    调用 DeepSeek API 获取对话回复

    参数:
        message (str): 用户输入的消息
        model (str): 使用的模型标识，如果为None则使用配置中的model1
        stream (bool): 是否使用流式输出
        prompt (str): 系统提示词，如果为None则使用配置中的prompt
        config (dict): 配置字典，如果为None则从文件加载
        prompt_type (str): 提示词类型，可选值为'default'、'ds'或'hh'，默认为'default'
        history_messages (list): 历史消息列表，每个消息应包含role和content字段

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
    
    print("输出下 prompt : " +  prompt)
    
    # 构建消息列表
    messages = [
        {"role": "system", "content": prompt}
    ]
    
    # 添加历史消息（如果有的话）
    if history_messages and isinstance(history_messages, list):
        messages.extend(history_messages)
    
    # 添加当前用户消息
    messages.append({"role": "user", "content": message})
    
    # 创建请求数据记录
    request_data = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": message,
        "model": model,
        "prompt_type": prompt_type if prompt_type else "default",
        "system_prompt": prompt,
        "has_history": bool(history_messages)
    }
    
    # 记录历史消息
    if history_messages and isinstance(history_messages, list):
        request_data["history_messages"] = history_messages
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream
        )
    except Exception as e:
        error_msg = f"调用 DeepSeek API 出错: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        
        # 记录错误信息
        request_data["status"] = "error"
        request_data["error_message"] = error_msg
        print_request_info(request_data)
        save_request_to_json(request_data)
        
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
        
        # 记录响应信息
        request_data["status"] = "success"
        request_data["response"] = content.strip()
        if reasoning_content:
            request_data["reasoning_content"] = reasoning_content
        
        # 记录完整会话
        if history_messages is None:
            history_messages = []
        # 添加当前对话到历史
        current_conversation = [
            {"role": "user", "content": message},
            {"role": "assistant", "content": content.strip()}
        ]
        request_data["current_conversation"] = current_conversation
        
        # 输出请求信息并保存到JSON
        print_request_info(request_data)
        save_request_to_json(request_data)
        
        return content.strip()  # 返回回复内容
    else:
        output = response.choices[0].message.content  # 获取回复内容
        
        # 记录响应信息
        request_data["status"] = "success"
        request_data["response"] = output
        
        # 记录完整会话
        if history_messages is None:
            history_messages = []
        # 添加当前对话到历史
        current_conversation = [
            {"role": "user", "content": message},
            {"role": "assistant", "content": output}
        ]
        request_data["current_conversation"] = current_conversation
        
        # 输出请求信息并保存到JSON
        print_request_info(request_data)
        save_request_to_json(request_data)
        
        return output  # 返回回复内容

def send_message(message, prompt_type="normal", history_messages=None):
    """
    发送消息并获取回复
    
    参数:
        message (str): 用户输入的消息
        prompt_type (str): 提示词类型
        history_messages (list): 历史消息列表
        
    返回:
        tuple: (回复列表, 更新后的历史消息)
    """
    config = load_config()
    try:
        reply = deepseek_chat(message, config.get('model1', ""), config=config, prompt_type=prompt_type, history_messages=history_messages)
        
        # 更新历史消息
        if history_messages is None:
            history_messages = []
        
        # 添加当前对话到历史
        history_messages.append({"role": "user", "content": message})
        history_messages.append({"role": "assistant", "content": reply})
        
        # 处理长回复
        if len(reply) >= 18000:
            segments = split_long_text(reply)
            return segments, history_messages
        else:
            return [reply], history_messages
    except Exception as e:
        print("发送消息时出错:", e)
        print(traceback.format_exc())
        return ["API返回错误，请稍后再试"], history_messages

# 简单的命令行测试
if __name__ == "__main__":
    print("Chat API 测试")

    # 测试单轮对话
    response, history = send_message("为什么你要这样做？", prompt_type="truthful")
    print("单轮对话回复:", response[0])
    print(f"历史消息数量: {len(history)}")

    # 测试多轮对话
    print("\n开始多轮对话测试:")
    conversation_history = []
    
    # 第一轮对话
    response1, conversation_history = send_message("你是谁？", prompt_type="truthful", history_messages=conversation_history)
    print("\n第一轮对话完成")
    print(f"对话历史长度: {len(conversation_history)}")
    
    # 第二轮对话
    response2, conversation_history = send_message("你能做什么？", prompt_type="truthful", history_messages=conversation_history)
    print("\n第二轮对话完成")
    print(f"对话历史长度: {len(conversation_history)}")
    
    # 将文本转换为SVG并保存
    svg_content = response2[0]
    output_path = svg_to_image(svg_content, output_dir="output")

    # 打印保存的文件路径
    print("\n保存的文件:")
    print(f"图片已保存到: {output_path}")