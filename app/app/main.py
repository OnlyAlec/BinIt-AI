from flask import Flask, render_template, request, jsonify, Blueprint
from PIL import Image
import io
import os
import numpy as np
import cv2
import base64
from tensorflow.keras.models import load_model
import tensorflow as tf
from tensorflow.keras.applications.efficientnet import preprocess_input
from flask_cors import CORS
from voice import getNewLangAudio, get_supported_languages_map


app = Flask(__name__)
CORS(app)

# =====================================================================
# CONFIGURACIÓN GRAD-CAM
# =====================================================================
TARGET_SIZE = (255, 255)
LAST_CONV_LAYER = 'top_activation'
GAUSSIAN_KERNEL_SIZE = (3, 3)
GAUSSIAN_SIGMA = 0
ALPHA = 1
BETA = 0
THRESH_METHOD = 'otsu'
FIXED_THRESH = 127
MORPH_KERNEL_SIZE = (5, 5)
MORPH_OPERATION = cv2.MORPH_CLOSE
MARGIN = 10
BBOX_COLOR = (0, 255, 0)
BBOX_THICKNESS = 2
COLORMAP = cv2.COLORMAP_JET
# =====================================================================

# Cargar modelo
model = load_model('model.h5')
grad_model = tf.keras.models.Model(
    inputs=model.input,
    outputs=[model.get_layer(LAST_CONV_LAYER).output, model.output]
)

# Lista de clases
CLASS_NAMES = [
    'CARDBOARD',
    'GLASS',
    'METAL',
    'ORGANIC',
    'PAPER',
    'PEN',
    'PET',
    'PLASTIC_BAG',
    'UNICEL',
    'WRAPPER',
    'OTHER'
]


