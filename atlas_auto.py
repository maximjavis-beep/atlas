#!/opt/homebrew/bin/python3
"""
Atlas 哲学研讨情报日报 - 纯脚本版本
零 Token 消耗，直接运行
"""
import feedparser
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import os
import sys
import subprocess
import re

# 路径配置
PROJECT_DIR = Path(__file__).parent
CONFIG_PATH = PROJECT_DIR / "config.json"
DB_PATH = PROJECT_DIR / "data.db"
REPORTS_DIR = PROJECT_DIR / "reports"
WEB_DIR = PROJECT_DIR / "web"

def init_db():
    """初始化数据库"""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            title TEXT,
            link TEXT,
            summary TEXT,
            published TEXT,
            source TEXT,
            region TEXT,
            fetched_at TEXT,
            keywords_matched TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_keywords():
    """获取关键词列表"""
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    return config.get("keywords", [])

def check_keywords(text, keywords):
    """检查文本中是否包含关键词"""
    if not text:
        return []
    text_lower = text.lower()
    matched = []
    for kw in keywords:
        if kw.lower() in text_lower:
            matched.append(kw)
    return matched

def extract_image_from_summary(summary):
    """从摘要中提取图片 URL - 只取第一张"""
    img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', summary)
    if img_matches:
        return img_matches[0]
    return None

def clean_html_tags(text):
    """清理 HTML 标签，保留文本内容"""
    # 移除 script 和 style
    text = re.sub(r'<(script|style)[^>]*>[^<]*</\1>', '', text, flags=re.DOTALL)
    # 移除所有 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 解码 HTML 实体
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    return text.strip()

def fetch_feed(name, url, region, keywords, max_items=10):
    """抓取单个 RSS 源"""
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:max_items]:
            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))
            
            # 检查关键词
            content = f"{title} {summary}"
            matched = check_keywords(content, keywords)
            
            article = {
                "id": hashlib.md5(f"{title}{url}".encode()).hexdigest(),
                "title": title,
                "link": entry.get("link", ""),
                "summary": summary[:500] if summary else "",
                "published": entry.get("published", datetime.now().isoformat()),
                "source": name,
                "region": region,
                "fetched_at": datetime.now().isoformat(),
                "keywords_matched": ",".join(matched)
            }
            articles.append(article)
    except Exception as e:
        print(f"    ⚠️ {name}: {str(e)[:50]}")
    return articles

