import subprocess
import sys
import time
def start_tunnel():
    print("==================================================")
    print("  LinkPulse Public Tunnel (localtunnel)")
    print("  Public URL: https://linkpulse-demo.loca.lt")
    print("==================================================")
    cmd = ['npx.cmd', 'localtunnel', '--port', '5000', '--subdomain', 'linkpulse-demo']
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(proc.stdout.readline, ''):
            print(line, end='', flush=True)
    except KeyboardInterrupt:
        print("\nStopping tunnel.")
    except Exception as e:
        print(f"Tunnel error: {e}")

if __name__ == '__main__':
    start_tunnel()
