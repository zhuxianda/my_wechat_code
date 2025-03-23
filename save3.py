#!/usr/bin/env python3
# save3.py - SVG处理工具
# 用于保存SVG内容到文件

import os
import time
from datetime import datetime
from pathlib import Path

def svg_to_image(svg_content, output_dir="output", filename=None):
    """
    将SVG内容保存为svg文件
    
    参数:
        svg_content (str): SVG内容
        output_dir (str): 输出目录
        filename (str): 文件名，如果为None则自动生成
        
    返回:
        str: 保存的文件路径
    """
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 生成时间戳作为文件名
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"svg_output_{timestamp}.svg"
    elif not filename.endswith(".svg"):
        filename = f"{filename}.svg"
    
    output_path = os.path.join(output_dir, filename)
    
    try:
        # 检查SVG内容是否有效
        if svg_content and (svg_content.strip().startswith("<svg") or "<svg " in svg_content):
            # 提取SVG内容（如果它嵌入在其他内容中）
            start_index = svg_content.find("<svg")
            end_index = svg_content.rfind("</svg>") + 6  # 包含结束标签
            
            if start_index >= 0 and end_index > 0:
                svg_content = svg_content[start_index:end_index]
            
            # 保存SVG文件
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
            
            print(f"SVG已保存: {output_path}")
        else:
            # 如果不是SVG内容，直接将内容保存为文本
            text_path = os.path.join(output_dir, f"{Path(filename).stem}.txt")
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
            
            print(f"内容已保存为文本: {text_path}")
            return text_path
        
        return output_path
    
    except Exception as e:
        print(f"保存SVG时出错: {e}")
        # 发生错误时，将原始内容保存为文本文件
        text_path = os.path.join(output_dir, f"{Path(filename).stem}.txt")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        
        print(f"已将原始内容保存为文本: {text_path}")
        return text_path

# 测试函数
if __name__ == "__main__":
    sample_svg = """
    <svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
        <rect width="100" height="100" fill="blue" />
        <circle cx="150" cy="100" r="50" fill="red" />
    </svg>
    """
    
    output_path = svg_to_image(sample_svg, output_dir="output", filename="test_svg")
    print(f"测试SVG已保存到: {output_path}")
    print(f"测试图像已保存到: {output_path}")