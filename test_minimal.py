from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return f"Hello from Railway! Port: {os.getenv('PORT', 'not set')}"

@app.route('/health')
def health():
    return {"status": "healthy", "port": os.getenv('PORT', 'not set')}

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
