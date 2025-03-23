# 微信聊天机器人

基于微信HTTP API和OpenRouter AI接口开发的智能聊天机器人。

## 功能特点

1. 监听微信消息并实时响应
2. 自动保存接收到的所有消息到本地JSON文件
3. 根据配置过滤特定群组和特定前缀的消息进行处理
4. 调用OpenRouter API获取AI回复
5. 自动@发送消息的用户并回复
6. **支持SVG格式回复**：自动将包含SVG内容的回复转换为图片发送

## 配置说明

机器人使用`config.json`文件进行配置，主要配置项包括：

- `api_key`: OpenRouter API密钥
- `base_url`: OpenRouter API的基础URL
- `model1`: 使用的AI模型名称
- `AtMe`: @用户的前缀格式
- `bot_name`: 机器人名称
- `group`: 目标微信群ID
- `wcf_api_key`: 微信HTTP API密钥 (获取密钥: http://47.112.191.107:8000)

## 使用方法

1. 确保配置文件`config.json`正确设置，特别是`wcf_api_key`
2. 运行机器人程序:

```bash
python3 wechat_bot.py
```

3. 在指定的微信群中，发送以"#真实"开头的消息即可触发机器人回复
4. 如果AI回复包含SVG内容，机器人会自动将其转换为图片发送

## API更新说明

本程序已更新以适配最新的微信HTTP API:
- 直接使用`/subscribe`端点订阅并获取消息
- 废弃了旧的`/enable-receiving-msg`和`/get-msg`端点
- 程序会持续通过`/subscribe`接口监听新消息

## 消息存储

所有接收到的消息会保存在`messages.json`文件中，包含以下信息：
- 发送时间
- 发送者ID
- 消息内容
- 消息类型
- 等其他微信API返回的信息

## SVG处理说明

机器人通过以下步骤处理SVG内容：

1. 检测AI回复中是否包含SVG内容
2. 将SVG内容保存为SVG文件
3. 通过WCF API发送SVG文件
4. 如果文件发送失败，尝试作为普通图片发送
5. 如果两种方式都失败，将发送原始文本内容

生成的SVG文件会保存在`output`目录中。

## 依赖库

- requests: 用于HTTP请求
- json: 用于处理JSON数据
- time: 用于时间控制
- os: 用于文件操作
- datetime: 用于时间戳转换
- uuid: 用于生成唯一文件名
- base64: 用于文件编码

## 注意事项

- 使用前需要确保微信HTTP API服务(http://47.112.191.107:8000)正常运行
- 需要有效的OpenRouter API密钥
- 机器人仅处理文本消息
- 确保`output`目录存在，用于保存生成的SVG文件
- 请记得将`config.json`中的`wcf_api_key`替换为有效的API密钥 