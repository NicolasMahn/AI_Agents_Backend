import datetime
import os
import threading
from flask_socketio import SocketIO
from flask import Flask, jsonify, request, send_file

import agent_manager
from agent_objs import chat, code_manager
from agent_systems import base_agent_system, llm_wrapper_system
from util import decode_url_str
app = Flask(__name__)

async_mode = os.getenv("ASYNC_MODE",'eventlet')  # Use eventlet for async mode only when deployed add env variable with "threading" as value in IDE

socketio = SocketIO(app, logger=True, engineio_logger=True,
                    async_mode=async_mode,
                    cors_allowed_origins="*") # Initialize SocketIO with Flask

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    send_message("Backend is live!")

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

def send_message(message, event="message"):
    try:
        socketio.emit(event, message + " - " + str(datetime.datetime.now().timestamp()), namespace='/')
    except Exception as e:
        print(f"Error emitting SocketIO message: {e}")

@app.route('/get_agents', methods=['GET'])
def get_agents():
    agents = agent_manager.get_agents()
    return jsonify(agents)

@app.route('/get_agent_description/<url_agent_name>', methods=['GET'])
def get_agent_description(url_agent_name):
    agent_name = decode_url_str(url_agent_name)
    description = agent_manager.get_agent_description(agent_name)
    if description:
        return jsonify(description)
    else:
        return jsonify({'error': f'Agent `{agent_name}` not found'}), 404

@app.route('/<url_agent_name>/reset_agent', methods=['DELETE'])
def reset_agent(url_agent_name):
    agent_name = decode_url_str(url_agent_name)
    success = agent_manager.agent_reset(agent_name)
    if success:
        return jsonify({'message': f'`{agent_name}` was reset successfully'})
    else:
        return jsonify({'message': f'`{agent_name}` not found'}), 404

@app.route('/<url_agent_name>/upload_file', methods=['POST'])
def upload_file(url_agent_name):
    agent_name = decode_url_str(url_agent_name)
    agent = agent_manager.get_agent(agent_name)
    upload_contents = request.get_json()
    filename = upload_contents['filename']
    agent.upload_file(upload_contents['contents'], filename)

    if filename in os.listdir(os.path.join(agent.agent_system_dir, 'uploads')):
        return jsonify({'message': 'File uploaded'})
    else:
        return jsonify({'error': 'File upload failed'}), 500

@app.route('/<url_agent_name>/add_message', methods=['PUT'])
def add_message(url_agent_name):
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input'}), 400
    try:
        agent_name = decode_url_str(url_agent_name)
        agent = agent_manager.get_agent(agent_name)
        if agent:
            threading.Thread(target=agent.add_message, args=('User', data['text'])).start()
        else:
            return jsonify({'error': f'Agent `{agent_name}` not found'}), 404
    except KeyError as e:
        return jsonify({'error': f'Missing key: {e}'}), 400
    return jsonify({'message': 'Message added'})

@app.route('/<url_agent_name>/get_chat_history/<url_chat_name>', methods=['GET'])
def get_chat_history(url_agent_name, url_chat_name):
    agent_name = decode_url_str(url_agent_name)
    chat_name = decode_url_str(url_chat_name)
    agent = agent_manager.get_agent(agent_name)
    if agent:
        chat = agent.get_chat(chat_name)
        if chat:
            return jsonify(chat)
        elif isinstance(chat, object):
            return jsonify({'warning': f'Chat `{chat_name}` is empty'}), 200
        else:
            return jsonify({'error': f'Chat `{chat_name}` not found'}), 404
    else:
        return jsonify({'error': f'Agent `{agent_name}` not found'}), 404

@app.route('/<url_agent_name>/get_chats', methods=['GET'])
def get_chats(url_agent_name):
    agent = decode_url_str(url_agent_name)
    agent = agent_manager.get_agent(agent)
    return jsonify(agent.get_chats())

