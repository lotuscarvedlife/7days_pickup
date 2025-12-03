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
    
    # 3. 确定查询的"结束日期" (end_date)
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
    将DataFrame转换为现代化的HTML卡片列表。
    """
    if df.empty:
        return """
        <div style="text-align: center; padding: 60px 20px;">
            <div style="font-size: 48px; margin-bottom: 20px;">📄</div>
            <h3 style="color: #666; margin-bottom: 10px;">暂无论文数据</h3>
            <p style="color: #999;">未能加载任何论文数据，请检查后台日志。</p>
        </div>
        """

    # 自定义CSS样式
    css_styles = """
    <style>
    .paper-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }
    
    .paper-card {
        background: linear-gradient(135deg, #ffffff 0%, #fafbfc 100%);
        border: 1px solid rgba(139, 92, 246, 0.1);
        border-radius: 20px;
        padding: 28px;
        margin-bottom: 28px;
        box-shadow: 0 4px 20px rgba(139, 92, 246, 0.08), 0 1px 8px rgba(139, 92, 246, 0.06);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: hidden;
    }

    .paper-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 5px;
        background: linear-gradient(90deg, #8b9cf3 0%, #a78bfa 50%, #c084fc 100%);
        box-shadow: 0 2px 8px rgba(167, 139, 250, 0.3);
    }

    .paper-card:hover {
        transform: translateY(-4px) scale(1.02);
        box-shadow: 0 12px 40px rgba(139, 92, 246, 0.15), 0 4px 12px rgba(139, 92, 246, 0.1);
        border-color: rgba(139, 92, 246, 0.2);
        background: linear-gradient(135deg, #ffffff 0%, #f5f8ff 100%);
    }
    
    .paper-title {
        font-size: 1.4em;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 16px;
        line-height: 1.4;
        position: relative;
        padding-right: 12px;
    }

    .paper-title::after {
        content: '';
        position: absolute;
        right: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 3px;
        height: 0;
        background: linear-gradient(180deg, #8b9cf3 0%, #a78bfa 100%);
        border-radius: 2px;
        transition: height 0.3s ease;
    }

    .paper-card:hover .paper-title::after {
        height: 60%;
    }
    
    .paper-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        margin-bottom: 16px;
        font-size: 0.9em;
    }
    
    .meta-item {
        display: flex;
        align-items: center;
        gap: 6px;
        color: #6c757d;
    }
    
    .meta-icon {
        font-size: 1.1em;
    }
    
    .section-title {
        font-size: 1.1em;
        font-weight: 600;
        color: #495057;
        margin-bottom: 8px;
        margin-top: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .section-content {
        line-height: 1.7;
        color: #475569;
        text-align: justify;
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        padding: 16px 20px;
        border-radius: 12px;
        border-left: 4px solid #8b9cf3;
        position: relative;
        font-size: 0.95em;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: all 0.3s ease;
    }

    .section-content:hover {
        transform: translateX(2px);
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.1);
    }

    .ai-summary {
        background: linear-gradient(135deg, #fef3c7 0%, #fef9c3 50%, #e0f2fe 100%);
        border-left-color: #f59e0b;
        color: #92400e;
        border: 1px solid rgba(245, 158, 11, 0.1);
        position: relative;
    }

    .ai-summary::before {
        content: '✨';
        position: absolute;
        top: 8px;
        right: 12px;
        font-size: 1.2em;
        animation: sparkle 2s ease-in-out infinite;
    }

    @keyframes sparkle {
        0%, 100% { opacity: 0.6; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.2); }
    }
    
    .paper-links {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid #e9ecef;
        position: relative;
        z-index: 10;
    }
    
    .paper-link {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 18px;
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid rgba(139, 92, 246, 0.15);
        border-radius: 12px;
        text-decoration: none;
        color: #475569;
        font-size: 0.85em;
        font-weight: 500;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: hidden;
        box-shadow: 0 1px 6px rgba(139, 92, 246, 0.08);
        cursor: pointer;
        z-index: 10;
    }

    .paper-link::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.05), transparent);
        transition: left 0.6s ease;
    }

    .paper-link:hover {
        background: linear-gradient(135deg, #8b9cf3 0%, #a78bfa 100%);
        color: white;
        border-color: transparent;
        transform: translateY(-2px) scale(1.05);
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.25);
        text-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
    }

    .paper-link:hover::before {
        left: 100%;
    }

    .paper-link span:first-child {
        font-size: 1.1em;
        transition: transform 0.3s ease;
    }

    .paper-link:hover span:first-child {
        transform: scale(1.2) rotate(5deg);
    }
    
    .category-badge {
        display: inline-block;
        padding: 6px 12px;
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        color: white;
        border-radius: 16px;
        font-size: 0.75em;
        font-weight: 600;
        letter-spacing: 0.3px;
        text-transform: uppercase;
        box-shadow: 0 2px 8px rgba(251, 191, 36, 0.3);
        position: relative;
        overflow: hidden;
    }

    .category-badge::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        animation: shimmer 2s infinite;
    }

    @keyframes shimmer {
        0% { left: -100%; }
        100% { left: 100%; }
    }
    
    @media (max-width: 768px) {
        .paper-container {
            padding: 12px;
        }
        
        .paper-card {
            padding: 16px;
            margin-bottom: 16px;
        }
        
        .paper-meta {
            flex-direction: column;
            gap: 8px;
        }
        
        .paper-links {
            flex-direction: column;
        }
        
        .paper-link {
            justify-content: center;
        }
    }
    </style>
    """

    cards_html = css_styles + '<div class="paper-container">'
    
    for _, row in df.iterrows():
        # 检查AI总结是否存在且不为空
        ai_summary = row.get('summarization', 'N/A')
        if pd.isna(ai_summary) or ai_summary.strip() == '':
            ai_summary = "<em style='color: #999;'>AI总结正在生成中或生成失败...</em>"

        # 格式化日期
        date_str = row['published_date'].strftime('%Y年%m月%d日')
        
        # 截取作者列表（如果太长）
        authors = row['authors']
        if len(authors) > 100:
            authors = authors[:100] + "..."
        
        cards_html += f"""
        <div class="paper-card">
            <h3 class="paper-title">{row['title']}</h3>
            
            <div class="paper-meta">
                <div class="meta-item">
                    <span class="meta-icon">👥</span>
                    <span><strong>作者:</strong> {authors}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-icon">📅</span>
                    <span><strong>发布:</strong> {date_str}</span>
                </div>
                <div class="meta-item">
                    <span class="category-badge">{row['primary_category']}</span>
                </div>
            </div>
            
            <div class="section-title">
                <span>📝</span>
                <span>论文摘要</span>
            </div>
            <div class="section-content">
                {row['summary']}
            </div>
            
            <div class="section-title">
                <span>🤖</span>
                <span>AI 智能总结</span>
            </div>
            <div class="section-content ai-summary">
                {ai_summary}
            </div>
            
            <div class="paper-links">
                <a href="{row['arxiv_url']}" target="_blank" class="paper-link">
                    <span>🔗</span>
                    <span>arXiv 原文</span>
                </a>
                <a href="{row['pdf_url']}" target="_blank" class="paper-link">
                    <span>📄</span>
                    <span>PDF 下载</span>
                </a>
                <a href="{row['arxiv_url'].replace('arxiv', 'alphaxiv')}" target="_blank" class="paper-link">
                    <span>💬</span>
                    <span>alphaXiv 讨论</span>
                </a>
            </div>
        </div>
        """
    
    cards_html += '</div>'
    return cards_html

def fetch_and_display_papers():
    """
    Gradio的入口函数，协调整个流程。
    """
    yield """
    <div style="text-align: center; padding: 80px 20px; background: linear-gradient(135deg, #8b9cf3 0%, #a78bfa 50%, #c084fc 100%); color: white; border-radius: 24px; margin: 20px; position: relative; overflow: hidden; box-shadow: 0 10px 40px rgba(139, 92, 246, 0.3);">
        <!-- 背景装饰 -->
        <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);"></div>

        <div style="position: relative; z-index: 2;">
            <!-- 主图标动画 -->
            <div style="font-size: 64px; margin-bottom: 24px; animation: float 3s ease-in-out infinite;">🚀</div>

            <!-- 加载标题 -->
            <h2 style="margin-bottom: 16px; font-size: 2rem; font-weight: 700; text-shadow: 2px 2px 8px rgba(0,0,0,0.2);">正在获取最新论文数据</h2>

            <!-- 描述文字 -->
            <p style="font-size: 1.1em; opacity: 0.95; margin-bottom: 32px; text-shadow: 1px 1px 4px rgba(0,0,0,0.2);">此过程可能需要几分钟，正在后台抓取和分析论文...</p>

            <!-- 现代化加载指示器 -->
            <div style="margin-top: 32px; display: flex; justify-content: center; gap: 8px;">
                <div class="loading-dot" style="width: 12px; height: 12px; background: #ffffff; border-radius: 50%; animation: bounce 1.4s ease-in-out infinite both; box-shadow: 0 2px 8px rgba(0,0,0,0.2);"></div>
                <div class="loading-dot" style="width: 12px; height: 12px; background: #ffffff; border-radius: 50%; animation: bounce 1.4s ease-in-out infinite both; animation-delay: 0.16s; box-shadow: 0 2px 8px rgba(0,0,0,0.2);"></div>
                <div class="loading-dot" style="width: 12px; height: 12px; background: #ffffff; border-radius: 50%; animation: bounce 1.4s ease-in-out infinite both; animation-delay: 0.32s; box-shadow: 0 2px 8px rgba(0,0,0,0.2);"></div>
            </div>

            <!-- 进度提示 -->
            <div style="margin-top: 40px; font-size: 0.9em; opacity: 0.8; animation: fade 2s ease-in-out infinite;">
                <div>🔍 搜索论文中...</div>
            </div>
        </div>
    </div>

    <style>
    @keyframes float {
        0%, 100% { transform: translateY(0px) scale(1); }
        50% { transform: translateY(-10px) scale(1.05); }
    }

    @keyframes bounce {
        0%, 80%, 100% {
            transform: scale(0);
            opacity: 0.5;
        }
        40% {
            transform: scale(1);
            opacity: 1;
        }
    }

    @keyframes fade {
        0%, 100% { opacity: 0.6; }
        50% { opacity: 1; }
    }
    </style>
    """
    
    # 1. 计算日期范围
    try:
        start_date, end_date = get_arxiv_dates()
    except Exception as e:
        yield f"""
        <div style="text-align: center; padding: 60px 20px; background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); border: 1px solid #fecaca; border-radius: 20px; margin: 20px; box-shadow: 0 8px 32px rgba(239, 68, 68, 0.1);">
            <div style="font-size: 64px; margin-bottom: 20px; animation: shake 0.5s ease-in-out;">⚠️</div>
            <h3 style="color: #dc2626; font-size: 1.5rem; font-weight: 700; margin-bottom: 12px;">日期计算出错</h3>
            <p style="color: #7f1d1d; background: rgba(254, 226, 226, 0.5); padding: 16px 24px; border-radius: 12px; display: inline-block; font-weight: 500;">错误信息：{e}</p>
        </div>

        <style>
        @keyframes shake {{
            0%, 100% {{ transform: translateX(0); }}
            25% {{ transform: translateX(-5px); }}
            75% {{ transform: translateX(5px); }}
        }}
        </style>
        """
        return
    
    # 2. 运行数据流水线
    pipeline_success = run_data_pipeline(start_date, end_date)
    
    if not pipeline_success:
        yield """
        <div style="text-align: center; padding: 60px 20px; background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); border: 1px solid #fecaca; border-radius: 20px; margin: 20px; box-shadow: 0 8px 32px rgba(239, 68, 68, 0.1);">
            <div style="font-size: 64px; margin-bottom: 20px; animation: bounce-slow 2s ease-in-out infinite;">❌</div>
            <h3 style="color: #dc2626; font-size: 1.5rem; font-weight: 700; margin-bottom: 16px;">数据处理失败</h3>
            <p style="color: #7f1d1d; background: rgba(254, 226, 226, 0.5); padding: 16px 24px; border-radius: 12px; display: inline-block; max-width: 500px; line-height: 1.6; font-weight: 500;">数据处理流水线执行失败，请检查后台终端输出获取详细信息。</p>
            <div style="margin-top: 24px; font-size: 0.9em; opacity: 0.8; color: #991b1b;">
                💡 建议检查网络连接或稍后重试
            </div>
        </div>

        <style>
        @keyframes bounce-slow {
            0%, 100% { transform: translateY(0px) scale(1); }
            50% { transform: translateY(-8px) scale(1.05); }
        }
        </style>
        """
        return

    # 3. 加载并准备数据
    papers_df = load_and_prepare_data(start_date, end_date)
    
    # 4. 生成HTML卡片
    html_output = generate_paper_cards_html(papers_df)
    
    yield html_output

# --- 构建Gradio应用 ---
# 自定义CSS主题
custom_css = """
.gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #cbd5e1 100%) !important;
    min-height: 100vh;
    position: relative;
}

