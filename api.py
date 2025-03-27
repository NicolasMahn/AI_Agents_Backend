import threading
import time

from flask import Flask, jsonify, request

import agent_manager
import agent_objs
from util import decode_url_str
import atexit
app = Flask(__name__)

@app.route('/get_agents', methods=['GET'])
def get_agents():
    agents = agent_manager.get_agents()
    return jsonify(agents)


@app.route('/<url_agent_name>/reset_agent', methods=['DELETE'])
def reset_agent(url_agent_name):
    agent_name = decode_url_str(url_agent_name)
    agent = agent_manager.get_agent(agent_name)
    if agent:
        agent.reset()
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
    return jsonify({'message': 'File uploaded'})

@app.route('/<url_agent_name>/add_message', methods=['PUT'])
def add_message(url_agent_name):
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid input'}), 400
    try:
        agent_name = decode_url_str(url_agent_name)
        agent = agent_manager.get_agent(agent_name)
        if agent:
            agent.add_message("User", data['text'])
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

@app.route('/<url_agent_name>/does_agent_code', methods=['GET'])
def does_agent_code(url_agent_name):
    agent = decode_url_str(url_agent_name)
    agent = agent_manager.get_agent(agent)
    return jsonify(agent.does_agent_code())


if __name__ == '__main__':
    app.run(debug=True)