@app.route('/<url_agent_name>/get_dashboard', methods=['GET'])
def get_dashboard(url_agent_name):
    agent = decode_url_str(url_agent_name)
    agent = agent_manager.get_agent(agent)
    code_obj = agent.get_frontend_code()
    if code_obj:
        return jsonify(code_obj.get_execution_code())
    return jsonify({'error': 'No frontend code found'}), 404

@app.route('/<url_agent_name>/get_code/<url_code_name>', methods=['GET'])
def get_code(url_agent_name, url_code_name):
    agent = decode_url_str(url_agent_name)
    agent = agent_manager.get_agent(agent)
    if agent:
        if 0 == len(agent.get_code_names()):
            return jsonify({'error': 'No code found'}), 404
        try:
            code_name = agent.get_code_names()[-1] if not url_code_name or decode_url_str(
                url_code_name) not in agent.get_code_names() else decode_url_str(url_code_name)
            return jsonify(agent.get_code_api(code_name))
        except KeyError:
            return jsonify({'error': f'Code `{url_code_name}` not found'}), 404
    else:
        return jsonify({'error': f'Agent `{agent}` not found'}), 404

@app.route('/<url_agent_name>/get_code_names', methods=['GET'])
def get_code_names(url_agent_name):
    agent = decode_url_str(url_agent_name)
    agent = agent_manager.get_agent(agent)
    return jsonify(agent.get_code_names())

@app.route('/get_available_models', methods=['GET'])
def get_available_models():
    return agent_manager.get_available_models()

@app.route('/set_model/<model>', methods=['POST'])
def set_model(model):
    if agent_manager.set_model(model):
        print(f'Set Model to `{model}`')
        send_message(f'Model is set.', "model_switch")
        return jsonify({'message': f'Model set to `{model}`'})
    else:
        print(f'Model `{model}` not available')
        send_message("Failed to set model.", "model_switch")
        return jsonify({'error': f'Model `{model}` not available'}), 404

@app.route('/get_model', methods=['GET'])
def get_model():
    return jsonify(agent_manager.get_model())

@app.route('/get_top_k', methods=['GET'])
def get_top_k():
    return jsonify(agent_manager.get_top_k())

@app.route('/set_top_k/<int:k>', methods=['POST'])
def set_top_k(k):
    if agent_manager.set_top_k(k):
        print(f'Set Top K to `{k}`')
        send_message(f'Top K is set.', "top_k_switch")
        return jsonify({'message': f'Top K set to `{k}`'})
    else:
        print(f'Invalid Top K value `{k}`')
        send_message("Failed to set Top K.", "top_k_switch")
        return jsonify({'error': f'Invalid Top K value `{k}`'}), 400

@app.route('/get_long_memory_display', methods=['GET'])
def get_long_memory_display():
    return jsonify(agent_manager.get_long_memory_display())

@app.route('/set_long_memory_display/<long_memory_display>', methods=['POST'])
def set_long_memory_display(long_memory_display):
    if long_memory_display in ['True', 'False']:
        agent_manager.set_long_memory_display(long_memory_display)
        print(f'Set Long Memory Display to `{long_memory_display}`')
        send_message(f'Long Memory Display is set.', "long_memory_switch")
        return jsonify({'message': f'Long Memory Display set to `{long_memory_display}`'})
    else:
        print(f'Invalid Long Memory Display value `{long_memory_display}`')
        send_message("Failed to set Long Memory Display.", "long_memory_switch")
        return jsonify({'error': f'Invalid Long Memory Display value `{long_memory_display}`'}), 400

@app.route('/get_file/<path:file_path>', methods=['GET'])
def get_file(file_path):
    try:
        if os.path.exists(file_path):
            return send_file(file_path)
        else:
            return jsonify({'error': f'File `{file_path}` not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

chat.register_message_callback(send_message)
code_manager.register_message_callback(send_message)
base_agent_system.register_message_callback(send_message)
llm_wrapper_system.register_message_callback(send_message)

if __name__ == '__main__':
    app.run(debug=False)