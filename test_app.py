#!/usr/bin/env python3
"""
Minimal test app to debug Railway deployment issues
"""

import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello from Railway!"

@app.route('/health')
def health():
    return {"status": "healthy", "port": os.getenv('PORT', '5001')}

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(debug=False, port=port, host='0.0.0.0')