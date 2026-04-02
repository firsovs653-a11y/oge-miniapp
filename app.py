from flask import Flask, render_template, jsonify, request
import json
import subprocess
import tempfile
import os

app = Flask(__name__)

# Загрузка заданий
TASKS = {}
try:
    with open('tasks.json', 'r', encoding='utf-8') as f:
        TASKS = json.load(f)
    print(f"✅ Загружено заданий: {len(TASKS)}")
except Exception as e:
    print(f"❌ Ошибка загрузки tasks.json: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tasks')
def get_tasks():
    return jsonify(TASKS)

@app.route('/api/task/<task_id>')
def get_task(task_id):
    task = TASKS.get(task_id, {})
    return jsonify(task)

@app.route('/api/check', methods=['POST'])
def check_code():
    data = request.json
    code = data.get('code', '')
    task_id = data.get('task_id', '')
    
    task = TASKS.get(task_id, {})
    test_input = task.get('test_input', '')
    expected_output = task.get('expected_output', '')
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        process = subprocess.run(
            ['python3', temp_file],
            input=test_input,
            text=True,
            capture_output=True,
            timeout=5,
            encoding='utf-8'
        )
        
        os.unlink(temp_file)
        
        if process.returncode == 0:
            actual_output = process.stdout.strip()
            is_correct = (actual_output == expected_output.strip())
            return jsonify({
                'correct': is_correct,
                'output': actual_output,
                'expected': expected_output,
                'error': None
            })
        else:
            return jsonify({
                'correct': False,
                'output': None,
                'expected': expected_output,
                'error': process.stderr.strip()
            })
    except Exception as e:
        return jsonify({
            'correct': False,
            'output': None,
            'expected': expected_output,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
