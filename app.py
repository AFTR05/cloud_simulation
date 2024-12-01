from flask import Flask, jsonify, request
from flask_cors import CORS
import docker
import os
import random

app = Flask(__name__)
CORS(app)

# Cliente Docker
client = docker.from_env()

# Ruta base para almacenamiento de volúmenes
BASE_STORAGE_PATH = "web/storage"

# Configuración base
DEFAULT_CONFIG = {
    "context": "./vm",  # Directorio de construcción
    "volume_mount": "/storage",  # Ruta dentro del contenedor
}

# Control de puertos asignados
used_ports = set()

# Nombre del grupo
GROUP_NAME = "grupo_vms"


def generar_nombre_contenedor():
    """
    Generar un nombre único para el contenedor.
    """
    return f"{GROUP_NAME}_vm{random.randint(1, 1000)}"


def generar_puerto_libre(base=5000):
    """
    Generar un puerto libre para el contenedor.
    """
    while True:
        puerto = base + random.randint(1, 1000)
        if puerto not in used_ports:
            used_ports.add(puerto)
            return puerto


def crear_contenedor():
    """
    Crear y ejecutar un contenedor con configuración automática y agrupado por nombre.
    """
    try:
        # Generar nombre y puerto dinámicos
        nombre = generar_nombre_contenedor()
        puerto_host = generar_puerto_libre()
        puerto_contenedor = 5000
        image_name = f"{nombre}_image"
        context_path = os.path.abspath(DEFAULT_CONFIG["context"])  # Usar ruta absoluta

        # Verificar si la imagen ya existe
        if image_name not in [img.tags[0] if img.tags else None for img in client.images.list()]:
            # Construir la imagen
            client.images.build(path=context_path, tag=image_name)

        # Crear volumen en la máquina host con una ruta absoluta
        volumen_host = os.path.join(os.path.abspath(BASE_STORAGE_PATH), nombre).replace("\\", "/")
        os.makedirs(volumen_host, exist_ok=True)

        # Crear el contenedor
        container = client.containers.run(
            image=image_name,
            name=nombre,
            detach=True,
            ports={f"{puerto_contenedor}/tcp": puerto_host},
            volumes={volumen_host: {"bind": DEFAULT_CONFIG["volume_mount"], "mode": "rw"}},
        )

        return f"Contenedor '{nombre}' creado y ejecutándose en el puerto {puerto_host} con volumen '{volumen_host}'."
    except Exception as e:
        return f"Error al crear o ejecutar el contenedor: {str(e)}"


@app.route('/crear', methods=['POST'])
def crear():
    """
    Ruta para crear y ejecutar un contenedor automáticamente.
    """
    mensaje = crear_contenedor()
    return jsonify({"message": mensaje})

@app.route('/subir-archivo', methods=['POST'])
def subir_archivo():
    """
    Ruta para subir un archivo al contenedor.
    """
    archivo = request.files.get('archivo')  # Obtener el archivo de la solicitud
    if archivo:
        print(f"Archivo recibido: {archivo.filename}")  # Agregar log para depuración
        # Crear el directorio para almacenar los archivos en el host
        volumen_host = os.path.join(os.path.abspath(BASE_STORAGE_PATH), "uploaded_files")
        os.makedirs(volumen_host, exist_ok=True)

        # Ruta final donde se guardará el archivo en el host
        archivo_path = os.path.join(volumen_host, archivo.filename)

        try:
            # Guardar el archivo en el host
            archivo.save(archivo_path)

            # Devolver respuesta de éxito
            return jsonify({"message": f"Archivo '{archivo.filename}' subido exitosamente."}), 200
        except Exception as e:
            # En caso de error, devolver un mensaje de error
            return jsonify({"error": f"Error al guardar el archivo: {str(e)}"}), 500
    else:
        # Si no se envió un archivo, devolver un error
        return jsonify({"error": "No se ha proporcionado un archivo."}), 400





@app.route('/contenedores', methods=['GET'])
def listar_contenedores():
    """
    Listar todos los contenedores activos y su configuración, agrupados por nombre.
    """
    containers = client.containers.list(all=True)
    container_list = [
        {
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "ports": c.ports,
        }
        for c in containers if GROUP_NAME in c.name  # Filtrar por el prefijo del grupo
    ]
    return jsonify(container_list), 200


@app.route('/contenedores/<string:nombre>', methods=['DELETE'])
def eliminar_contenedor(nombre):
    """
    Eliminar un contenedor por su nombre y limpiar su volumen.
    """
    try:
        container = client.containers.get(nombre)
        container.remove(force=True)

        # Eliminar el volumen asociado
        volumen_host = os.path.join(BASE_STORAGE_PATH, nombre)
        if os.path.exists(volumen_host):
            os.rmdir(volumen_host)  # Asegúrate de que esté vacío

        return jsonify({"message": f"Contenedor '{nombre}' eliminado con éxito"}), 200
    except docker.errors.NotFound:
        return jsonify({"error": f"Contenedor '{nombre}' no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": f"Error al eliminar el contenedor: {str(e)}"}), 500


if __name__ == '__main__':
    # Crear el directorio base para volúmenes si no existe
    os.makedirs(BASE_STORAGE_PATH, exist_ok=True)
    app.run(debug=True)
