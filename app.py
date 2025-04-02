from flask import Flask, render_template, send_file, request, jsonify, url_for
import os
from md_to_image import convert_md_to_image
import glob
from datetime import datetime, timedelta
import json
import subprocess
import sys
from llm_analyzer import LLMAnalyzer
from dotenv import load_dotenv
import re

# 加载 .env 文件
load_dotenv()

app = Flask(__name__)

# 创建 LLMAnalyzer 实例，使用环境变量
llm_analyzer = LLMAnalyzer(
    api_key=os.getenv('LLM_API_KEY'),
    model_name=os.getenv('LLM_MODEL_NAME', 'gpt-4'),
    base_url=os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')
)

def get_report_files():
    """获取所有报告文件"""
    files = []
    reports_dir = 'reports'
    
    try:
        # 遍历reports目录下的所有日期文件夹
        for date_dir in sorted(os.listdir(reports_dir), reverse=True):
            dir_path = os.path.join(reports_dir, date_dir)
            if os.path.isdir(dir_path) and date_dir != 'lastest':
                # 查找该日期目录下的report文件
                for file in os.listdir(dir_path):
                    if file.endswith('.md') and 'report' in file:
                        file_path = os.path.join(dir_path, file)
                        files.append({
                            'name': file,
                            'path': file_path,
                            'date': date_dir,
                            'type': '日报'
                        })
    except Exception as e:
        print(f"Error reading files: {str(e)}")
        return []
        
    return files

def get_config_from_request():
    """从请求中获取配置"""
    if request.is_json:
        return request.get_json()
    return {
        'darkMode': request.args.get('darkMode', 'false').lower() == 'true',
        'showLineNumbers': request.args.get('showLineNumbers', 'false').lower() == 'true',
        'style': {
            'background': request.args.get('background'),
            'text': request.args.get('text'),
            'header_bg': request.args.get('header_bg'),
            'header_gradient': request.args.get('header_gradient'),
            'container_bg': request.args.get('container_bg'),
            'topic_bg': request.args.get('topic_bg'),
            'topic_border': request.args.get('topic_border'),
            'title_color': request.args.get('title_color'),
            'content_color': request.args.get('content_color'),
            'footer_color': request.args.get('footer_color'),
            'table_border': request.args.get('table_border'),
            'table_header_bg': request.args.get('table_header_bg'),
            'table_header_text': request.args.get('table_header_text'),
            'code_bg': request.args.get('code_bg'),
            'code_text': request.args.get('code_text'),
            'pre_bg': request.args.get('pre_bg'),
            'pre_text': request.args.get('pre_text')
        },
        'font': {
            'body': request.args.get('font_body'),
            'code': request.args.get('font_code')
        },
        'size': {
            'container_width': request.args.get('container_width'),
            'logo_size': request.args.get('logo_size'),
            'header_padding': request.args.get('header_padding'),
            'topic_padding': request.args.get('topic_padding'),
            'topic_margin': request.args.get('topic_margin'),
            'border_radius': request.args.get('border_radius')
        }
    }

