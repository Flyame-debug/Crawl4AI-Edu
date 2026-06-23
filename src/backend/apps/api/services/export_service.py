# backend/services/export_service.py

import json
import csv
import io
from datetime import datetime
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

class ExportService:
    """导出服务 - 从结构化数据转换为各种格式"""
    
    @classmethod
    def export(cls, task, format_type, request):
        """统一导出入口"""
        # 获取数据
        pages = task.pages.all()
        raw_html = pages.first().raw_html if pages.first() else None
        
        # 构建结构化数据
        structured_data = []
        for page in pages:
            if page.extracted_data:
                structured_data.append(page.extracted_data)
            else:
                structured_data.append({
                    'url': page.url,
                    'category': page.category,
                    'content': page.markdown[:500] if page.markdown else '',
                    'created_at': page.created_at.strftime('%Y-%m-%d %H:%M:%S') if page.created_at else None
                })
        
        # 调用对应的转换方法
        handler = getattr(cls, f'_to_{format_type}', None)
        if not handler:
            return None, f'不支持的格式: {format_type}'
        
        content, mime_type, extension = handler(task, structured_data, raw_html)
        return content, mime_type, extension
    
    # ==================== 格式转换方法 ====================
    
    @classmethod
    def _to_json(cls, task, data, raw_html):
        """JSON格式"""
        result = {
            'task_id': str(task.task_id),
            'task_name': task.task_name,
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'total': len(data),
            'data': data
        }
        if raw_html:
            result['raw_html'] = raw_html[:10000]  # 限制大小
        return json.dumps(result, ensure_ascii=False, indent=2), 'application/json', 'json'
    
    @classmethod
    def _to_csv(cls, task, data, raw_html):
        """CSV格式"""
        output = io.StringIO()
        if data:
            fieldnames = list(data[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        return output.getvalue(), 'text/csv', 'csv'
    
    @classmethod
    def _to_txt(cls, task, data, raw_html):
        """TXT纯文本格式"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"采集结果 - {task.task_name or task.task_id}")
        lines.append("=" * 60)
        lines.append(f"任务ID: {task.task_id}")
        lines.append(f"创建时间: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"数据量: {len(data)} 条")
        lines.append("=" * 60)
        lines.append("")
        
        for i, item in enumerate(data, 1):
            lines.append(f"[记录 {i}]")
            for key, value in item.items():
                lines.append(f"  {key}: {value}")
            lines.append("")
            lines.append("-" * 30)
        
        return "\n".join(lines), 'text/plain', 'txt'
    
    @classmethod
    def _to_md(cls, task, data, raw_html):
        """Markdown格式"""
        lines = []
        lines.append(f"# 采集结果 - {task.task_name or task.task_id}")
        lines.append("")
        lines.append(f"- **任务ID**: {task.task_id}")
        lines.append(f"- **创建时间**: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **数据量**: {len(data)} 条")
        lines.append("")
        
        for i, item in enumerate(data, 1):
            lines.append(f"## 记录 {i}")
            lines.append("")
            for key, value in item.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines), 'text/markdown', 'md'
    
    @classmethod
    def _to_html(cls, task, data, raw_html):
        """HTML格式（含原始数据）"""
        template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>采集结果</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: #409EFF; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f2f2f2; }
        .raw-data { background: #f5f5f5; padding: 15px; border-radius: 4px; overflow: auto; max-height: 400px; }
        .footer { margin-top: 40px; text-align: center; color: #999; font-size: 12px; }
        pre { white-space: pre-wrap; word-wrap: break-word; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 采集结果</h1>
        <p><strong>任务:</strong> {task_name}</p>
        <p><strong>任务ID:</strong> {task_id}</p>
        <p><strong>创建时间:</strong> {created_at}</p>
        <p><strong>数据量:</strong> {total} 条</p>
    </div>
    
    <h2>📋 结构化数据</h2>
    <table>
        <tr>{headers}</tr>
        {rows}
    </table>
    
    <h2>📄 原始HTML</h2>
    <div class="raw-data">
        <pre>{raw_html}</pre>
    </div>
    
    <div class="footer">
        <p>生成时间: {export_time} | Crawl4AI 采集系统</p>
    </div>
</body>
</html>"""
        
        headers = ""
        rows = ""
        if data:
            keys = list(data[0].keys())
            headers = "".join([f"<th>{k}</th>" for k in keys])
            for item in data[:100]:
                row = "".join([f"<td>{str(item.get(k, ''))}</td>" for k in keys])
                rows += f"<tr>{row}</tr>"
        
        raw_html_escaped = (raw_html or '暂无原始数据').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')[:20000]
        
        content = template.format(
            task_name=task.task_name or f"任务_{str(task.task_id)[:8]}",
            task_id=task.task_id,
            created_at=task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            total=len(data),
            headers=headers,
            rows=rows,
            raw_html=raw_html_escaped,
            export_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        return content, 'text/html', 'html'
    
    @classmethod
    def _to_xml(cls, task, data, raw_html):
        """XML格式"""
        import xml.dom.minidom as minidom
        from xml.etree import ElementTree as ET
        
        root = ET.Element("results")
        root.set("task_id", str(task.task_id))
        root.set("total", str(len(data)))
        
        for item in data:
            record = ET.SubElement(root, "record")
            for key, value in item.items():
                field = ET.SubElement(record, key)
                field.text = str(value)
        
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  "), 'application/xml', 'xml'
    
    @classmethod
    def _to_sql(cls, task, data, raw_html):
        """SQL INSERT语句"""
        lines = []
        lines.append("-- 采集数据导入")
        lines.append(f"-- 任务ID: {task.task_id}")
        lines.append(f"-- 数据量: {len(data)} 条")
        lines.append("")
        
        if data:
            table_name = f"crawl_data_{str(task.task_id)[:8]}"
            fields = list(data[0].keys())
            lines.append(f"CREATE TABLE IF NOT EXISTS {table_name} (")
            lines.append("    id INTEGER PRIMARY KEY AUTOINCREMENT,")
            for field in fields:
                lines.append(f"    {field} TEXT,")
            lines.append("    created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            lines.append(");")
            lines.append("")
            
            for item in data:
                values = []
                for field in fields:
                    val = str(item.get(field, '')).replace("'", "''")
                    values.append(f"'{val}'")
                lines.append(f"INSERT INTO {table_name} ({', '.join(fields)}) VALUES ({', '.join(values)});")
        
        return "\n".join(lines), 'text/plain', 'sql'
    
    @classmethod
    def _to_rss(cls, task, data, raw_html):
        """RSS订阅格式"""
        rss_template = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>采集结果 - {task_name}</title>
        <link>http://localhost</link>
        <description>采集数据订阅</description>
        <pubDate>{pub_date}</pubDate>
        {items}
    </channel>
</rss>"""
        
        items = []
        for item in data[:20]:
            title = item.get('title', '未命名') or item.get('name', '未命名')
            desc = str(item.get('content', '') or item.get('description', ''))[:200]
            items.append(f"""
        <item>
            <title>{title}</title>
            <link>{item.get('url', '')}</link>
            <description>{desc}</description>
            <pubDate>{datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
        </item>
            """)
        
        content = rss_template.format(
            task_name=task.task_name or f"任务_{str(task.task_id)[:8]}",
            pub_date=datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
            items="".join(items)
        )
        return content, 'application/rss+xml', 'xml'