.gradio-container::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background:
        radial-gradient(circle at 20% 80%, rgba(139, 92, 246, 0.05) 0%, transparent 50%),
        radial-gradient(circle at 80% 20%, rgba(167, 139, 250, 0.05) 0%, transparent 50%),
        radial-gradient(circle at 40% 40%, rgba(192, 132, 252, 0.03) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
}

.gradio-container > * {
    position: relative;
    z-index: 1;
}

#header {
    background: linear-gradient(135deg, #8b9cf3 0%, #a78bfa 50%, #c084fc 100%);
    color: white;
    padding: 2.2rem;
    text-align: center;
    border-radius: 0 0 24px 24px;
    margin-bottom: 2rem;
    box-shadow: 0 6px 30px rgba(139, 92, 246, 0.3);
    position: relative;
    overflow: hidden;
}

#header::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
    z-index: 1;
}

#header h1,
#header p {
    position: relative;
    z-index: 2;
}

#header h1 {
    font-size: 2.8rem !important;
    font-weight: 800 !important;
    margin-bottom: 0.8rem !important;
    text-shadow: 2px 2px 8px rgba(0,0,0,0.3), 0 0 20px rgba(255,255,255,0.2);
    letter-spacing: 0.5px;
    color: #ffffff !important;
}

#header p {
    font-size: 1.2rem !important;
    font-weight: 500 !important;
    opacity: 1 !important;
    margin: 0.3rem 0 !important;
    text-shadow: 1px 1px 3px rgba(0,0,0,0.2);
    color: #f8fafc !important;
}