def save_articles(articles):
    """保存文章到数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    added = 0
    for a in articles:
        try:
            c.execute('''
                INSERT OR IGNORE INTO articles 
                (id, title, link, summary, published, source, region, fetched_at, keywords_matched)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (a["id"], a["title"], a["link"], a["summary"], 
                  a["published"], a["source"], a["region"], a["fetched_at"], a["keywords_matched"]))
            if c.rowcount > 0:
                added += 1
        except Exception as e:
            pass
    conn.commit()
    conn.close()
    return added

def fetch_all_rss():
    """抓取所有 RSS 源"""
    print("📡 步骤 1: 抓取 RSS 源")
    print("-" * 40)
    
    init_db()
    
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    
    keywords = get_keywords()
    total_added = 0
    total_sources = 0
    
    for region_key, region_data in config["regions"].items():
        region_name = region_data["name"]
        sources = region_data.get("sources", [])
        
        if not sources:
            continue
        
        print(f"\n📍 {region_name}")
        
        for source in sources:
            name = source["name"]
            url = source["url"]
            print(f"  → {name}")
            
            articles = fetch_feed(name, url, region_name, keywords, max_items=10)
            added = save_articles(articles)
            total_added += added
            total_sources += 1
            if added > 0:
                print(f"     新增 {added} 条")
            else:
                print(f"     暂无更新")
    
    print(f"\n✅ 抓取完成! 共 {total_sources} 个源，新增 {total_added} 条资讯")
    return total_added

def get_recent_articles(hours=24):
    """获取最近的文章"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    since = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    c.execute('''
        SELECT title, link, summary, published, source, region, keywords_matched
        FROM articles
        WHERE fetched_at > ?
        ORDER BY fetched_at DESC
    ''', (since,))
    
    articles = c.fetchall()
    conn.close()
    return articles

def generate_markdown_report():
    """生成 Markdown 报告 - 按信源分组，每个信源一张图片"""
    print("\n📝 步骤 2: 生成 Markdown 报告")
    print("-" * 40)
    
    articles = get_recent_articles(hours=24)
    today = datetime.now().strftime("%Y-%m-%d")
    date_file = datetime.now().strftime("%Y%m%d")
    
    # 统计
    regions = set(a[5] for a in articles)
    sources = set(a[4] for a in articles)
    
    md = f"""# 🧠 Atlas 哲学研讨情报日报

**日期**: {today}  
**来源**: 全球 {len(regions)} 个地区 · {len(sources)} 个信源

---

## 📊 今日概览

- **新增资讯**: {len(articles)} 条
- **重点关键词**: 研讨会、讲座、论坛、学术会议

---
"""
    
    # 按地区和信源分组
    by_region_source = {}

    for a in articles:
        title, link, summary, published, source, region, keywords = a
        key = (region, source)
        if key not in by_region_source:
            by_region_source[key] = []
        by_region_source[key].append(a)
    
    # 按地区组织
    region_sources = {}
    for (region, source), items in by_region_source.items():
        if region not in region_sources:
            region_sources[region] = []
        region_sources[region].append((source, items))

    # 生成各地区内容
    for region in sorted(region_sources.keys()):
        md += f"\n## 🌍 {region}\n\n"

        for source, items in region_sources[region]:
            # 信源标题
            md += f"### 📰 {source}\n\n"

            # 如果有文章
            if items:
                # 列出该信源的文章（最多5条），每篇文章单独显示自己的图片
                for title, link, summary, published, s, r, keywords in items[:5]:
                    # 提取该文章的图片
                    img_url = extract_image_from_summary(summary)
                    if img_url:
                        md += f"![{title}]({img_url})\n\n"

                    md += f"- **[{title}]({link})**\n"
                    # 清理 HTML 标签
                    clean_summary = clean_html_tags(summary)[:120]
                    md += f"  {clean_summary}...\n"
                    if keywords:
                        md += f"  *关键词: {', '.join(keywords.split(',')[:3])}*\n"
                    md += "\n"
            else:
                # 该信源暂无更新
                md += "*📝 该信源暂无更新*\n\n"
    
    if not articles:
        md += "\n*今日暂无新资讯*\n"
    
    md += f"""
---

*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}*  
*Atlas Intelligence System*
"""
    
    # 保存报告
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / f"atlas_report_{date_file}.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)
    
    # 同时保存最新版本
    latest_path = REPORTS_DIR / "atlas_latest.md"
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(md)
    
    print(f"  ✅ Markdown 报告: {report_path}")
    print(f"  ✅ 最新版本: {latest_path}")
    print(f"  📊 共 {len(articles)} 条资讯，{len(regions)} 个地区")
    
    return report_path, len(articles)

def markdown_to_html(md_path):
    """将 Markdown 转换为 HTML - 按信源分组，每个信源一张图片"""
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    update_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    
    lines = md_content.split('\n')
    html_lines = []
    in_list = False
    in_source_section = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 跳过第一行标题
        if stripped.startswith('# 🧠 Atlas'):
            continue
            
        # 处理日期和来源信息
        if stripped.startswith('**日期**') or stripped.startswith('**来源**'):
            html_lines.append(f'<p class="meta-info">{stripped.replace("**", "")}</p>')
            continue
        
        # 处理分隔线
        if stripped == '---':
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            if in_source_section:
                html_lines.append('</div>')  # 关闭 source-section
                in_source_section = False
            html_lines.append('<hr>')
            continue
        
        # 处理 H2 标题（地区）
        if stripped.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            if in_source_section:
                html_lines.append('</div>')
                in_source_section = False
            content = stripped[3:]
            html_lines.append(f'<h2>{content}</h2>')
            continue
        
        # 处理 H3 标题（信源名称）
        if stripped.startswith('### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            if in_source_section:
                html_lines.append('</div>')
            
            # 提取信源名称
            source_name = stripped[4:].replace('📰 ', '')
            html_lines.append(f'<div class="source-section">')
            html_lines.append(f'<h3 class="source-name">📰 {source_name}</h3>')
            in_source_section = True
            continue
        
        # 处理 Markdown 图片格式 ![alt](url)
        img_match = re.match(r'!\[(.+?)\]\((.+?)\)', stripped)
        if img_match:
            alt_text, img_url = img_match.groups()
            html_lines.append(f'<div class="source-image"><img src="{img_url}" alt="{alt_text}" loading="lazy"></div>')
            continue
        
        # 处理列表项（文章列表）
        if stripped.startswith('- '):
            if not in_list:
                html_lines.append('<ul class="article-list">')
                in_list = True
            
            # 处理文章链接格式 - **[title](url)**
            content = stripped[2:]
            # 转换粗体链接
            content = re.sub(r'\*\*\[(.+?)\]\((.+?)\)\*\*', r'<a href="\2" target="_blank" class="article-title">\1</a>', content)
            # 转换普通粗体
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            # 转换斜体（关键词）
            content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
            html_lines.append(f'<li>{content}</li>')
            continue
        
        # 普通段落（摘要文字）
        if stripped:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            clean_text = clean_html_tags(stripped)
            if clean_text:
                html_lines.append(f'<p class="article-desc">{clean_text}</p>')
    
    # 清理未关闭的标签
    if in_list:
        html_lines.append('</ul>')
    if in_source_section:
        html_lines.append('</div>')
    
    html_content = '\n'.join(html_lines)
    
    # 构建完整 HTML
    html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas 哲学研讨情报日报</title>
    <meta name="description" content="全球哲学研讨情报追踪系统 - 覆盖美洲、欧洲、非洲、亚洲的哲学学术动态">
    <!-- Open Graph 元标签 -->
    <meta property="og:title" content="🧠 Atlas 哲学研讨情报日报">
    <meta property="og:description" content="全球哲学研讨情报追踪系统 - 每日更新哲学学术资讯">
    <meta property="og:image" content="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1200&h=630&fit=crop">
    <meta property="og:url" content="https://atlas-philosophy.vercel.app/">
    <meta property="og:type" content="website">
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="🧠 Atlas 哲学研讨情报日报">
    <meta name="twitter:description" content="全球哲学研讨情报追踪系统">
    <meta name="twitter:image" content="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1200&h=630&fit=crop">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            text-align: center;
            padding: 40px 20px;
            color: white;
        }}
        header h1 {{ font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        header p {{ font-size: 1.1em; opacity: 0.9; }}
        .update-time {{
            background: rgba(255,255,255,0.2);
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            margin-top: 15px;
            font-size: 0.9em;
        }}
        .card {{
            background: white;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        .card h2 {{
            color: #1a1a2e;
            margin: 30px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 3px solid #0f3460;
            font-size: 1.5em;
        }}
        .card h2:first-child {{ margin-top: 0; }}
        
        /* 信源区块样式 */
        .source-section {{
            background: #fafafa;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #0f3460;
        }}
        .source-name {{
            color: #16213e;
            font-size: 1.2em;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 3px solid #16213e;
        }}
        
        /* 图片响应式 - 确保在各种设备上都能正常显示 */
        .card img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 10px 0;
            display: block;
        }}

        /* 信源图片容器 - 自适应屏幕 */
        .source-image {{
            margin: 15px 0;
            text-align: center;
            width: 100%;
            overflow: hidden;
            border-radius: 8px;
            background: #f5f5f5;
        }}

        /* 信源图片 - 保持比例自适应 */
        .source-image img {{
            width: 100%;
            max-height: 300px;
            height: auto;
            object-fit: contain;
            display: block;
            margin: 0 auto;
        }}

        /* 文章内图片 - 响应式 */
        .article-image {{
            margin: 10px 0;
            width: 100%;
            border-radius: 6px;
            overflow: hidden;
            background: #f5f5f5;
        }}
        .article-image img {{
            width: 100%;
            height: auto;
            max-height: 250px;
            object-fit: contain;
            display: block;
        }}
        
        /* 文章列表 */
        .article-list {{
            list-style: none;
            padding: 0;
            margin: 15px 0 0 0;
        }}
        .article-list li {{
            padding: 10px 0;
            border-bottom: 1px solid #eee;
            color: #555;
            font-size: 0.95em;
        }}
        .article-list li:last-child {{
            border-bottom: none;
        }}
        .article-title {{
            color: #0f3460;
            text-decoration: none;
            font-weight: 600;
            display: block;
            margin-bottom: 5px;
        }}
        .article-title:hover {{
            color: #16213e;
            text-decoration: underline;
        }}
        .article-desc {{
            color: #666;
            font-size: 0.9em;
            margin: 5px 0;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #e0e0e0;
            margin: 30px 0;
        }}
        footer {{
            text-align: center;
            padding: 30px;
            color: rgba(255,255,255,0.8);
            font-size: 0.9em;
        }}
        
        /* 移动端优化 */
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            header {{ padding: 20px 10px; }}
            header h1 {{ font-size: 1.5em; margin-bottom: 5px; }}
            header p {{ font-size: 0.9em; }}
            .update-time {{ padding: 5px 12px; font-size: 0.8em; margin-top: 10px; }}
            .card {{ padding: 15px; border-radius: 12px; }}
            .card h2 {{ font-size: 1.2em; margin: 20px 0 15px 0; padding-bottom: 8px; }}
            
            .source-section {{ padding: 12px; margin-bottom: 15px; }}
            .source-name {{ font-size: 1em; margin-bottom: 10px; padding-left: 8px; }}
            
            /* 移动端图片 - 自适应 */
            .source-image {{
                margin: 10px 0;
                border-radius: 6px;
            }}
            .source-image img {{
                max-height: 200px;
                width: 100%;
            }}
            .article-image {{
                margin: 8px 0;
            }}
            .article-image img {{
                max-height: 180px;
            }}
            
            .article-list {{ margin-top: 10px; }}
            .article-list li {{ padding: 8px 0; font-size: 0.9em; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧠 Atlas 哲学研讨情报日报</h1>
            <p>全球哲学研讨情报追踪系统</p>
            <div class="update-time">更新时间: {update_time}</div>
        </header>
        
        <div class="card">
            {html_content}
        </div>
        
        <footer>
            <p>Atlas Intelligence System</p>
        </footer>
    </div>
</body>
</html>'''
    
    return html_template

