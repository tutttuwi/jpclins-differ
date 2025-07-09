#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jpclins StructureDefinitionのelement配列の全属性を比較し、
差分を色付きで表示するHTMLテーブルを生成するツール
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import difflib
import inspect
import textwrap
import sys

class StructureDefinitionElementComparator:
    def __init__(self, v1_path, v2_path):
        self.v1_path = Path(v1_path)
        self.v2_path = Path(v2_path)
        self.v1_elements = {}
        self.v2_elements = {}
        self.all_attributes = set()
        
    def parse_structure_definition_elements(self, file_path):
        """StructureDefinitionファイルからelement配列を抽出"""
        if not file_path.exists():
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            elements = {}
            
            # snapshot.elementsを優先、なければdifferential.elementsを使用
            element_list = data.get('snapshot', {}).get('element', [])
            if not element_list:
                element_list = data.get('differential', {}).get('element', [])
            
            for element in element_list:
                path = element.get('path', '')
                if path:
                    elements[path] = element
                    # 全属性を収集
                    self.all_attributes.update(element.keys())
            
            return elements
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {}
    
    def compare_files(self):
        """両バージョンのStructureDefinitionファイルを比較"""
        # 1.9.0のStructureDefinitionファイル一覧を取得
        v1_package = self.v1_path / "package"
        if v1_package.exists():
            for file_path in v1_package.glob("StructureDefinition-*.json"):
                self.v1_elements[file_path.name] = self.parse_structure_definition_elements(file_path)
        
        # 1.10.0のStructureDefinitionファイル一覧を取得
        v2_package = self.v2_path / "package"
        if v2_package.exists():
            for file_path in v2_package.glob("StructureDefinition-*.json"):
                self.v2_elements[file_path.name] = self.parse_structure_definition_elements(file_path)
    
    def analyze_element_differences(self, filename):
        """特定のファイルのelement差分を分析"""
        v1_elements = self.v1_elements.get(filename, {})
        v2_elements = self.v2_elements.get(filename, {})
        
        all_paths = set(v1_elements.keys()) | set(v2_elements.keys())
        differences = []
        
        for path in sorted(all_paths):
            v1_element = v1_elements.get(path)
            v2_element = v2_elements.get(path)
            
            if not v1_element and v2_element:
                # 新規追加
                differences.append({
                    'path': path,
                    'type': 'added',
                    'v1_element': None,
                    'v2_element': v2_element
                })
            elif v1_element and not v2_element:
                # 削除
                differences.append({
                    'path': path,
                    'type': 'removed',
                    'v1_element': v1_element,
                    'v2_element': None
                })
            elif v1_element and v2_element:
                # 変更の可能性
                changed_attributes = []
                for attr in self.all_attributes:
                    v1_value = v1_element.get(attr)
                    v2_value = v2_element.get(attr)
                    if v1_value != v2_value:
                        changed_attributes.append({
                            'attribute': attr,
                            'v1_value': v1_value,
                            'v2_value': v2_value
                        })
                
                if changed_attributes:
                    differences.append({
                        'path': path,
                        'type': 'modified',
                        'v1_element': v1_element,
                        'v2_element': v2_element,
                        'changed_attributes': changed_attributes
                    })
                else:
                    # 変更なし
                    differences.append({
                        'path': path,
                        'type': 'unchanged',
                        'v1_element': v1_element,
                        'v2_element': v2_element
                    })
        
        return differences
    
    def format_value(self, value):
        """値をHTML表示用にフォーマット"""
        if value is None:
            return '<span class="no-value">-</span>'
        elif isinstance(value, (dict, list)):
            return f'<pre class="complex-value">{json.dumps(value, indent=2, ensure_ascii=False)}</pre>'
        else:
            return str(value)
    
    def html_diff(self, old, new):
        # old/newがdictやlistなら整形
        if isinstance(old, (dict, list)):
            old = json.dumps(old, indent=2, ensure_ascii=False)
        if isinstance(new, (dict, list)):
            new = json.dumps(new, indent=2, ensure_ascii=False)
        old_lines = str(old).splitlines()
        new_lines = str(new).splitlines()
        diff = difflib.ndiff(old_lines, new_lines)
        html = ''
        for line in diff:
            if line.startswith('+ '):
                html += f'<div class="diff-added">+ {line[2:]}</div>'
            elif line.startswith('- '):
                html += f'<div class="diff-removed">- {line[2:]}</div>'
            else:
                html += f'<div>{line[2:]}</div>'
        return html

    def get_file_metadata(self, file_path):
        """StructureDefinitionファイルのメタ情報をdictで返す"""
        if not file_path.exists():
            return {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            meta_keys = [
                'resourceType','id','language','url','version','name','title','status','date','publisher','description','copyright','fhirVersion','kind','abstract','type','baseDefinition','derivation','mapping'
            ]
            return {k: data.get(k) for k in meta_keys if k in data}
        except Exception as e:
            return {'error': str(e)}

    def get_file_metadata_html(self, meta):
        """メタ情報をHTMLテーブルで返す"""
        if not meta:
            return '<div>メタ情報なし</div>'
        html = '<table style="border-collapse:collapse;">'
        for k, v in meta.items():
            html += f'<tr><th style="text-align:left;padding:2px 8px;background:#f8f9fa;">{k}</th><td style="padding:2px 8px;">{self.format_value(v)}</td></tr>'
        html += '</table>'
        return html

    def get_script_source_html(self):
        """このスクリプト自身のソースをHTMLで返す"""
        try:
            with open(__file__, 'r', encoding='utf-8') as f:
                code = f.read()
            return f'<pre style="max-height:400px;overflow-y:auto;background:#222;color:#eee;padding:10px;border-radius:6px;">{code}</pre>'
        except Exception:
            return '<div>スクリプトソース取得不可</div>'

    def generate_html_report(self, output_file="structure_definition_elements_diff.html"):
        """HTMLレポートを生成"""
        # 統計情報を計算
        total_files = len(set(self.v1_elements.keys()) | set(self.v2_elements.keys()))
        modified_files = []
        
        for filename in sorted(set(self.v1_elements.keys()) | set(self.v2_elements.keys())):
            differences = self.analyze_element_differences(filename)
            if any(d['type'] != 'unchanged' for d in differences):
                modified_files.append((filename, differences))
        
        # サイドバー用ファイルリスト
        sidebar_items = []
        file_meta_map = {}
        v1_package = self.v1_path / "package"
        v2_package = self.v2_path / "package"
        for file_idx, (filename, differences) in enumerate(modified_files):
            # ファイルパス特定
            v1_file = v1_package / filename
            v2_file = v2_package / filename
            meta = self.get_file_metadata(v2_file if v2_file.exists() else v1_file)
            file_meta_map[filename] = meta
            sidebar_items.append(f'<div class="sidebar-item" title="{filename}"><a href="#file-{file_idx}">{filename}</a></div>')
        # 追加情報（スクリプト全文）
        script_html = self.get_script_source_html()
        js_script = textwrap.dedent('''
// ファイルごとの表示状態を管理
window.fileRowDisplay = {};
window.fileMetaDisplay = {};
function toggleFileSection(idx) {
  var wrap = document.getElementById('file-content-wrap-' + idx);
  var header = document.getElementById('file-header-' + idx);
  if (wrap.style.display === 'none') {
    wrap.style.display = '';
    header.classList.add('active');
    // 状態復元
    var fileId = 'file' + idx;
    var showAll = (window.fileRowDisplay[fileId] === 'all');
    toggleRows(fileId, showAll, true); // 状態復元
    var metaId = 'meta-' + fileId;
    var metaEl = document.getElementById(metaId);
    if (window.fileMetaDisplay[fileId] === 'show') {
      metaEl.style.display = '';
    } else {
      metaEl.style.display = 'none';
    }
  } else {
    wrap.style.display = 'none';
    header.classList.remove('active');
  }
}
function toggleRows(fileId, showAll, restoreOnly) {
  var allRows = document.querySelectorAll('.row-' + fileId);
  allRows.forEach(function(row) {
    if (showAll) {
      row.style.display = '';
    } else {
      if (row.classList.contains('row-unchanged')) {
        row.style.display = 'none';
      } else {
        row.style.display = '';
      }
    }
  });
  if (!restoreOnly) {
    window.fileRowDisplay[fileId] = showAll ? 'all' : 'diff';
  }
}
function toggleDisplay(id, fileId) {
  var el = document.getElementById(id);
  if (el.style.display === 'none') { el.style.display = ''; if(fileId) window.fileMetaDisplay[fileId] = 'show'; } else { el.style.display = 'none'; if(fileId) window.fileMetaDisplay[fileId] = 'hide'; }
}
''')
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>jpclins StructureDefinition Elements差分レポート (1.9.0 → 1.10.0)</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }}
        #sidebar {{
            position: fixed;
            left: 0;
            top: 0;
            width: 340px;
            height: 100vh;
            background: #f8f9fa;
            border-right: 1px solid #e9ecef;
            overflow-y: auto;
            z-index: 100;
            padding: 30px 0 30px 0;
            box-shadow: 2px 0 8px rgba(0,0,0,0.04);
        }}
        #sidebar h3 {{
            margin: 0 0 16px 32px;
            font-size: 1.2em;
            color: #1976d2;
        }}
        #sidebar-list {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding: 0 0 0 24px;
        }}
        .sidebar-item {{
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
            padding: 8px 16px;
            margin-right: 16px;
            margin-bottom: 0;
            transition: background 0.2s, box-shadow 0.2s;
            white-space: nowrap;
            overflow-x: auto;
            max-width: 260px;
        }}
        .sidebar-item:hover {{
            background: #e3f2fd;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .sidebar-item a {{
            color: #007bff;
            text-decoration: none;
            font-weight: 500;
        }}
        .sidebar-item a:hover {{
            text-decoration: underline;
        }}
        #main-content {{
            margin-left: 360px;
            padding: 30px;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .summary {{
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }}
        .content {{
            padding: 30px;
        }}
        .file-section {{
            margin-bottom: 40px;
        }}
        .file-header {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 0;
            display: flex;
            align-items: center;
            cursor: pointer;
        }}
        .file-header h2 {{
            margin: 0;
            color: #1976d2;
            flex: 1;
            font-size: 1.1em;
        }}
        .file-header .badge, .file-header .toggle-btn, .file-header .fold-btn {{
            /* pointer-events: none; を削除 */
        }}
        .file-header.active {{
            background: #1976d2;
            color: #fff;
        }}
        .file-header.active h2 {{
            color: #fff;
        }}
        .file-content-wrap {{
            /* 追加 */
        }}
        .file-content-wrap.collapsed {{
            display: none;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.9em;
            margin-left: 8px;
        }}
        .badge-added {{
            background: #28a745;
            color: white;
        }}
        .badge-removed {{
            background: #dc3545;
            color: white;
        }}
        .badge-modified {{
            background: #ffc107;
            color: #333;
        }}
        .badge-unchanged {{
            background: #6c757d;
            color: white;
        }}
        .toggle-btn {{
            background: #007bff;
            color: white;
            border: none;
            padding: 6px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
        }}
        .toggle-btn:hover {{
            background: #0056b3;
        }}
        .table-container {{
            max-height: 500px;
            overflow: auto;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            margin-top: 20px;
        }}
        .elements-table {{
            width: 100%;
            min-width: 2000px;
            border-collapse: collapse;
        }}
        .elements-table th, .elements-table td {{
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
            vertical-align: top;
            font-size: 0.9em;
        }}
        .elements-table th {{
            background-color: #f8f9fa;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        .elements-table tr:hover {{
            background-color: #f8f9fa;
        }}
        .row-added {{
            background-color: #d4edda !important;
        }}
        .row-removed {{
            background-color: #f8d7da !important;
        }}
        .row-modified {{
            background-color: #fff3cd !important;
        }}
        .cell-added {{
            background-color: #c3e6cb;
            color: #155724;
        }}
        .cell-removed {{
            background-color: #f5c6cb;
            color: #721c24;
        }}
        .cell-modified {{
            background-color: #ffeaa7;
            color: #856404;
        }}
        .path-cell {{
            font-weight: bold;
            font-family: 'Courier New', monospace;
            background-color: #f8f9fa;
        }}
        .no-value {{
            color: #6c757d;
            font-style: italic;
        }}
        .complex-value {{
            background-color: #f8f9fa;
            padding: 4px;
            border-radius: 2px;
            font-size: 0.8em;
            max-width: 300px;
            overflow-x: auto;
            white-space: pre-wrap;
        }}
        .diff-cell-content {{
            max-height: 200px;
            overflow-y: auto;
        }}
        .legend {{
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 20px;
        }}
        .legend-color {{
            display: inline-block;
            width: 20px;
            height: 20px;
            margin-right: 5px;
            border-radius: 2px;
        }}
        .fold-btn {{
            background: #888;
            color: white;
            border: none;
            padding: 2px 10px;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
            font-size: 0.9em;
        }}
        .fold-btn:hover {{
            background: #444;
        }}
        .diff-added {{
            background-color: #d4edda;
            color: #155724;
            padding: 2px 8px;
            border-radius: 4px;
            margin: 2px 0;
            font-size: 0.9em;
        }}
        .diff-removed {{
            background-color: #f8d7da;
            color: #721c24;
            padding: 2px 8px;
            border-radius: 4px;
            margin: 2px 0;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
<div id="sidebar">
<h3>差分ファイル一覧</h3>
<div id="sidebar-list">
{''.join(sidebar_items)}
</div>
</div>
<div id="main-content">
<div class="container">
<div class="header">
<h1>jpclins StructureDefinition Elements差分レポート</h1>
<p>バージョン 1.9.0 → 1.10.0 の比較結果</p>
<p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
</div>
<div class="summary">
<h2>差分サマリー</h2>
<p>比較対象ファイル数: {total_files}</p>
<p>変更ありファイル数: {len(modified_files)}</p>
</div>
<div style="margin-bottom:24px;">
<button class="fold-btn" onclick="toggleDisplay('script-info')">追加情報（スクリプト全文など）表示/非表示</button>
<div id="script-info" style="display:none;">{script_html}</div>
</div>
<div class="content">
<div class="legend">
<h3>凡例</h3>
<div class="legend-item"><span class="legend-color" style="background-color: #d4edda;"></span>新規追加</div>
<div class="legend-item"><span class="legend-color" style="background-color: #f8d7da;"></span>削除</div>
<div class="legend-item"><span class="legend-color" style="background-color: #fff3cd;"></span>変更</div>
</div>"""
        
        # 変更されたファイルごとにテーブルを生成
        for file_idx, (filename, differences) in enumerate(modified_files):
            # 件数集計
            count_added = sum(1 for d in differences if d['type'] == 'added')
            count_removed = sum(1 for d in differences if d['type'] == 'removed')
            count_modified = sum(1 for d in differences if d['type'] == 'modified')
            count_unchanged = sum(1 for d in differences if d['type'] == 'unchanged')
            file_id = f"file{file_idx}"
            meta = self.get_file_metadata(v2_package / filename if (v2_package / filename).exists() else v1_package / filename)
            file_meta_map[filename] = meta
            sidebar_items.append(f'<div class="sidebar-item" title="{filename}"><a href="#file-{file_idx}">{filename}</a></div>')
            desc = meta.get("description") or filename
            meta_html = self.get_file_metadata_html(meta)
            html_content += f"""
<a id="file-{file_idx}"></a>
<div class="file-section">
  <div class="file-header active" id="file-header-{file_idx}" onclick="toggleFileSection({file_idx})">
    <h2>{desc}</h2>
    <span class="badge badge-added">追加: {count_added}</span>
    <span class="badge badge-removed">削除: {count_removed}</span>
    <span class="badge badge-modified">変更: {count_modified}</span>
    <span class="badge badge-unchanged">変更なし: {count_unchanged}</span>
    <button class="toggle-btn" onclick="event.stopPropagation();toggleRows('{file_id}', false)">差分のみ表示</button>
    <button class="toggle-btn" onclick="event.stopPropagation();toggleRows('{file_id}', true)">全行表示</button>
    <button class="fold-btn" onclick="event.stopPropagation();toggleDisplay('meta-{file_id}', '{file_id}')">メタ情報表示/非表示</button>
  </div>
  <div class="file-content-wrap" id="file-content-wrap-{file_idx}">
    <div id="meta-{file_id}" style="display:none;margin-bottom:10px;">{meta_html}</div>
    <div class="table-container">
      <table class="elements-table">
        <thead>
          <tr>
            <th>Path</th>
            <th>Type</th>"""
            
            # 全属性のヘッダーを生成
            for attr in sorted(self.all_attributes):
                if attr != 'path':  # pathは既に別列にあるので除外
                    html_content += f"""
                                <th>{attr}</th>"""
            
            html_content += """
                            </tr>
                        </thead>
                        <tbody>"""
            
            # 各行を生成
            for diff in differences:
                row_class = f"row-{diff['type']} row-{file_id}"
                display_style = '' if diff['type'] != 'unchanged' else 'style="display:none"'
                html_content += f"""
                            <tr class="{row_class}" {display_style}>
                                <td class="path-cell">{diff['path']}</td>
                                <td>{diff['type']}</td>"""
                
                # 各属性の値を生成
                for attr in sorted(self.all_attributes):
                    if attr == 'path':
                        continue
                    
                    v1_element = diff.get('v1_element', {})
                    v2_element = diff.get('v2_element', {})
                    
                    v1_value = v1_element.get(attr) if v1_element else None
                    v2_value = v2_element.get(attr) if v2_element else None
                    
                    if diff['type'] == 'added':
                        cell_class = 'cell-added'
                        cell_content = f"""
                                    <td class="{cell_class}"><div class="diff-cell-content">{self.format_value(v2_value)}</div></td>"""
                    elif diff['type'] == 'removed':
                        cell_class = 'cell-removed'
                        cell_content = f"""
                                    <td class="{cell_class}"><div class="diff-cell-content">{self.format_value(v1_value)}</div></td>"""
                    elif diff['type'] == 'modified':
                        if v1_value != v2_value:
                            cell_class = 'cell-modified'
                            cell_content = f"""
                                    <td class="{cell_class}"><div class="diff-cell-content">{self.html_diff(v1_value, v2_value)}</div></td>"""
                        else:
                            cell_content = f"""
                                    <td><div class="diff-cell-content">{self.format_value(v1_value)}</div></td>"""
                    else:  # unchanged
                        cell_content = f"""
                                    <td><div class="diff-cell-content">{self.format_value(v1_value)}</div></td>"""
                    
                    html_content += cell_content
                
                html_content += """
                            </tr>"""
            
            html_content += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>"""
        
        html_content += """
        </div>
    </div>
""" + f"<script>{js_script}</script>" + """
</body>
</html>"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTMLレポートが生成されました: {output_file}")
        return output_file

def main():
    """メイン関数"""
    if len(sys.argv) >= 3:
        v1_path = sys.argv[1]
        v2_path = sys.argv[2]
    else:
        v1_path = "jp-eCSCLINS.r4-1.9.0-snap"
        v2_path = "jp-eCSCLINS.r4-1.10.0-snap"
        print("使い方: python compare_structure_definition_elements.py <旧バージョンフォルダ> <新バージョンフォルダ>")
        print(f"デフォルト: {v1_path} → {v2_path}")
    
    print("jpclins StructureDefinition Elements差分比較を開始します...")
    print(f"比較対象: {v1_path} → {v2_path}")
    
    comparator = StructureDefinitionElementComparator(v1_path, v2_path)
    
    print("ファイル一覧を取得中...")
    comparator.compare_files()
    
    print("HTMLレポートを生成中...")
    output_file = comparator.generate_html_report()
    
    print(f"\n✅ 完了！")
    print(f"レポートファイル: {output_file}")
    print(f"ブラウザで {output_file} を開いて差分を確認してください。")

if __name__ == "__main__":
    main() 