.main-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 20px;
}

/* 隐藏Gradio默认的footer */
footer {
    display: none !important;
}
"""

with gr.Blocks(
    title="七日拾遗 - 美化版",
    # css=custom_css,
    # theme=gr.themes.Soft(
    #     primary_hue="purple",
    #     secondary_hue="blue",
    #     neutral_hue="slate"
    # )
) as app:
    
    # 头部区域
    gr.HTML("""
    <div id="header">
        <h1>🎓 七日拾遗</h1>
        <p>每日精选，助您洞悉 eess.AS 领域最新科研动态</p>
        <p style="font-size: 0.9em; margin-top: 8px; opacity: 0.8;">
            🤖 AI 智能总结 | 📊 数据驱动 | 🌐 实时更新
        </p>
    </div>
    """)
    
    # 主要内容区域
    with gr.Column(elem_classes=["main-container"]):
        output_area = gr.HTML(value="""
        <div style="text-align: center; padding: 60px 20px;">
            <div style="font-size: 48px; margin-bottom: 20px;">🚀</div>
            <h3 style="color: #666;">应用已启动</h3>
            <p style="color: #999;">正在初始化，即将开始获取最新论文数据...</p>
        </div>
        """)
    
    # 当应用加载完成后，自动调用fetch_and_display_papers函数
    app.load(fetch_and_display_papers, None, output_area)

# --- 启动应用 ---
if __name__ == "__main__":
    print("启动美化版 Gradio 应用...")
    print("请在浏览器中打开以下链接:")
    # 本地纯享
    app.launch(
        css=custom_css,
        theme=gr.themes.Soft(
            primary_hue="purple",
            secondary_hue="blue",
            neutral_hue="slate"
        )
    )
    # 子网共享
    # app.launch(server_name='0.0.0.0')