@app.route('/')
def index():
    try:
        reports_dir = 'reports'
        files = []
        
        # 遍历 reports 目录下的所有日期目录
        for date_dir in os.listdir(reports_dir):
            date_path = os.path.join(reports_dir, date_dir)
            if not os.path.isdir(date_path):
                continue
                
            # 遍历日期目录下的所有 Markdown 文件
            for filename in os.listdir(date_path):
                if not filename.endswith('.md'):
                    continue
                    
                # 使用相对路径，确保路径格式正确
                relative_path = os.path.join('reports', date_dir, filename).replace('\\', '/')
                full_path = os.path.join(date_path, filename)
                file_stat = os.stat(full_path)
                
                files.append({
                    'name': filename,
                    'path': relative_path,  # 使用相对路径
                    'size': file_stat.st_size,
                    'date': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        # 按日期降序排序
        files.sort(key=lambda x: x['date'], reverse=True)
        
        return render_template('index.html', files=files)
    except Exception as e:
        print(f"Error listing files: {str(e)}")
        return render_template('index.html', error=str(e))

@app.route('/preview/<path:filename>')
def preview(filename):
    """预览文件"""
    try:
        # 安全检查：确保文件路径在reports目录下
        safe_path = os.path.normpath(filename)
        if not safe_path.startswith('reports'):
            return jsonify({'error': 'Invalid file path'}), 400
            
        # 获取所在的日期目录和文件名
        dir_path = os.path.dirname(safe_path)
        base_name = os.path.basename(safe_path)
        
        # 检查预览图片是否存在（与 md 文件位于同一目录）
        preview_filename = os.path.splitext(base_name)[0] + '.png'
        preview_path = os.path.join(dir_path, preview_filename)
        
        # 如果预览图片不存在，先生成
        if not os.path.exists(preview_path) or os.path.getsize(preview_path) == 0:
            convert_md_to_image(safe_path, preview_path, width=600)
        
        if os.path.exists(preview_path) and os.path.getsize(preview_path) > 0:
            # 使用 /reports/ 路径访问预览图片
            preview_url = '/' + preview_path.replace('\\', '/')
            return jsonify({
                'success': True,
                'preview_url': preview_url
            })
        else:
            return jsonify({'error': 'Failed to generate preview'}), 500
            
    except Exception as e:
        print(f"预览错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/content/<path:filename>')
def content(filename):
    """获取文件内容"""
    try:
        # 安全检查：确保文件路径在reports目录下
        safe_path = os.path.normpath(filename)
        if not safe_path.startswith('reports'):
            return jsonify({'error': 'Invalid file path'}), 400
            
        # 读取文件内容
        if os.path.exists(safe_path):
            with open(safe_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({
                'success': True,
                'content': content
            })
        else:
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        print(f"读取内容错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/regenerate/<path:filename>')
def regenerate(filename):
    """重新生成预览图片"""
    try:
        # 确保文件路径安全
        safe_path = os.path.normpath(filename)
        if not safe_path.startswith('reports'):
            return jsonify({"error": "Invalid file path"}), 400
            
        # 获取所在的日期目录和文件名
        dir_path = os.path.dirname(safe_path)
        base_name = os.path.basename(safe_path)
        
        # 设置预览图片路径（与 md 文件位于同一目录）
        preview_filename = os.path.splitext(base_name)[0] + '.png'
        preview_path = os.path.join(dir_path, preview_filename)
        
        # 生成预览图片
        convert_md_to_image(safe_path, preview_path, width=600)
        
        # 检查预览图片是否生成成功
        if os.path.exists(preview_path) and os.path.getsize(preview_path) > 0:
            # 使用 /reports/ 路径访问预览图片
            preview_url = '/' + preview_path.replace('\\', '/')
            return jsonify({
                'success': True,
                'preview_url': preview_url
            })
        else:
            return jsonify({"error": "Failed to regenerate preview"}), 500
            
    except Exception as e:
        print(f"重新生成错误: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/regenerate-md/<path:filename>')
def regenerate_md(filename):
    """使用大模型重新生成MD文件"""
    try:
        # 确保文件路径安全
        safe_path = os.path.normpath(filename)
        if not safe_path.startswith('reports'):
            return jsonify({"error": "Invalid file path"}), 400

        # 从 main.py 导入必要的组件
        from main import llm_analyzer, translator
            
        # 获取所在的日期目录和文件名
        dir_path = os.path.dirname(safe_path)
        
        # 从 MD 文件路径中找到对应的原始数据文件
        raw_data_file = safe_path.replace('_report', '_raw').replace('.md', '.txt')
        
        print(f"Looking for raw data file: {raw_data_file}")
        
        if not os.path.exists(raw_data_file):
            return jsonify({"error": f"Raw data file not found: {raw_data_file}"}), 404
            
        # 获取时间范围，与 main.py 中保持一致
        now = datetime.utcnow()
        time_ranges = {
            "24h": now - timedelta(hours=24),
            "week": now - timedelta(days=7),
            "month": now - timedelta(days=30)
        }
        
        # 调用 generate_report 函数重新生成报告
        success = llm_analyzer.generate_report(raw_data_file, safe_path, time_ranges, translator)
        
        if success:
            # 生成预览图片
            base_name = os.path.basename(safe_path)
            preview_filename = os.path.splitext(base_name)[0] + '.png'
            preview_path = os.path.join(dir_path, preview_filename)
            
            convert_md_to_image(safe_path, preview_path, width=600)
            
            return jsonify({
                'success': True,
                'message': '报告重新生成成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '报告重新生成失败'
            })
            
    except Exception as e:
        print(f"重新生成MD错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/regenerate-all')
def regenerate_all():
    try:
        # 获取配置参数
        config = get_config_from_request()
        
        # 遍历所有文件并重新生成预览
        reports_dir = 'reports'
        results = []
        
        for date_dir in os.listdir(reports_dir):
            date_path = os.path.join(reports_dir, date_dir)
            if not os.path.isdir(date_path):
                continue
                
            for filename in os.listdir(date_path):
                if not filename.endswith('.md'):
                    continue
                    
                file_path = os.path.join(date_path, filename)
                relative_path = os.path.join('reports', date_dir, filename).replace('\\', '/')
                
                # 强制重新生成预览图片
                image_path = convert_md_to_image(relative_path, config, force=True)
                if image_path:
                    results.append({'file': filename, 'success': True})
                else:
                    results.append({'file': filename, 'success': False, 'error': '生成预览失败'})
        
        return jsonify({'results': results})
    except Exception as e:
        print(f"Regenerate all error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/generate-report', methods=['POST'])
def generate_report():
    try:
        # 直接调用 llm_analyzer.generate_report 方法
        success = llm_analyzer.generate_report()
        
        if success:
            return jsonify({
                'success': True,
                'message': '报告生成成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '报告生成失败'
            })
    except Exception as e:
        print(f"Generate report error: {str(e)}")
        return jsonify({
            'success': False,
            'message': '执行失败',
            'error': str(e)
        })

# 添加一个新路由，用于直接访问 reports 文件夹中的文件
@app.route('/reports/<path:filename>')
def reports_files(filename):
    return send_file(os.path.join('reports', filename))

@app.route('/generate-today', methods=['POST'])
def generate_today():
    """生成当天的完整报告"""
    try:
        # 导入 main 函数
        from main import main
        
        # 执行 main 函数
        success = main()
        
        if success:
            # 获取当前日期
            current_date = datetime.now().strftime("%Y-%m-%d")
            date_dir = os.path.join("reports", current_date)
            
            if os.path.exists(date_dir):
                # 查找新生成的报告文件
                report_file = os.path.join(date_dir, f"reddit_report_{current_date}.md")
                preview_file = os.path.join(date_dir, f"reddit_report_{current_date}.png")
                
                if os.path.exists(report_file):
                    return jsonify({
                        'success': True,
                        'message': '今日报告生成成功',
                        'report_path': report_file
                    })
            
            return jsonify({
                'success': True,
                'message': '今日报告生成成功，但文件未找到'
            })
        else:
            return jsonify({
                'success': False,
                'message': '今日报告生成失败'
            })
    
    except Exception as e:
        print(f"生成今日报告错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 