from flask import Flask, render_template, request, jsonify
import subprocess
import tempfile
import os

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/check_code', methods=['POST'])
def check_code():
    data = request.json
    code = data.get('code', '')
    test_input = data.get('test_input', '')
    expected_output = data.get('expected_output', '')

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
            if actual_output == expected_output.strip():
                return jsonify({'success': True, 'output': actual_output, 'message': '✅ Правильно!'})
            else:
                return jsonify({'success': False, 'output': actual_output,
                                'message': f'❌ Неправильно. Ожидалось: {expected_output}'})
        else:
            return jsonify({'success': False, 'output': process.stderr, 'message': 'Ошибка выполнения'})

    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': '', 'message': '⏰ Превышено время выполнения'})
    except Exception as e:
        return jsonify({'success': False, 'output': '', 'message': f'Ошибка: {str(e)}'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)