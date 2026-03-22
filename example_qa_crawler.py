#!/usr/bin/env python3
"""
Q&A爬虫使用示例（纯crawl4ai版本）
"""

import os
import sys
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.crawl.crawl import QACrawler

async def main():
    """
    主函数：演示如何使用Q&A爬虫（纯crawl4ai版本）
    """
    # 配置爬虫参数
    max_depth = 2  # 设置最大下钻深度
    output_file = "./data/crawled_qa_data.json"  # 输出文件路径
    
    # 定义种子URL列表（可以从配置文件或数据库读取）
    seed_urls = [
        "https://help.atome.ph/hc/en-gb/categories/4439682039065-Atome Card",
        # 可以添加更多种子URL
        # "https://example.com/faq",
        # "https://example.com/support"
    ]
    
    print(f"开始爬取Q&A数据...")
    print(f"种子URL数量: {len(seed_urls)}")
    print(f"最大下钻深度: {max_depth}")
    print(f"输出文件: {output_file}")
    
    # 创建并运行爬虫
    crawler = QACrawler(max_depth=max_depth, output_file=output_file)
    await crawler.run(seed_urls)
    
    print("爬取完成！")
    
    # 验证结果
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            data = f.read()
            print(f"输出文件大小: {len(data)} 字符")
            
        # 统计Q&A对数量
        import json
        with open(output_file, 'r', encoding='utf-8') as f:
            qa_data = json.load(f)
            print(f"成功提取的Q&A对数量: {len(qa_data)}")
            
            # 显示前几个示例
            if qa_data:
                print("\n前3个Q&A示例:")
                for i, item in enumerate(qa_data[:3]):
                    print(f"\n{i+1}. 问题: {item['question'][:100]}...")
                    print(f"   答案: {item['answer'][:100]}...")
                    print(f"   来源: {item['url']}")
    else:
        print("警告：输出文件未生成")

def run_example():
    """运行示例"""
    asyncio.run(main())

if __name__ == "__main__":
    run_example()