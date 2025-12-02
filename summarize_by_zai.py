# -*- coding: utf-8 -*-
import os
import pandas as pd
import argparse
from datetime import datetime, timedelta
from zai import ZhipuAiClient
from tqdm import tqdm

# --- 配置区域 ---
# 请在这里填入您的智谱AI API Key
API_KEY = ""
# --- 配置区域结束 ---

def get_summary_from_zai(client, title, abstract):
    """
    调用智谱AI API为单篇论文生成摘要。
    """
    prompt = f"请用一小段话总结以下论文的核心内容，内容包括标题和摘要：\n\n标题：{title}\n\n摘要：{abstract}。注意，总结段落需要包括你认为的核心方法和创新点，仅输出一段总结文字即可。"
    
    try:
        response = client.chat.completions.create(
            model="glm-4.5-flash",  # 免费模型参考：https://docs.bigmodel.cn/cn/guide/models/free/
            messages=[
                {
                    "role": "system",
                    "content": "你是一个精通科研论文的AI助手，擅长根据论文标题和摘要，将复杂的论文内容总结为一小段通俗易懂又不失专业性的话。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            thinking={
                "type": "enabled",    # 启用深度思考模式
            },
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"调用API失败: {e}"

def find_csv_files(categories, start_date, end_date):
    """
    根据类别和日期范围查找匹配的CSV文件。
    """
    found_files = []
    cat_str = '-'.join(categories).replace('.', '')
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        # 匹配 arxiv_{categories}_{date}.csv 和 arxiv_{categories}_keywords_{...}_{date}.csv 格式
        pattern_prefix = f"arxiv_{cat_str}"
        pattern_suffix = f"_{date_str}.csv"
        
        for filename in os.listdir('.'):
            if filename.startswith(pattern_prefix) and filename.endswith(pattern_suffix):
                found_files.append(filename)
        
        current_date += timedelta(days=1)
        
    return list(set(found_files)) # 去重

def process_file(client, filepath):
    """
    处理单个CSV文件，为其添加摘要列。
    """
    print(f"\n正在处理文件: {filepath}")
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"错误：文件 {filepath} 未找到。")
        return

    if 'summarization' in df.columns:
        print("检测到 'summarization' 列，将跳过已有内容的行。")
        # 创建一个待处理的子集，只包含summarization为空的行
        to_process_df = df[df['summarization'].isnull() | (df['summarization'] == '')]
    else:
        df['summarization'] = ''
        to_process_df = df

    if to_process_df.empty:
        print("文件中所有论文都已有总结，无需处理。")
        return

    print(f"共需要为 {len(to_process_df)} 篇论文生成总结...")
    
    # 使用tqdm显示进度条
    for index, row in tqdm(to_process_df.iterrows(), total=len(to_process_df), desc="生成总结"):
        title = row['title']
        summary = row['summary']
        
        # 调用API获取总结
        one_sentence_summary = get_summary_from_zai(client, title, summary)
        
        # 将总结写回原始DataFrame的对应位置
        df.loc[index, 'summarization'] = one_sentence_summary

    # 保存更新后的DataFrame到原文件
    try:
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"文件 {filepath} 已成功更新并保存。")
    except Exception as e:
        print(f"保存文件 {filepath} 时出错: {e}")

def main():
    """
    主函数，解析参数并执行摘要生成任务。
    """
    parser = argparse.ArgumentParser(description="使用智谱AI为arXiv论文CSV文件生成一句话总结。")
    parser.add_argument(
        '--categories', 
        nargs='+', 
        required=True, 
        help="一个或多个arXiv研究领域代码 (例如: cs.AI stat.ML)。"
    )
    parser.add_argument(
        '--date', 
        type=str, 
        default=None, 
        help="要搜索的特定日期 (格式: 'YYYY-MM-DD') 或日期范围 (格式: 'YYYY-MM-DD:YYYY-MM-DD')。如果未提供，则默认为昨天。"
    )
    
    args = parser.parse_args()
    
    if API_KEY == "YOUR_API_KEY":
        print("错误：请在脚本中设置您的 ZhipuAiClient API_KEY。")
        exit()

    # 解析日期
    if args.date:
        if ':' in args.date:
            try:
                start_str, end_str = args.date.split(':')
                start_date = datetime.strptime(start_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_str, '%Y-%m-%d')
            except ValueError:
                print("错误：日期范围格式不正确。请使用 'YYYY-MM-DD:YYYY-MM-DD' 格式。")
                exit()
        else:
            try:
                start_date = end_date = datetime.strptime(args.date, '%Y-%m-%d')
            except ValueError:
                print("错误：日期格式不正确。请使用 'YYYY-MM-DD' 格式。")
                exit()
    else:
        start_date = end_date = datetime.now() - timedelta(days=1)

    print(f"将在 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 的日期范围内为领域 {', '.join(args.categories)} 查找文件。")

    # 查找相关文件
    csv_files = find_csv_files(args.categories, start_date, end_date)
    
    if not csv_files:
        print("未找到任何匹配的CSV文件。")
        return

    print(f"找到以下文件进行处理: {', '.join(csv_files)}")

    # 初始化AI客户端
    client = ZhipuAiClient(api_key=API_KEY)

    # 逐个处理文件
    for filepath in csv_files:
        process_file(client, filepath)

    print("\n--- 所有任务已完成 ---")

if __name__ == "__main__":
    main()