def make_gradcam_heatmap(img_array):
    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_array)
        pred_index = tf.argmax(predictions[0])
        class_channel = predictions[:, pred_index]

    grads = tape.gradient(class_channel, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    heatmap = tf.reduce_sum(tf.multiply(conv_outputs[0], pooled_grads), axis=-1)
    heatmap = tf.maximum(heatmap, 0)
    heatmap /= tf.reduce_max(heatmap)

    return heatmap.numpy(), pred_index.numpy()


def apply_gradcam(heatmap, original_img):
    # Procesamiento del heatmap
    heatmap = cv2.GaussianBlur(heatmap, GAUSSIAN_KERNEL_SIZE, GAUSSIAN_SIGMA)
    heatmap = cv2.resize(heatmap, (original_img.shape[1], original_img.shape[0]))
    heatmap_uint8 = np.uint8(255 * heatmap)

    # Crear superposición
    heatmap_color = cv2.applyColorMap(heatmap_uint8, COLORMAP)
    heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)
    superimposed_img = cv2.addWeighted(original_img, ALPHA, heatmap_color, BETA, 0)

    # Thresholding y bounding box
    if THRESH_METHOD == 'otsu':
        _, thresh = cv2.threshold(heatmap_uint8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        _, thresh = cv2.threshold(heatmap_uint8, FIXED_THRESH, 255, cv2.THRESH_BINARY)

    kernel = np.ones(MORPH_KERNEL_SIZE, np.uint8)
    thresh = cv2.morphologyEx(thresh, MORPH_OPERATION, kernel)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        x = max(0, x - MARGIN)
        y = max(0, y - MARGIN)
        w = min(original_img.shape[1] - x, w + 2*MARGIN)
        h = min(original_img.shape[0] - y, h + 2*MARGIN)

        cv2.rectangle(superimposed_img, (x, y), (x+w, y+h), BBOX_COLOR, BBOX_THICKNESS)

    return superimposed_img


# =====================================================================
# CONFIGURACIÓN DE BLUEPRINT CON PREFIJO
# =====================================================================

# Obtener el prefijo desde variable de entorno o usar por defecto
SUBPATH = os.environ.get('ULSA_SUBPATH', '/binit')

# Crear Blueprint con el prefijo
binit_bp = Blueprint('binit', __name__, url_prefix=SUBPATH)


@binit_bp.route('/')
def index():
    """Página principal de la aplicación BinIt"""
    return render_template('index.html')


@binit_bp.route('/health')
def health_check():
    """Endpoint de salud para monitoreo"""
    return jsonify({
        'status': 'healthy',
        'service': 'binit-ai',
        'endpoints': {
            'main': f'{SUBPATH}/',
            'predict': f'{SUBPATH}/predict',
            'save_image': f'{SUBPATH}/save_image',
            'health': f'{SUBPATH}/health'
        }
    })

@binit_bp.route('/lang', methods=['GET'])
def listLang():
    return jsonify(get_supported_languages_map())

@binit_bp.route('/voice', methods=['POST'])
def generate_voice():
    try:
        data = request.get_json()
        lang = data.get('lang', '')
        
        if not lang:
            app.logger.error('No se especificó el idioma')
            return jsonify({'error': 'No se especificó el idioma'}), 400
        
        # Usar la nueva función para generar todos los audios
        from voice import generate_all_audios_for_language
        result = generate_all_audios_for_language(lang, app.logger)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': f'Audios generados exitosamente para {lang}',
                'generated_files': result['generated_files'],
                'total_generated': result['total_generated'],
                'errors': result['errors']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Error desconocido'),
                'errors': result.get('errors', [])
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error en /voice: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@binit_bp.route('/predict', methods=['POST'])
def predict():
    try:
        # Breakpoint para debugging - puedes poner aquí un punto de interrupción
        print("🔍 DEBUG: Iniciando predicción...")
        
        # Procesar imagen
        pil_image = Image.open(io.BytesIO(request.data)).convert('RGB')
        pil_image = pil_image.resize(TARGET_SIZE)
        original_img = np.array(pil_image)

        # Preprocesar para modelo
        x = preprocess_input(original_img.copy())
        x = np.expand_dims(x, axis=0)

        # Predicción
        y = model.predict(x)[0]
        idx = np.argmax(y)
        confidence = float(y[idx])

        # Breakpoint para debugging - aquí puedes ver la predicción
        print(f"🔍 DEBUG: Predicción - idx: {idx}, confidence: {confidence}")

        if confidence <= 0.5:
            class_name = 'OTHER'
        else:
            class_name = CLASS_NAMES[idx]

        # Generar Grad-CAM
        heatmap, _ = make_gradcam_heatmap(x)
        grad_img = apply_gradcam(heatmap, original_img)

        # Convertir a base64
        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(grad_img, cv2.COLOR_RGB2BGR))
        img_str = base64.b64encode(buffer).decode('utf-8')

        result = {
            'label': class_name,
            'confidence': round(confidence * 100, 2),
            'gradcam': img_str
        }
        
        print(f"🔍 DEBUG: Resultado final - {result['label']} con {result['confidence']}% confianza")
        
        return jsonify(result)

    except Exception as e:
        print(f"⁉️ Error: {str(e)}")
        app.logger.error(f"Error en /predict: {str(e)}")
        return jsonify({'error': str(e)}), 500


@binit_bp.route('/save_image', methods=['POST'])
def save_image():
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No se recibió imagen'}), 400

        # Obtener imagen y clase
        image_file = request.files['image']
        correct_class = request.form.get('correct_class').upper()

        print(f"Clase recibida: {correct_class}")

        # Validar clase
        if correct_class not in CLASS_NAMES:
            return jsonify({'success': False, 'error': f'Clase no válida: {correct_class}'}), 400

        dir_name = correct_class
        save_dir = os.path.join('training_data', dir_name)
        os.makedirs(save_dir, exist_ok=True)

        # Encontrar siguiente número incremental
        max_num = 0
        existing_files = os.listdir(save_dir)
        for f in existing_files:
            if f.startswith(f"{correct_class}_") and f.endswith('.jpg'):
                try:
                    num = int(f.split('_')[1].split('.')[0])
                    if num > max_num:
                        max_num = num
                except:
                    pass
        next_num = max_num + 1

        # Guardar imagen
        filename = f"{correct_class}_{next_num}.jpg"
        image_path = os.path.join(save_dir, filename)
        image = Image.open(image_file)
        print(image_file)
        image_file
        image.save(image_path)

        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error en /save_image: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================================================
# RUTA DE ESTADO EN LA RAÍZ (para healthcheck de Docker)
# =====================================================================
@app.route('/')
def root_health():
    """Endpoint de salud en la raíz para healthcheck de Docker"""
    return jsonify({
        'status': 'healthy',
        'service': 'binit-ai-container'
    })


# Registrar el blueprint
app.register_blueprint(binit_bp)
