import os
import sys


PROJECT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RML")
sys.path.insert(0, PROJECT_DIR)

from app import app


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
