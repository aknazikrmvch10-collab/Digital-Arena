import subprocess
import time
import requests
import os
import signal
import sys
import re

def kill_process(name):
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/IM', name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        else:
            subprocess.run(['pkill', '-f', name])
    except:
        pass

def update_env_file(key, value):
    """Updates or adds a key-value pair in the .env file."""
    env_path = '.env'
    if not os.path.exists(env_path):
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(f"{key}={value}\n")
        return

    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        # Ensure newline before appending if needed
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
        new_lines.append(f"{key}={value}\n")

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def main():
    print("Stopping old processes...")
    kill_process("ngrok.exe")
    # kill_process("python.exe") 
    
    print("Starting ngrok...")
    # Start ngrok in background
    ngrok_process = subprocess.Popen(['ngrok', 'http', '8000'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    print("Waiting for ngrok tunnel...")
    public_url = None
    for i in range(10):
        time.sleep(2)
        try:
            response = requests.get('http://127.0.0.1:4040/api/tunnels')
            data = response.json()
            if data['tunnels']:
                public_url = data['tunnels'][0]['public_url']
                break
        except:
            print(f"   ... waiting ({i+1}/10)")
            
    if not public_url:
        print("Failed to get ngrok URL. Is ngrok running?")
        ngrok_process.kill()
        return

    print(f"Tunnel active: {public_url}")

    # Update .env instead of config.py
    print("Updating .env...")
    update_env_file("BASE_URL", public_url)
        
    print("Starting Bot...")
    # Start bot
    bot_process = subprocess.Popen(['python', 'main.py'])
    
    print("\n" + "="*50)
    print(f"   BOT IS RUNNING! ")
    print(f"   Mini App URL: {public_url}/miniapp/index.html")
    print("="*50 + "\n")
    
    try:
        bot_process.wait()
    except KeyboardInterrupt:
        print("🛑 Stopping...")
        ngrok_process.kill()
        bot_process.kill()

if __name__ == "__main__":
    main()
