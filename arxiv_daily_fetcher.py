# -*- coding: utf-8 -*-
import arxiv
import pandas as pd
from datetime import datetime, timedelta
import argparse

def fetch_arxiv_papers_by_date(client, query, category_name, target_date_str, max_results=1000):
    """
    根据指定的查询条件和日期，获取论文。
    """
    print(f"\n正在为领域 '{category_name}' 执行查询...")
    
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    papers_data = []
    count = 0

    try:
        results_generator = client.results(search)
        for result in results_generator:
            published_date = result.published.strftime('%Y%m%d')

            if published_date == target_date_str:
                authors = [author.name for author in result.authors]
                papers_data.append({
                    'title': result.title,
                    'authors': ', '.join(authors),
                    'published_date': result.published.strftime('%Y-%m-%d'),
                    'summary': result.summary.replace('\n', ' '),
                    'arxiv_url': result.entry_id,
                    'pdf_url': result.pdf_url,
                    'primary_category': result.primary_category
                })
                count += 1
            elif result.published.strftime('%Y%m%d') < target_date_str:
                print(f"搜索已越过目标日期 {target_date_str}，停止此领域的查询。")
                break

    except arxiv.UnexpectedEmptyPageError:
        print(f"在 '{category_name}' 领域提前到达结果末尾，已处理所有可用论文。")
    except Exception as e:
        print(f"在 '{category_name}' 领域处理时发生未知错误: {e}")

    if not papers_data:
        print(f"在 '{category_name}' 领域未找到目标日期的论文。")
        return pd.DataFrame()

    print(f"在 '{category_name}' 领域成功提取 {count} 篇论文。")
    return pd.DataFrame(papers_data)

def save_to_csv(dataframe, filename='arxiv_papers.csv'):
    """
    将DataFrame保存到CSV文件。
    """
    if dataframe.empty:
        print("数据为空，不生成 CSV 文件。")
        return
        
    try:
        dataframe.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n数据已成功保存到文件: {filename}")
    except Exception as e:
        print(f"保存文件时出错: {e}")

def main():
    """
    主函数，用于解析命令行参数并执行论文抓取。
    """
    parser = argparse.ArgumentParser(description="从 arXiv 按指定领域、关键词和日期提取论文。")
    parser.add_argument(
        '--categories', 
        nargs='+', 
        required=True, 
        help="一个或多个 arXiv 研究领域代码 (例如: cs.AI stat.ML)。"
    )
    parser.add_argument(
        '--keywords', 
        nargs='*', 
        default=[], 
        help="一个或多个要在标题或摘要中搜索的关键词 (可选)。"
    )
    parser.add_argument(
        '--date', 
        type=str, 
        default=None, 
        help="要搜索的特定日期 (格式: 'YYYY-MM-DD')。如果未提供，则默认为昨天。"
    )
    
    args = parser.parse_args()
    
    search_categories = args.categories
    search_keywords = args.keywords
    target_date_str = args.date

    if target_date_str:
        try:
            target_dt = datetime.strptime(target_date_str, '%Y-%m-%d')
            print(f"开始提取 arXiv 论文，指定日期: {target_date_str}")
        except ValueError:
            print(f"错误：日期格式不正确。请使用 'YYYY-MM-DD' 格式。")
            exit()
    else:
        target_dt = datetime.now() - timedelta(days=1)
        print(f"开始提取 arXiv 论文，目标日期: {target_dt.strftime('%Y-%m-%d')}")

    target_date_for_api = target_dt.strftime('%Y%m%d')
    target_date_for_filename = target_dt.strftime('%Y-%m-%d')
    
    keyword_query_part = ""
    if search_keywords:
        keyword_or_parts = " OR ".join([f'ti:"{kw}" OR abs:"{kw}"' for kw in search_keywords])
        keyword_query_part = f" AND ({keyword_or_parts})"
        print(f"已启用关键词过滤: {', '.join(search_keywords)}")

    client = arxiv.Client()
    all_papers_dfs = []
    
    for category in search_categories:
        full_query = f"cat:{category}{keyword_query_part}"
        papers_df = fetch_arxiv_papers_by_date(
            client=client, 
            query=full_query, 
            category_name=category, 
            target_date_str=target_date_for_api, 
            max_results=500
        )
        if not papers_df.empty:
            all_papers_dfs.append(papers_df)

    if all_papers_dfs:
        combined_df = pd.concat(all_papers_dfs, ignore_index=True)
        combined_df.drop_duplicates(subset=['arxiv_url'], keep='first', inplace=True)
        
        final_count = len(combined_df)
        print(f"\n--- 合并结果 ---")
        print(f"去重后共找到 {final_count} 篇独立论文。")

        categories_str = '-'.join(search_categories).replace('.', '')
        keywords_str = ""
        if search_keywords:
            safe_keywords = [kw.replace(' ', '_') for kw in search_keywords]
            keywords_str = f"_keywords_{'-'.join(safe_keywords)}"

        output_filename = f'arxiv_{categories_str}{keywords_str}_{target_date_for_filename}.csv'
        save_to_csv(combined_df, output_filename)
    else:
        print(f"\n所有指定领域均未找到在 {target_date_for_filename} 更新的论文。")

# --- 主程序入口 ---
if __name__ == "__main__":
    main()

