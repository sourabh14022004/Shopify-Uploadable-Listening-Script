#!/usr/bin/env python3
"""
Flask web application for CSV conversion
"""

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import tempfile
import shutil
from pathlib import Path
import pandas as pd
from main1 import process_file

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    try:
        # Check if files are present
        if 'source_files' not in request.files:
            return jsonify({'error': 'No source files provided'}), 400
        
        source_files = request.files.getlist('source_files')
        fallback_price = request.form.get('fallback_price', 'true').lower() == 'true'
        template_option = request.form.get('template_option', 'custom')  # 'default' or 'custom'
        custom_output_name = request.form.get('custom_output_name', '').strip()
        
        if not source_files or all(f.filename == '' for f in source_files):
            return jsonify({'error': 'At least one source file is required'}), 400
        
        # Handle template file
        if template_option == 'default':
            # Use default template - look for common template files in current directory
            default_template_names = [
                'SomerSault_listings1_shopify_final_inventory-fixed.csv',
                'product_template_unit_price.csv',
                'template.csv'
            ]
            template_path = None
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
            for template_name in default_template_names:
                potential_path = os.path.join(base_dir, template_name)
                if os.path.exists(potential_path):
                    template_path = potential_path
                    break
            
            if not template_path:
                return jsonify({'error': 'Default template not found. Please upload your own template or ensure "SomerSault_listings1_shopify_final_inventory-fixed.csv" exists in the application directory.'}), 400
        else:
            # Use custom template
            template_file = request.files.get('template_file')
            if not template_file or template_file.filename == '':
                return jsonify({'error': 'Template file is required'}), 400
            
            # Save template file
            template_filename = secure_filename(template_file.filename)
            template_path = os.path.join(app.config['UPLOAD_FOLDER'], template_filename)
            template_file.save(template_path)
        
        # Process each source file
        results = []
        output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        valid_source_files = [f for f in source_files if f and f.filename != '']
        file_count = len(valid_source_files)
        
        for index, source_file in enumerate(valid_source_files):
            source_filename = secure_filename(source_file.filename)
            source_path = os.path.join(app.config['UPLOAD_FOLDER'], source_filename)
            source_file.save(source_path)
            
            # Generate output filename
            display_name = None  # For showing in results
            if custom_output_name:
                # Use custom name
                if file_count > 1:
                    # Multiple files: append number
                    name_without_ext = custom_output_name.replace('.csv', '')
                    display_name = f"{name_without_ext}_{index + 1}.csv"
                    output_filename = display_name
                else:
                    # Single file: use custom name as-is
                    display_name = custom_output_name if custom_output_name.endswith('.csv') else f"{custom_output_name}.csv"
                    output_filename = display_name
            else:
                # Use default naming
                source_stem = Path(source_filename).stem
                display_name = f"{source_stem} - Converted - Shopify.csv"
                output_filename = display_name
            
            # Sanitize filename for filesystem (but keep display_name for UI)
            output_filename_sanitized = secure_filename(output_filename)
            output_path = os.path.join(output_dir, output_filename_sanitized)
            
            try:
                # Process the file
                process_file(source_path, template_path, output_path, fallback_price_to_cost=fallback_price)
                
                results.append({
                    'source': source_filename,
                    'output': output_filename_sanitized,  # For download
                    'display_name': display_name,  # For showing in UI
                    'status': 'success',
                    'download_url': f'/download/{output_filename_sanitized}'
                })
            except Exception as e:
                results.append({
                    'source': source_filename,
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'output')
    file_path = os.path.join(output_dir, secure_filename(filename))
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/view/<filename>')
def view_csv(filename):
    """Preview CSV file as HTML table"""
    output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'output')
    file_path = os.path.join(output_dir, secure_filename(filename))
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        # Read CSV file
        df = pd.read_csv(file_path, dtype=str).fillna('')
        
        # Limit rows for preview (first 100 rows)
        preview_df = df.head(100)
        
        # Convert to HTML table
        html_table = preview_df.to_html(
            classes='csv-preview-table',
            table_id='csvTable',
            escape=False,
            index=False
        )
        
        # Create full HTML page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Preview: {filename}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .header {{
                    background: white;
                    padding: 15px 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .header h2 {{
                    margin: 0;
                    color: #333;
                    font-size: 1.2em;
                }}
                .header-info {{
                    color: #666;
                    font-size: 0.9em;
                }}
                .download-btn {{
                    background: #667eea;
                    color: white;
                    padding: 8px 20px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-size: 0.9em;
                    transition: background 0.3s;
                }}
                .download-btn:hover {{
                    background: #5568d3;
                }}
                .container {{
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    overflow-x: auto;
                }}
                .csv-preview-table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 0.85em;
                }}
                .csv-preview-table th {{
                    background: #667eea;
                    color: white;
                    padding: 10px;
                    text-align: left;
                    font-weight: 600;
                    position: sticky;
                    top: 0;
                    z-index: 10;
                }}
                .csv-preview-table td {{
                    padding: 8px 10px;
                    border-bottom: 1px solid #e0e0e0;
                }}
                .csv-preview-table tr:hover {{
                    background: #f8f9ff;
                }}
                .csv-preview-table tr:nth-child(even) {{
                    background: #fafafa;
                }}
                .note {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 10px 15px;
                    margin-top: 15px;
                    border-radius: 4px;
                    font-size: 0.9em;
                    color: #856404;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div>
                    <h2>{filename}</h2>
                    <div class="header-info">
                        Showing {len(preview_df)} of {len(df)} rows, {len(df.columns)} columns
                    </div>
                </div>
                <a href="/download/{filename}" class="download-btn" download>Download CSV</a>
            </div>
            <div class="container">
                {html_table}
                {f'<div class="note">Note: Showing first 100 rows. Total rows: {len(df)}. Download the file to see all data.</div>' if len(df) > 100 else ''}
            </div>
        </body>
        </html>
        """
        
        return html_content
    except Exception as e:
        return jsonify({'error': f'Error reading CSV: {str(e)}'}), 500

if __name__ == '__main__':
    # Clean up on exit
    import atexit
    def cleanup():
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            shutil.rmtree(app.config['UPLOAD_FOLDER'])
    atexit.register(cleanup)
    
    # Use PORT environment variable (set by Render) or default to 5001 for local development
    port = int(os.environ.get('PORT', 5001))
    # Disable debug mode in production (Render sets environment variables)
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

