#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jpclins StructureDefinitionファイルの差分比較ツール
1.9.0と1.10.0のバージョン間の差分をテーブル形式のHTMLレポートとして出力
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
import difflib

class StructureDefinitionComparator:
    def __init__(self, v1_path, v2_path):
        self.v1_path = Path(v1_path)
        self.v2_path = Path(v2_path)
        self.v1_files = {}
        self.v2_files = {}
        self.differences = []
        
    def get_file_hash(self, file_path):
        """ファイルのMD5ハッシュを計算"""
        if not file_path.exists():
            return None
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def get_file_size(self, file_path):
        """ファイルサイズを取得"""
        if not file_path.exists():
            return None
        return file_path.stat().st_size
    
    def parse_structure_definition(self, file_path):
        """StructureDefinitionファイルを解析してプロファイル情報を抽出"""
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # プロファイル情報を抽出
            profile_info = {
                'url': data.get('url', ''),
                'version': data.get('version', ''),
                'name': data.get('name', ''),
                'title': data.get('title', ''),
                'status': data.get('status', ''),
                'date': data.get('date', ''),
                'publisher': data.get('publisher', ''),
                'description': data.get('description', ''),
                'purpose': data.get('purpose', ''),
                'copyright': data.get('copyright', ''),
                'fhirVersion': data.get('fhirVersion', ''),
                'kind': data.get('kind', ''),
                'abstract': data.get('abstract', False),
                'type': data.get('type', ''),
                'baseDefinition': data.get('baseDefinition', ''),
                'derivation': data.get('derivation', ''),
                'differential': {
                    'element_count': len(data.get('differential', {}).get('element', [])) if data.get('differential') else 0
                },
                'snapshot': {
                    'element_count': len(data.get('snapshot', {}).get('element', [])) if data.get('snapshot') else 0
                }
            }
            
            return profile_info
        except Exception as e:
            return {'error': str(e)}
    
    def compare_files(self):
        """両バージョンのStructureDefinitionファイルを比較"""
        # 1.9.0のStructureDefinitionファイル一覧を取得
        v1_package = self.v1_path / "package"
        if v1_package.exists():
            for file_path in v1_package.glob("StructureDefinition-*.json"):
                self.v1_files[file_path.name] = {
                    'path': file_path,
                    'size': self.get_file_size(file_path),
                    'hash': self.get_file_hash(file_path),
                    'profile_info': self.parse_structure_definition(file_path)
                }
        
        # 1.10.0のStructureDefinitionファイル一覧を取得
        v2_package = self.v2_path / "package"
        if v2_package.exists():
            for file_path in v2_package.glob("StructureDefinition-*.json"):
                self.v2_files[file_path.name] = {
                    'path': file_path,
                    'size': self.get_file_size(file_path),
                    'hash': self.get_file_hash(file_path),
                    'profile_info': self.parse_structure_definition(file_path)
                }
    
    def analyze_differences(self):
        """差分を分析"""
        all_files = set(self.v1_files.keys()) | set(self.v2_files.keys())
        
        for filename in sorted(all_files):
            v1_info = self.v1_files.get(filename)
            v2_info = self.v2_files.get(filename)
            
            if not v1_info and v2_info:
                # 1.10.0で新規追加
                self.differences.append({
                    'filename': filename,
                    'type': 'added',
                    'v1_info': None,
                    'v2_info': v2_info
                })
            elif v1_info and not v2_info:
                # 1.10.0で削除
                self.differences.append({
                    'filename': filename,
                    'type': 'removed',
                    'v1_info': v1_info,
                    'v2_info': None
                })
            elif v1_info and v2_info:
                if v1_info['hash'] != v2_info['hash']:
                    # 内容が変更された
                    self.differences.append({
                        'filename': filename,
                        'type': 'modified',
                        'v1_info': v1_info,
                        'v2_info': v2_info
                    })
    
    def generate_detailed_diff(self, filename):
        """特定のファイルの詳細な差分を生成"""
        v1_file = self.v1_files.get(filename, {}).get('path')
        v2_file = self.v2_files.get(filename, {}).get('path')
        
        if not v1_file or not v2_file:
            return None
        
        try:
            with open(v1_file, 'r', encoding='utf-8') as f1:
                v1_content = f1.readlines()
            with open(v2_file, 'r', encoding='utf-8') as f2:
                v2_content = f2.readlines()
            
            diff = difflib.unified_diff(
                v1_content, v2_content,
                fromfile=f'1.9.0/{filename}',
                tofile=f'1.10.0/{filename}',
                lineterm=''
            )
            return list(diff)
        except Exception as e:
            return [f"Error reading file: {e}"]
    
    def generate_html_report(self, output_file="structure_definition_diff_report.html"):
        """HTMLレポートを生成"""
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>jpclins StructureDefinition差分レポート (1.9.0 → 1.10.0)</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
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
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #495057;
        }}
        .summary-card .number {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #495057;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .table-container {{
            overflow-x: auto;
            border: 1px solid #e9ecef;
            border-radius: 4px;
        }}
        .profile-table {{
            width: 100%;
            min-width: 1200px;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .profile-table th, .profile-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
            vertical-align: top;
        }}
        .profile-table th {{
            background-color: #f8f9fa;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        .profile-table tr:hover {{
            background-color: #f8f9fa;
        }}
        .status-added {{
            color: #28a745;
            font-weight: bold;
        }}
        .status-removed {{
            color: #dc3545;
            font-weight: bold;
        }}
        .status-modified {{
            color: #ffc107;
            font-weight: bold;
        }}
        .diff-content {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 15px;
            margin-top: 10px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
        }}
        .diff-line {{
            padding: 2px 0;
        }}
        .diff-added {{
            background-color: #d4edda;
            color: #155724;
        }}
        .diff-removed {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .diff-context {{
            background-color: #f8f9fa;
            color: #6c757d;
        }}
        .toggle-btn {{
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 10px;
        }}
        .toggle-btn:hover {{
            background: #0056b3;
        }}
        .hidden {{
            display: none;
        }}
        .version-header {{
            background-color: #e3f2fd;
            font-weight: bold;
            text-align: center;
        }}
        .field-name {{
            font-weight: bold;
            color: #495057;
        }}
        .field-value {{
            word-break: break-word;
            max-width: 300px;
        }}
        .no-data {{
            color: #6c757d;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>jpclins StructureDefinition差分レポート</h1>
            <p>バージョン 1.9.0 → 1.10.0 の比較結果</p>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <h2>差分サマリー</h2>
            <div class="summary-grid">
"""
        
        # 統計情報を計算
        added_count = len([d for d in self.differences if d['type'] == 'added'])
        removed_count = len([d for d in self.differences if d['type'] == 'removed'])
        modified_count = len([d for d in self.differences if d['type'] == 'modified'])
        unchanged_count = len(self.v1_files) - modified_count - removed_count
        
        html_content += (
            '<div class="summary-card">\n'
            '    <h3>新規追加</h3>\n'
            '    <div class="number status-added">' + str(added_count) + '</div>\n'
            '</div>\n'
        )
        html_content += (
            '<div class="summary-card">\n'
            '    <h3>削除</h3>\n'
            '    <div class="number status-removed">' + str(removed_count) + '</div>\n'
            '</div>\n'
        )
        html_content += (
            '<div class="summary-card">\n'
            '    <h3>変更</h3>\n'
            '    <div class="number status-modified">' + str(modified_count) + '</div>\n'
            '</div>\n'
        )
        html_content += (
            '<div class="summary-card">\n'
            '    <h3>変更なし</h3>\n'
            '    <div class="number">' + str(unchanged_count) + '</div>\n'
            '</div>\n'
        )
        html_content += (
            '</div>\n'
            '</div>\n'
        )
        
        html_content += (
            '<div class="content">\n'
        )
        
        # 新規追加されたファイル
        if added_count > 0:
            html_content += (
                '<div class="section">\n'
                '    <h2>新規追加されたStructureDefinition</h2>\n'
                '    <div class="table-container">\n'
                '        <table class="profile-table">\n'
                '            <thead>\n'
                '                <tr>\n'
                '                    <th>項目</th>\n'
                '                    <th>1.10.0</th>\n'
                '                </tr>\n'
                '            </thead>\n'
                '            <tbody>\n'
            )
            for diff in self.differences:
                if diff['type'] == 'added':
                    v2_info = diff['v2_info']['profile_info']
                    html_content += (
                        f'                <tr>\n'
                        f'                    <td class="field-name">ファイル名</td>\n'
                        f'                    <td class="field-value">{diff["filename"]}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">URL</td>\n'
                        f'                    <td class="field-value">{v2_info.get("url", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">バージョン</td>\n'
                        f'                    <td class="field-value">{v2_info.get("version", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">名前</td>\n'
                        f'                    <td class="field-value">{v2_info.get("name", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">タイトル</td>\n'
                        f'                    <td class="field-value">{v2_info.get("title", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">ステータス</td>\n'
                        f'                    <td class="field-value">{v2_info.get("status", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">日付</td>\n'
                        f'                    <td class="field-value">{v2_info.get("date", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">発行者</td>\n'
                        f'                    <td class="field-value">{v2_info.get("publisher", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">説明</td>\n'
                        f'                    <td class="field-value">{v2_info.get("description", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">目的</td>\n'
                        f'                    <td class="field-value">{v2_info.get("purpose", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">著作権</td>\n'
                        f'                    <td class="field-value">{v2_info.get("copyright", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">FHIRバージョン</td>\n'
                        f'                    <td class="field-value">{v2_info.get("fhirVersion", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">種類</td>\n'
                        f'                    <td class="field-value">{v2_info.get("kind", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">抽象</td>\n'
                        f'                    <td class="field-value">{v2_info.get("abstract", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">タイプ</td>\n'
                        f'                    <td class="field-value">{v2_info.get("type", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">基本定義</td>\n'
                        f'                    <td class="field-value">{v2_info.get("baseDefinition", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">派生</td>\n'
                        f'                    <td class="field-value">{v2_info.get("derivation", "")}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">差分要素数</td>\n'
                        f'                    <td class="field-value">{v2_info.get("differential", {}).get("element_count", 0)}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td class="field-name">スナップショット要素数</td>\n'
                        f'                    <td class="field-value">{v2_info.get("snapshot", {}).get("element_count", 0)}</td>\n'
                        f'                </tr>\n'
                        f'                <tr>\n'
                        f'                    <td colspan="2" style="height: 20px; background-color: #f8f9fa;"></td>\n'
                        f'                </tr>\n'
                    )
            html_content += (
                '            </tbody>\n'
                '        </table>\n'
                '    </div>\n'
                '</div>\n'
            )
        
        # 削除されたファイル
        if removed_count > 0:
            html_content += """
            <div class="section">
                <h2>削除されたStructureDefinition</h2>
                <div class="table-container">
                    <table class="profile-table">
                        <thead>
                            <tr>
                                <th>項目</th>
                                <th>1.9.0</th>
                            </tr>
                        </thead>
                        <tbody>
"""
            for diff in self.differences:
                if diff['type'] == 'removed':
                    v1_info = diff['v1_info']['profile_info']
                    html_content += f"""
                        <tr>
                            <td class="field-name">ファイル名</td>
                            <td class="field-value">{diff['filename']}</td>
                        </tr>
                        <tr>
                            <td class="field-name">URL</td>
                            <td class="field-value">{v1_info.get('url', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">バージョン</td>
                            <td class="field-value">{v1_info.get('version', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">名前</td>
                            <td class="field-value">{v1_info.get('name', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">タイトル</td>
                            <td class="field-value">{v1_info.get('title', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">ステータス</td>
                            <td class="field-value">{v1_info.get('status', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">日付</td>
                            <td class="field-value">{v1_info.get('date', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">発行者</td>
                            <td class="field-value">{v1_info.get('publisher', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">説明</td>
                            <td class="field-value">{v1_info.get('description', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">目的</td>
                            <td class="field-value">{v1_info.get('purpose', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">著作権</td>
                            <td class="field-value">{v1_info.get('copyright', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">FHIRバージョン</td>
                            <td class="field-value">{v1_info.get('fhirVersion', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">種類</td>
                            <td class="field-value">{v1_info.get('kind', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">抽象</td>
                            <td class="field-value">{v1_info.get('abstract', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">タイプ</td>
                            <td class="field-value">{v1_info.get('type', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">基本定義</td>
                            <td class="field-value">{v1_info.get('baseDefinition', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">派生</td>
                            <td class="field-value">{v1_info.get('derivation', '')}</td>
                        </tr>
                        <tr>
                            <td class="field-name">差分要素数</td>
                            <td class="field-value">{v1_info.get('differential', {}).get('element_count', 0)}</td>
                        </tr>
                        <tr>
                            <td class="field-name">スナップショット要素数</td>
                            <td class="field-value">{v1_info.get('snapshot', {}).get('element_count', 0)}</td>
                        </tr>
                        <tr>
                            <td colspan="2" style="height: 20px; background-color: #f8f9fa;"></td>
                        </tr>
"""
            html_content += """
                        </tbody>
                    </table>
                </div>
            </div>
"""
        
        # 変更されたファイル
        if modified_count > 0:
            html_content += """
            <div class="section">
                <h2>変更されたStructureDefinition</h2>
                <div class="table-container">
                    <table class="profile-table">
                        <thead>
                            <tr>
                                <th>項目</th>
                                <th>1.9.0</th>
                                <th>1.10.0</th>
                                <th>詳細差分</th>
                            </tr>
                        </thead>
                        <tbody>
"""
            for diff in self.differences:
                if diff['type'] == 'modified':
                    v1_info = diff['v1_info']['profile_info']
                    v2_info = diff['v2_info']['profile_info']
                    
                    html_content += f"""
                        <tr class="version-header">
                            <td colspan="4">{diff['filename']}</td>
                        </tr>
                        <tr>
                            <td class="field-name">URL</td>
                            <td class="field-value">{v1_info.get('url', '')}</td>
                            <td class="field-value">{v2_info.get('url', '')}</td>
                            <td>
                                <button class="toggle-btn" onclick="toggleDiff('diff-{diff['filename'].replace('.', '-')}')">
                                    差分を表示
                                </button>
                            </td>
                        </tr>
                        <tr>
                            <td class="field-name">バージョン</td>
                            <td class="field-value">{v1_info.get('version', '')}</td>
                            <td class="field-value">{v2_info.get('version', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">名前</td>
                            <td class="field-value">{v1_info.get('name', '')}</td>
                            <td class="field-value">{v2_info.get('name', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">タイトル</td>
                            <td class="field-value">{v1_info.get('title', '')}</td>
                            <td class="field-value">{v2_info.get('title', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">ステータス</td>
                            <td class="field-value">{v1_info.get('status', '')}</td>
                            <td class="field-value">{v2_info.get('status', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">日付</td>
                            <td class="field-value">{v1_info.get('date', '')}</td>
                            <td class="field-value">{v2_info.get('date', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">発行者</td>
                            <td class="field-value">{v1_info.get('publisher', '')}</td>
                            <td class="field-value">{v2_info.get('publisher', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">説明</td>
                            <td class="field-value">{v1_info.get('description', '')}</td>
                            <td class="field-value">{v2_info.get('description', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">目的</td>
                            <td class="field-value">{v1_info.get('purpose', '')}</td>
                            <td class="field-value">{v2_info.get('purpose', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">著作権</td>
                            <td class="field-value">{v1_info.get('copyright', '')}</td>
                            <td class="field-value">{v2_info.get('copyright', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">FHIRバージョン</td>
                            <td class="field-value">{v1_info.get('fhirVersion', '')}</td>
                            <td class="field-value">{v2_info.get('fhirVersion', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">種類</td>
                            <td class="field-value">{v1_info.get('kind', '')}</td>
                            <td class="field-value">{v2_info.get('kind', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">抽象</td>
                            <td class="field-value">{v1_info.get('abstract', '')}</td>
                            <td class="field-value">{v2_info.get('abstract', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">タイプ</td>
                            <td class="field-value">{v1_info.get('type', '')}</td>
                            <td class="field-value">{v2_info.get('type', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">基本定義</td>
                            <td class="field-value">{v1_info.get('baseDefinition', '')}</td>
                            <td class="field-value">{v2_info.get('baseDefinition', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">派生</td>
                            <td class="field-value">{v1_info.get('derivation', '')}</td>
                            <td class="field-value">{v2_info.get('derivation', '')}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">差分要素数</td>
                            <td class="field-value">{v1_info.get('differential', {}).get('element_count', 0)}</td>
                            <td class="field-value">{v2_info.get('differential', {}).get('element_count', 0)}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td class="field-name">スナップショット要素数</td>
                            <td class="field-value">{v1_info.get('snapshot', {}).get('element_count', 0)}</td>
                            <td class="field-value">{v2_info.get('snapshot', {}).get('element_count', 0)}</td>
                            <td></td>
                        </tr>
                        <tr>
                            <td colspan="4">
                                <div id="diff-{diff['filename'].replace('.', '-')}" class="diff-content hidden">
"""
                    
                    # 詳細差分を生成
                    detailed_diff = self.generate_detailed_diff(diff['filename'])
                    if detailed_diff:
                        for line in detailed_diff:
                            if line.startswith('+'):
                                html_content += f'<div class="diff-line diff-added">{line}</div>'
                            elif line.startswith('-'):
                                html_content += f'<div class="diff-line diff-removed">{line}</div>'
                            else:
                                html_content += f'<div class="diff-line diff-context">{line}</div>'
                    
                    html_content += """
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td colspan="4" style="height: 20px; background-color: #f8f9fa;"></td>
                        </tr>
"""
            html_content += """
                        </tbody>
                    </table>
                </div>
            </div>
"""
        
        html_content += """
        </div>
    </div>
    
    <script>
        function toggleDiff(elementId) {
            const element = document.getElementById(elementId);
            const button = element.previousElementSibling;
            
            if (element.classList.contains('hidden')) {
                element.classList.remove('hidden');
                button.textContent = '差分を隠す';
            } else {
                element.classList.add('hidden');
                button.textContent = '差分を表示';
            }
        }
    </script>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTMLレポートが生成されました: {output_file}")
        return output_file

def main():
    """メイン関数"""
    v1_path = "jp-eCSCLINS.r4-1.9.0-snap"
    v2_path = "jp-eCSCLINS.r4-1.10.0-snap"
    
    print("jpclins StructureDefinitionファイルの差分比較を開始します...")
    print(f"比較対象: {v1_path} → {v2_path}")
    
    comparator = StructureDefinitionComparator(v1_path, v2_path)
    
    print("ファイル一覧を取得中...")
    comparator.compare_files()
    
    print("差分を分析中...")
    comparator.analyze_differences()
    
    print("HTMLレポートを生成中...")
    output_file = comparator.generate_html_report()
    
    print(f"\n✅ 完了！")
    print(f"レポートファイル: {output_file}")
    print(f"ブラウザで {output_file} を開いて差分を確認してください。")

if __name__ == "__main__":
    main() 