def update_website():
    """更新网站内容"""
    print("\n🌐 步骤 3: 更新网站")
    print("-" * 40)
    
    # 找到最新的 Markdown 文件
    latest_md = REPORTS_DIR / "atlas_latest.md"
    
    if not latest_md.exists():
        print(f"  ❌ 未找到报告文件: {latest_md}")
        return None
    
    # 生成 HTML
    html_content = markdown_to_html(latest_md)
    
    # 保存到网站目录
    WEB_DIR.mkdir(exist_ok=True)
    index_path = WEB_DIR / "index.html"
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"  ✅ 网站已更新: {index_path}")
    return index_path

def generate_pdf():
    """生成 PDF 版本，同时生成 latest_XX.pdf 序列号文件"""
    print("\n📑 步骤 4: 生成 PDF")
    print("-" * 40)
    
    # 检查 Puppeteer 脚本
    puppeteer_script = Path.home() / ".openclaw/workspace/html_to_pdf.js"
    if not puppeteer_script.exists():
        print(f"  ⚠️ Puppeteer 脚本不存在，跳过 PDF 生成")
        return None
    
    # 网站 HTML 路径
    html_path = WEB_DIR / "index.html"
    if not html_path.exists():
        print(f"  ❌ 未找到网站 HTML")
        return None
    
    # 生成带时间戳的 PDF 文件名
    now = datetime.now()
    date_folder = now.strftime("%Y%m%d")
    time_suffix = now.strftime("%H%M")
    
    # 目标文件夹
    pdf_dir = REPORTS_DIR / date_folder
    pdf_dir.mkdir(exist_ok=True)
    
    pdf_filename = f"atlas_{date_folder}_{time_suffix}.pdf"
    pdf_path = pdf_dir / pdf_filename
    
    # 执行转换
    try:
        result = subprocess.run(
            ["node", str(puppeteer_script), str(html_path), str(pdf_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"  ❌ PDF 生成失败: {result.stderr}")
            return None
        
        print(f"  ✅ PDF 已生成: {pdf_path}")
        
        # 生成 latest_XX.pdf 序列号文件
        import glob
        existing_latest = glob.glob(str(pdf_dir / "atlas_latest_*.pdf"))
        next_num = 1
        for f in existing_latest:
            try:
                num = int(Path(f).stem.replace("atlas_latest_", ""))
                if num >= next_num:
                    next_num = num + 1
            except ValueError:
                continue
        
        latest_filename = f"atlas_latest_{next_num:02d}.pdf"
        latest_path = pdf_dir / latest_filename
        
        # 复制为 latest 版本
        import shutil
        shutil.copy2(pdf_path, latest_path)
        print(f"  ✅ 序列号文件已生成: {latest_path}")
        
        return pdf_path
    except Exception as e:
        print(f"  ❌ PDF 生成异常: {str(e)}")
        return None

def deploy_to_vercel():
    """部署到 Vercel"""
    print("\n🚀 步骤 5: 部署到 Vercel")
    print("-" * 40)
    
    # 检查是否在 git 仓库中
    git_dir = PROJECT_DIR / ".git"
    if not git_dir.exists():
        print("  ❌ 未找到 Git 仓库，跳过部署")
        return False
    
    # 执行 git 命令
    os.chdir(PROJECT_DIR)
    
    # 添加更改
    os.system("git add -A")
    
    # 提交
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    result = os.system(f'git commit -m "Update: {date_str} Atlas data"')
    
    if result != 0:
        print("  ⚠️ 没有更改需要提交，或提交失败")
        return False
    
    # 推送
    result = os.system("git push origin main")
    
    if result == 0:
        print("  ✅ 已推送到 GitHub，Vercel 将自动部署")
        return True
    else:
        print("  ❌ 推送失败")
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Atlas 哲学研讨情报日报 - 纯脚本工具')
    parser.add_argument('--fetch', action='store_true', help='抓取 RSS 源')
    parser.add_argument('--report', action='store_true', help='生成报告')
    parser.add_argument('--website', action='store_true', help='更新网站')
    parser.add_argument('--pdf', action='store_true', help='生成 PDF')
    parser.add_argument('--deploy', action='store_true', help='部署到 Vercel')
    parser.add_argument('--all', action='store_true', help='执行完整流程')
    
    args = parser.parse_args()
    
    if args.all or (not args.fetch and not args.report and not args.website and not args.pdf and not args.deploy):
        # 默认执行完整流程
        print("🧠 Atlas 自动更新流程")
        print("=" * 50)
        
        # 1. 抓取 RSS
        fetch_all_rss()
        
        # 2. 生成报告
        report_path, article_count = generate_markdown_report()
        
        # 3. 更新网站
        update_website()
        
        # 4. 生成 PDF
        pdf_path = generate_pdf()
        
        # 5. 部署
        deploy_to_vercel()
        
        print("\n" + "=" * 50)
        print("✅ 全部完成!")
        print(f"📊 共 {article_count} 条资讯")
        if pdf_path:
            print(f"📑 PDF: {pdf_path}")
        
    else:
        if args.fetch:
            fetch_all_rss()
        if args.report:
            generate_markdown_report()
        if args.website:
            update_website()
        if args.pdf:
            generate_pdf()
        if args.deploy:
            deploy_to_vercel()

if __name__ == "__main__":
    main()
