# -*- coding: utf-8 -*-
import os
import argparse
import subprocess
from datetime import datetime, timedelta

def check_and_run_pipeline(categories, target_date):
    """
    检查指定日期的文件是否存在，如果不存在，则运行完整的处理流程。
    """
    date_str = target_date.strftime('%Y-%m-%d')
    categories_str = '-'.join(categories).replace('.', '')
    
    # 检查是否存在已总结的文件（这是最理想的状态）
    # 注意：这里我们只检查基础文件名格式，因为关键词是可选的。
    # 一个更稳健的方法是扫描所有可能的文件名。
    
    # 扫描目录，查找匹配的文件
    found = False
    pattern_prefix = f"arxiv_{categories_str}"
    pattern_suffix = f"_{date_str}.csv"
    
    for filename in os.listdir('.'):
        if filename.startswith(pattern_prefix) and filename.endswith(pattern_suffix):
            print(f"[{date_str} | {', '.join(categories)}]：文件 '{filename}' 已存在，视为已完成建档。")
            found = True
            break # 找到一个匹配的就足够了

    if not found:
        print(f"[{date_str} | {', '.join(categories)}]：未找到存档文件，启动处理流程...")
        
        # --- 第1步: 调用 arxiv_daily_fetcher.py ---
        print(f"--> 步骤 1: 正在抓取 {date_str} 的论文...")
        fetcher_cmd = [
            'python',
            'arxiv_daily_fetcher.py',
            '--categories', *categories,
            '--date', date_str
        ]
        
        try:
            # 使用 check=True 会在命令返回非零退出码时抛出异常
            subprocess.run(fetcher_cmd, check=True, text=True, capture_output=True)
            print(f"--> 步骤 1: 论文抓取成功。")
        except subprocess.CalledProcessError as e:
            print(f"错误：调用 arxiv_daily_fetcher.py 失败。返回码: {e.returncode}")
            print(f"错误输出:\n{e.stderr}")
            return # 如果第一步失败，则终止后续流程
        except FileNotFoundError:
            print("错误：找不到 'python' 命令或 'arxiv_daily_fetcher.py' 脚本。")
            return

        # --- 第2步: 调用 summarize_by_zai.py ---
        print(f"--> 步骤 2: 正在为 {date_str} 的论文生成AI总结...")
        summarizer_cmd = [
            'python',
            'summarize_by_zai.py',
            '--categories', *categories,
            '--date', date_str
        ]
        
        try:
            subprocess.run(summarizer_cmd, check=True, text=True, capture_output=True)
            print(f"--> 步骤 2: AI总结生成并保存成功。")
        except subprocess.CalledProcessError as e:
            print(f"错误：调用 summarize_by_zai.py 失败。返回码: {e.returncode}")
            print(f"错误输出:\n{e.stderr}")
            return
        except FileNotFoundError:
            print("错误：找不到 'python' 命令或 'summarize_by_zai.py' 脚本。")
            return
        
        print(f"[{date_str} | {', '.join(categories)}]：处理流程已成功完成。")

def main():
    """
    主函数，解析参数并按天执行流程。
    """
    parser = argparse.ArgumentParser(description="自动化arXiv论文抓取和总结的流程。")
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
        help="要处理的特定日期 (格式: 'YYYY-MM-DD') 或日期范围 (格式: 'YYYY-MM-DD:YYYY-MM-DD')。如果未提供，则默认为昨天。"
    )
    
    args = parser.parse_args()
    
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

    print(f"--- 开始执行自动化流程 --- ")
    print(f"监控领域: {', '.join(args.categories)}")
    print(f"处理日期范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    print("---------------------------\n")

    # 遍历日期范围内的每一天
    current_date = start_date
    while current_date <= end_date:
        check_and_run_pipeline(args.categories, current_date)
        current_date += timedelta(days=1)
        print("\n") # 每天的处理之间加个换行

    print("--- 所有日期的检查和处理已完成 ---")

if __name__ == "__main__":
    main()