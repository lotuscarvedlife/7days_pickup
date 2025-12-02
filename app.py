# -*- coding: utf-8 -*-
import gradio as gr
import pandas as pd
import os
import subprocess
from datetime import datetime, timedelta
import pytz

# --- 配置 ---
CATEGORIES = ['eess.AS']
DAYS_TO_SHOW = 7

def get_arxiv_dates(days_to_show=DAYS_TO_SHOW):
    """
    根据arXiv的更新规则，计算出需要抓取的起始和结束日期。
    规则：每日截止时间为美国东部时间(ET) 14:00，周末不更新。
    返回：(start_date, end_date) 两个datetime.date对象。
    """
    # 1. 定义时区
    utc_zone = pytz.UTC
    et_zone = pytz.timezone('US/Eastern')  # 美国东部时区，会自动处理夏令时
    
    # 2. 获取当前的ET时间和UTC时间
    utc_now = datetime.now(utc_zone)
    et_now = utc_now.astimezone(et_zone)
    
    # 3. 确定查询的“结束日期” (end_date)
    #    如果当前ET时间已经超过今天14:00，则今天已经更新，结束日期设为今天。
    #    否则，结束日期设为昨天。
    today_et_cutoff = et_now.replace(hour=14, minute=0, second=0, microsecond=0)
    
    if et_now >= today_et_cutoff:
        # 今天已更新
        end_date_et = et_now
    else:
        # 今天未更新，结束日期为昨天
        end_date_et = et_now - timedelta(days=1)
    
    # 将结束日期转换为纯日期对象（去掉时分秒），并转为UTC日期用于后续查询
    end_date = end_date_et.date()
    
    # 4. 计算起始日期 (start_date)
    #    从结束日期开始向前回溯，跳过周六(5)和周日(6)，直到集满所需的天数。
    start_date = end_date
    valid_days_counted = 1  # 结束日期本身算第一天
    
    while valid_days_counted < days_to_show:
        # 向前推一天
        start_date -= timedelta(days=1)
        # 检查是否为周末 (周一=0, 周日=6)
        if start_date.weekday() < 5:  # 0-4 代表周一到周五
            valid_days_counted += 1
    
    print(f"[日期计算] 根据规则，将查询从 {start_date} 到 {end_date} 期间（共{DAYS_TO_SHOW}个更新日）的论文。")
    print(f"[日期计算] 当前UTC时间: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"[日期计算] 当前ET时间: {et_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    return start_date, end_date

def run_data_pipeline(start_date, end_date):
    """
    执行数据处理流水线，抓取并总结论文。
    """
    print(f"开始执行数据流水线，日期范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    date_range_str = f"{start_date.strftime('%Y-%m-%d')}:{end_date.strftime('%Y-%m-%d')}"
    
    pipeline_cmd = [
        'python',
        'run_pipeline.py',
        '--categories', *CATEGORIES,
        '--date', date_range_str
    ]
    
    try:
        # 使用 capture_output=True 来捕获标准输出和错误
        result = subprocess.run(pipeline_cmd, check=True, text=True, encoding='utf-8', capture_output=True)
        print("流水线标准输出:")
        print(result.stdout)
        print("流水线执行成功。")
        return True
    except subprocess.CalledProcessError as e:
        print(f"错误：调用 run_pipeline.py 失败。")
        print(f"返回码: {e.returncode}")
        print(f"标准输出:\n{e.stdout}")
        print(f"错误输出:\n{e.stderr}")
        return False
    except FileNotFoundError:
        print("错误：找不到 'python' 命令或 'run_pipeline.py' 脚本。")
        return False

def load_and_prepare_data(start_date, end_date):
    """
    查找、加载并准备要展示的论文数据。
    """
    all_papers = []
    cat_str = '-'.join(CATEGORIES).replace('.', '')
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        pattern_prefix = f"arxiv_{cat_str}"
        pattern_suffix = f"_{date_str}.csv"
        
        for filename in os.listdir('.'):
            if filename.startswith(pattern_prefix) and filename.endswith(pattern_suffix):
                try:
                    df = pd.read_csv(filename)
                    all_papers.append(df)
                except Exception as e:
                    print(f"读取文件 {filename} 时出错: {e}")
        current_date += timedelta(days=1)

    if not all_papers:
        return pd.DataFrame()
        
    combined_df = pd.concat(all_papers, ignore_index=True)
    # 转换日期列为datetime对象以便排序
    combined_df['published_date'] = pd.to_datetime(combined_df['published_date'], format='mixed')
    # 按日期降序排列
    combined_df.sort_values(by='published_date', ascending=False, inplace=True)
    
    return combined_df

def generate_paper_cards_html(df):
    """
    将DataFrame转换为HTML卡片列表。
    """
    if df.empty:
        return "<p style='text-align:center; color: #888;'>未能加载任何论文数据，请检查后台日志。</p>"

    cards_html = ""
    for _, row in df.iterrows():
        # 检查AI总结是否存在且不为空
        ai_summary = row.get('summarization', 'N/A')
        if pd.isna(ai_summary) or ai_summary.strip() == '':
            ai_summary = "<i>AI总结正在生成中或生成失败...</i>"

        cards_html += f"""
        <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="margin-top: 0; margin-bottom: 10px; font-size: 1.4em;"><strong>{row['title']}</strong></h3>
            <p style="color: #555; margin-bottom: 8px;"><strong>Authors:</strong> {row['authors']}</p>
            <p style="color: #555; margin-bottom: 15px;"><strong>Date:</strong> {row['published_date'].strftime('%Y-%m-%d')}</p>
            
            <h4 style="margin-bottom: 5px; font-size: 1.1em;">Abstract</h4>
            <p style="text-align: justify;">{row['summary']}</p>
            
            <h4 style="margin-bottom: 5px; font-size: 1.1em;">AI Summary</h4>
            <p style="text-align: justify; color: #0056b3;">{ai_summary}</p>
            
            <hr style="border: none; border-top: 1px solid #eee; margin-top: 20px; margin-bottom: 15px;">
            
            <p style="font-size: 0.9em; color: #888;">
                Category: {row['primary_category']} | 
                <a href="{row['arxiv_url']}" target="_blank">arXiv Link</a> | 
                <a href="{row['pdf_url']}" target="_blank">PDF</a> | 
                <a href="{row['arxiv_url'].replace('arxiv', 'alphaxiv')}" target="_blank">alphaXiv</a>
            </p>
        </div>
        """
    return cards_html

def fetch_and_display_papers():
    """
    Gradio的入口函数，协调整个流程。
    """
    yield "<div style='text-align:center; padding: 40px;'><p>正在准备数据，请稍候...</p><p>（此过程可能需要几分钟，因为它正在后台抓取和分析论文）</p></div>"
    
    # 1. 计算日期范围
    # end_date = datetime.now() - timedelta(days=1)
    # start_date = end_date - timedelta(days=DAYS_TO_SHOW - 1)
    try:
        start_date, end_date = get_arxiv_dates()
    except Exception as e:
        yield f"<p style='text-align:center; color: red;'>计算日期时出错：{e}</p>"
        return
    
    # 2. 运行数据流水线
    pipeline_success = run_data_pipeline(start_date, end_date)
    
    if not pipeline_success:
        yield "<p style='text-align:center; color: red;'>数据处理流水线执行失败，请检查后台终端输出获取详细信息。</p>"
        return

    # 3. 加载并准备数据
    papers_df = load_and_prepare_data(start_date, end_date)
    
    # 4. 生成HTML卡片
    html_output = generate_paper_cards_html(papers_df)
    
    yield html_output

# --- 构建Gradio应用 ---
with gr.Blocks(title="七日拾遗") as app:
    gr.Markdown("# 七日拾遗")
    gr.Markdown("每日精选，助您洞悉 `eess.AS` 领域最新科研动态。")
    
    output_area = gr.HTML(value="<p style='text-align:center;'>应用加载完成，即将开始获取数据...</p>")
    
    # 当应用加载完成后，自动调用fetch_and_display_papers函数
    app.load(fetch_and_display_papers, None, output_area)

# --- 启动应用 ---
if __name__ == "__main__":
    print("启动Gradio应用...")
    print("请在浏览器中打开以下链接:")
    # 本地纯享
    # app.launch()
    # 子网共享
    app.launch(server_name='0.0.0.0')