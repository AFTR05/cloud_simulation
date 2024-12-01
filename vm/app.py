from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__)

# Directorio de almacenamiento
STORAGE_DIR = "/storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    file.save(os.path.join(STORAGE_DIR, file.filename))
    return jsonify({"message": "File uploaded successfully"}), 201

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(STORAGE_DIR, filename)

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    file_path = os.path.join(STORAGE_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": "File deleted successfully"}), 200
    return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)