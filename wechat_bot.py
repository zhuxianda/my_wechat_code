#!/usr/bin/env python3
# wechat_bot.py - 微信机器人
# 基于 WCF HTTP API 和 OpenRouter API 开发的聊天机器人

import json
import time
import requests
import os
import re
from datetime import datetime
import chat  # 导入chat.py模块
import uuid
import base64
from chat import send_message
from save3 import svg_to_image
import sys

# 配置
CONFIG_FILE = 'config.json'
MESSAGES_FILE = 'messages.json'
API_BASE_URL = 'http://47.112.191.107:8000'

def load_config():
    """加载配置文件"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            config = json.load(file)
            print("配置文件加载成功")
            return config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return None

def save_messages(messages):
    """保存消息到本地JSON文件"""
    try:
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as file:
            json.dump(messages, file, ensure_ascii=False, indent=2)
            return True
    except Exception as e:
        print(f"保存消息失败: {e}")
        return False

def load_messages():
    """从本地JSON文件加载消息"""
    try:
        if os.path.exists(MESSAGES_FILE):
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        return []
    except Exception as e:
        print(f"加载消息失败: {e}")
        return []

def get_message(api_key, block=True):
    """从微信API获取消息"""
    try:
        # 检查文档中是否有新的端点，目前仍然使用get-msg，但如有变更请更新
        url = f"{API_BASE_URL}/get-msg"
        params = {"block": block}
        headers = {"X-API-KEY": api_key}
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"获取消息失败: {e}")
        return None

def subscribe_to_sse(api_key):
    """订阅微信消息，使用Server-Sent Events (SSE)方式接收持续推送"""
    try:
        print("开始SSE订阅消息流...")
        url = f"{API_BASE_URL}/subscribe"
        headers = {"X-API-KEY": api_key, "Accept": "text/event-stream"}
        
        # 创建一个流式请求
        response = requests.get(url, headers=headers, stream=True)
        
        # 检查连接状态
        if response.status_code == 401 or response.status_code == 403:
            print(f"API密钥验证失败，请确保WCF API密钥正确 (状态码: {response.status_code})")
            time.sleep(5)
            return None
            
        response.raise_for_status()
        print("SSE连接已建立，开始监听消息流")
        
        # 直接返回流式响应
        return response
    except requests.exceptions.ConnectionError:
        print(f"连接到API服务器失败，请确保API服务 {API_BASE_URL} 可访问")
        time.sleep(5)
        return None
    except Exception as e:
        print(f"创建SSE订阅失败: {e}")
        print(f"异常类型: {type(e).__name__}")
        import traceback
        print(f"异常堆栈: {traceback.format_exc()}")
        time.sleep(2)
        return None

def process_sse_events(response, config, messages):
    """处理SSE事件流"""
    if not response:
        return
    
    # 缓存用于处理分块消息
    buffer = ""
    
    try:
        # 遍历响应流中的每一行
        for line in response.iter_lines(decode_unicode=True):
            if line:
                # 过滤掉"data: "前缀并处理
                if line.startswith('data: '):
                    data_str = line[6:]  # 删除"data: "前缀
                    if data_str.strip():
                        try:
                            # 解析JSON数据
                            data = json.loads(data_str)
                            #print(f"收到SSE事件: {json.dumps(data, ensure_ascii=False)[:200]}...")
                            
                            # 添加更美观的数据输出
                            # print("\n" + "="*50)
                            # print(f"收到新消息 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            # print("-"*50)
                            
                            # 提取关键信息并格式化输出
                            # if "type" in data:
                            #     msg_type = data.get("type")
                            #     type_text = "文本消息" if msg_type == 1 else f"其他类型消息({msg_type})"
                            #     print(f"消息类型: {type_text}")
                            
                            # if "sender" in data:
                            #     print(f"发送者ID: {data.get('sender')}")
                                
                            # if "sender_name" in data:
                            #     print(f"发送者昵称: {data.get('sender_name')}")
                            
                            # if "roomid" in data:
                            #     print(f"群组ID: {data.get('roomid')}")
                                
                            # if "content" in data:
                            #     content = data.get("content", "")
                            #     print(f"消息内容: {content}")
                            
                            # # 打印完整JSON（美化格式）
                            # print("-"*50)
                            # print("完整数据:")
                            # print(json.dumps(data, ensure_ascii=False, indent=2))
                            # print("="*50)
                            
                            # 处理消息数据
                            if "id" in data and "type" in data and "sender" in data and "content" in data:
                                msg = data
                                
                                # 保存消息到本地
                                if "timestamp" not in msg:
                                    msg["timestamp"] = int(time.time())
                                if "datetime" not in msg:
                                    msg["datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                messages.append(msg)
                                
                                save_messages(messages)
                                
                                # 处理消息
                                process_message(msg, config, messages)
                            else:
                                # 可能是心跳或其他类型的事件
                                print(f"收到非标准消息格式或事件: {data}")
                        except json.JSONDecodeError as e:
                            print(f"解析SSE事件JSON失败: {e}")
                            print(f"原始事件数据: {data_str[:100]}...")
            else:
                # 空行可能是心跳消息或事件的分隔符
                pass
                
    except requests.exceptions.ChunkedEncodingError as e:
        print(f"SSE流读取中断: {e}")
        raise
    except Exception as e:
        print(f"处理SSE事件失败: {e}")
        import traceback
        print(f"异常堆栈: {traceback.format_exc()}")
        raise

def send_text_message(api_key, msg, receiver, aters=None):
    """发送文本消息"""
    try:
        url = f"{API_BASE_URL}/send-text"
        headers = {"X-API-KEY": api_key}
        data = {
            "msg": msg,
            "receiver": receiver
        }
        if aters:
            data["aters"] = aters
        
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        print("================")
        print(data)
        print("================")
        return response.json()
    except Exception as e:
        print(f"发送消息失败: {e}")
        return None

def get_self_wxid(api_key):
    """获取自己的微信ID"""
    try:
        url = f"{API_BASE_URL}/get-self-wxid"
        headers = {"X-API-KEY": api_key}
        response = requests.get(url, headers=headers)
        
        # 确保正确处理响应编码
        response.encoding = 'utf-8'
        
        # 检查HTTP状态码
        if response.status_code == 401 or response.status_code == 403:
            print(f"API密钥验证失败，请确保WCF API密钥正确 (状态码: {response.status_code})")
            return None
        
        response.raise_for_status()
        
        # 尝试解析JSON
        try:
            result = response.json()
        except Exception as e:
            print(f"解析响应JSON失败: {e}")
            print(f"原始响应内容: {response.text[:100]}...")
            return None
            
        if result.get("status") == "ok":
            return result.get("data")
        else:
            print(f"获取微信ID失败，API返回: {result}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"连接到API服务器失败，请确保API服务 {API_BASE_URL} 可访问")
        return None
    except Exception as e:
        print(f"获取微信ID失败: {e}")
        return None

def is_target_message(msg, group_id, prefixes=["#真实", "#毒舌"]):
    """判断是否是目标消息"""
    # 检查消息类型是否为文本消息
    if msg.get("type") != 1:  # 文本消息类型通常为1
        return False
    
    # 检查是否来自目标群
    room_id = msg.get("roomid")
    if not room_id or (isinstance(group_id, list) and room_id not in group_id) or (not isinstance(group_id, list) and room_id != group_id):
        return False
    
    # 检查消息内容是否以任一指定前缀开头
    content = msg.get("content", "")
    for prefix in prefixes:
        if content.startswith(prefix):
            return prefix  # 返回匹配到的前缀
    
    return False

def process_message(msg, config, messages=None):
    """处理接收到的消息"""
    # 获取配置信息
    api_key = config.get("api_key", "")  # OpenRouter API密钥
    wcf_api_key = config.get("wcf_api_key", "")  # 微信HTTP API密钥
    target_group = config.get("group", "")
    bot_name = config.get("bot_name", "")
    at_me_prefix = config.get("AtMe", "@")
    
    # 检查是否是目标消息，并获取匹配的前缀
    matched_prefix = is_target_message(msg, target_group, ["#真实", "#毒舌"])
    if not matched_prefix:
        return
    
    print(f"有进来 数据 处理消息: {msg}")

    # 获取发送者信息
    sender_wxid = msg.get("sender", "")
    room_id = msg.get("roomid", "")
    
    # 获取消息内容并去除前缀
    content = msg.get("content", "")
    content = content.replace(matched_prefix, "", 1).strip()
    
    # 设置prompt_type
    prompt_type = "normal"
    if matched_prefix == "#毒舌":
        prompt_type = "ds"
    elif matched_prefix == "#真实":
        prompt_type = "zs"
    
    # 调用AI获取回复
    print(f"处理消息: {content} (类型: {prompt_type})")
    # 发送正在思考的消息
    notify_msg = f"{at_me_prefix}{sender_wxid} 正在思考中..."
    send_text_message(wcf_api_key, notify_msg, room_id, sender_wxid)
    
    # 获取最近5分钟的聊天历史
    chat_history = []
    if messages is not None:
        chat_history = get_recent_chat_history(messages, room_id, minutes=5)
        print(f"找到{len(chat_history)}条最近的聊天记录作为上下文")
    
    # 使用不同的prompt_type调用AI，并传递聊天历史
    ai_responses = chat.send_message(content, prompt_type=prompt_type, history_messages=chat_history)
    if not ai_responses or len(ai_responses) == 0:
        # 发送错误消息
        error_msg = f"{at_me_prefix}{sender_wxid} 抱歉，AI服务暂时不可用，请稍后再试。"
        send_text_message(wcf_api_key, error_msg, room_id, sender_wxid)
        return
    
    ai_reply = ai_responses[0]
    
    # 检查回复是否为SVG内容
    if ai_reply and (ai_reply.strip().startswith("<svg") or "<svg " in ai_reply):
        try:
            # 发送一条简短的文本消息通知用户
            notify_msg = f"{at_me_prefix}{sender_wxid} 正在生成图像回复..."
            send_text_message(wcf_api_key, notify_msg, room_id, sender_wxid)
            
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"ai_response_{timestamp}_{unique_id}.svg"
            
            # 保存SVG文件
            svg_file_path = svg_to_image(ai_reply, output_dir="output", filename=filename)
            
            # 提取SVG前后可能存在的文本
            start_index = ai_reply.find("<svg")
            end_index = ai_reply.rfind("</svg>") + 6
            
            # 发送SVG前面的文本（如果有）
            if start_index > 0:
                before_svg = ai_reply[:start_index].strip()
                if before_svg:
                    before_msg = f"{at_me_prefix}{sender_wxid} {before_svg}"
                    send_text_message(wcf_api_key, before_msg, room_id, sender_wxid)
            
            # 尝试发送SVG文件
            try:
                # 读取SVG文件内容
                with open(svg_file_path, "rb") as svg_file:
                    svg_data = base64.b64encode(svg_file.read()).decode('utf-8')
                
                # 发送SVG作为文件
                send_file(wcf_api_key, svg_data, filename, room_id)
                print(f"已发送SVG文件: {svg_file_path}")
                
                # 发送SVG后面的文本（如果有）
                if end_index < len(ai_reply) - 1:
                    after_svg = ai_reply[end_index:].strip()
                    if after_svg:
                        after_msg = f"{at_me_prefix}{sender_wxid} {after_svg}"
                        send_text_message(wcf_api_key, after_msg, room_id, sender_wxid)
                
                return
            except Exception as e:
                print(f"发送SVG文件失败: {e}")
                # 如果发送文件失败，尝试发送图片
                try:
                    with open(svg_file_path, "rb") as img_file:
                        image_data = base64.b64encode(img_file.read()).decode('utf-8')
                    
                    # 发送图像
                    send_image(wcf_api_key, image_data, os.path.basename(svg_file_path), room_id)
                    print(f"已发送SVG作为图像: {svg_file_path}")
                    return
                except Exception as e2:
                    print(f"发送SVG作为图像也失败: {e2}")
        except Exception as e:
            print(f"处理SVG图像时出错: {e}")
            # 如果处理SVG出错，仍然发送文本回复
    
    # 构建回复消息，添加@发送者
    reply = f"{at_me_prefix}{sender_wxid} {ai_reply}"
    
    # 发送回复
    send_result = send_text_message(wcf_api_key, reply, room_id, sender_wxid)
    print(f"发送回复结果: {send_result}")

def send_image(api_key, image_data, filename, receiver):
    """发送图片消息"""
    try:
        url = f"{API_BASE_URL}/send-image"
        headers = {"X-API-KEY": api_key}
        data = {
            "image_data": image_data,
            "filename": filename,
            "receiver": receiver
        }
        
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"发送图片失败: {e}")
        return None

def send_file(api_key, file_data, filename, receiver):
    """发送文件消息"""
    try:
        url = f"{API_BASE_URL}/send-file"
        headers = {"X-API-KEY": api_key}
        data = {
            "file_data": file_data,
            "filename": filename,
            "receiver": receiver
        }
        
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"发送文件失败: {e}")
        return None

def get_recent_chat_history(messages, room_id, minutes=2):
    """
    获取最近几分钟内的聊天历史
    
    参数:
        messages (list): 消息列表
        room_id (str): 群组ID
        minutes (int): 获取几分钟之内的消息，默认为5分钟
    
    返回:
        list: 格式化后的最近聊天记录，用于AI模型的历史消息
    """
    if not messages:
        return []
    
    # 获取当前时间的时间戳
    current_time = int(time.time())
    # 计算几分钟前的时间戳
    time_threshold = current_time - (minutes * 60)
    
    # 筛选出最近几分钟内指定群组的消息
    recent_messages = []
    for msg in reversed(messages):  # 从最新的消息开始遍历
        # 跳过非目标群组的消息
        if msg.get("roomid") != room_id:
            continue
            
        # 检查消息时间是否在指定范围内
        msg_timestamp = msg.get("timestamp", 0)
        if msg_timestamp < time_threshold:
            break  # 如果消息时间早于阈值，停止遍历
            
        # 仅添加文本消息
        if msg.get("type") == 1:  # 文本消息类型
            recent_messages.append(msg)
    
    # 因为是从新到旧遍历的，所以需要反转列表
    recent_messages.reverse()
    
    # 格式化消息，转换为AI模型需要的格式
    formatted_history = []
    for msg in recent_messages:
        sender_name = msg.get("sender", "用户")
        content = msg.get("content", "")
        
        # 检查并去除消息前缀（如#真实、#毒舌等）
        for prefix in ["#真实", "#毒舌"]:
            if content.startswith(prefix):
                content = content.replace(prefix, "", 1).strip()
                break
                
        formatted_history.append({
            "role": "user",
            "content": f"{sender_name}: {content}"
        })
    
    return formatted_history

def main():
    """主函数"""
    print("微信机器人启动中...")
    print("=" * 50)
    
    # 加载配置
    config = load_config()
    if not config:
        print("错误: 无法加载配置文件，请确保config.json存在且格式正确")
        return
        
    api_key = config.get("api_key", "")  # OpenRouter API密钥
    wcf_api_key = config.get("wcf_api_key", "")  # 微信HTTP API密钥
    target_group = config.get("group", "")
    test_mode = config.get("test_mode", False)  # 测试模式
    
    if not api_key:
        print("错误: 未找到OpenRouter API密钥，请检查配置文件")
        return
    
    if not test_mode and (not wcf_api_key or wcf_api_key == "在这里填入有效的微信API密钥"):
        print("错误: 未找到有效的微信HTTP API密钥，请在config.json中设置wcf_api_key")
        print("获取API密钥: http://47.112.191.107:8000")
        print("\n如果您只想测试流程，可以在config.json中添加 \"test_mode\": true 启用测试模式")
        return
        
    if test_mode:
        print("⚠️ 测试模式已启用 - 将模拟微信API响应")
    
    if not target_group:
        print("警告: 未设置目标群组，机器人将响应所有带有前缀的消息")
    else:
        print(f"机器人将监听群组: {target_group}")
    
    # 获取自己的微信ID
    print("正在连接微信API服务...")
    
    if test_mode:
        # 测试模式模拟微信ID
        self_wxid = "test_wxid_123456"
        print("测试模式: 已模拟微信ID")
    else:
        # 实际获取微信ID
        self_wxid = get_self_wxid(wcf_api_key)
        if not self_wxid:
            print("错误: 无法获取微信ID，请检查API密钥是否正确")
            return
    
    print("-" * 50)
    print(f"机器人微信ID: {self_wxid}")
    print(f"AI模型: {config.get('model1', '未指定')}")
    print(f"消息前缀: #真实")
    print("-" * 50)
    print("开始监听消息...")
    
    # 加载历史消息
    messages = load_messages()
    
    max_reconnect_delay = 30
    reconnect_delay = 1
    
    try:
        if test_mode:
            # 测试模式下模拟接收消息
            print("模拟等待新消息中...")
            # time.sleep(10)
            # print("收到模拟测试消息!")
            
            # # 创建一个模拟消息
            # test_msg = {
            #     "id": 12345,
            #     "type": 1,  # 文本消息
            #     "sender": "wxid_test_sender",
            #     "content": "#真实 你好，这是一条测试消息",
            #     "roomid": target_group[0] if isinstance(target_group, list) else target_group or "test_group_id",
            #     "timestamp": int(time.time()),
            #     "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # }
            
            # # 保存消息
            # messages.append(test_msg)
            # save_messages(messages)
            
            # # 处理模拟消息
            # print("处理消息...")
            # process_message(test_msg, config)
            
            # # 处理模拟消息
            # print("处理消息...")
            # process_message(test_msg, config, messages)
        else:
            # 实际模式下使用SSE接收消息
            while True:
                try:
                    # 创建SSE连接
                    sse_response = subscribe_to_sse(wcf_api_key)
                    
                    if sse_response:
                        # 重置重连延迟
                        reconnect_delay = 1
                        
                        # 处理SSE事件流
                        process_sse_events(sse_response, config, messages)
                    else:
                        # SSE连接失败，延迟后重试
                        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                        print(f"无法建立SSE连接，{reconnect_delay}秒后重试...")
                        time.sleep(reconnect_delay)
                except KeyboardInterrupt:
                    raise  # 将键盘中断传递给外层try-except块
                except requests.exceptions.ConnectionError as e:
                    print(f"SSE连接中断: {e}")
                    reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                    print(f"连接中断，{reconnect_delay}秒后重新连接...")
                    time.sleep(reconnect_delay)
                except Exception as e:
                    print(f"SSE监听过程中发生异常: {e}")
                    import traceback
                    print(f"异常堆栈: {traceback.format_exc()}")
                    reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                    print(f"发生异常，{reconnect_delay}秒后重试...")
                    time.sleep(reconnect_delay)
    except KeyboardInterrupt:
        print("\n用户中断，程序停止")
    except Exception as e:
        print(f"发生严重异常: {e}")
    finally:
        # 保存消息
        save_messages(messages)
        print("已保存所有消息")
        print("程序已退出")

if __name__ == "__main__":
    main() 