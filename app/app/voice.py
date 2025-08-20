import os
import logging
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from flask import jsonify

# Apply fugashi patch before importing Coqui TTS
try:
    from fugashi_patch import apply_fugashi_patch
    apply_fugashi_patch()
except ImportError:
    pass  # Patch file not found, continue without patch

load_dotenv()
COQUI_TTS_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
# Base path para archivos de voz de referencia en español
VOICE_REFERENCE_BASE_PATH = "static/audios/es/"
OUTPATH_FILE_START = "static/audios/"

class ITranslator(ABC):
    @abstractmethod
    def translate(self, text: str, targetLangCode: str, sourceLangCode: str = "es") -> str | None:
        """Traduce texto de un idioma fuente a un idioma destino."""
        pass

class ITextToSpeech(ABC):
    @abstractmethod
    def synthesize(self, text: str, langCode: str, refAudioPath: str, outputPath: str) -> bool:
        """Sintetiza texto a audio usando una voz de referencia."""
        pass

class DeepLTranslationService(ITranslator):
    """
    Servicio de traducción que utiliza la API de DeepL.
    """
    def __init__(self, apiKey: str):
        if not apiKey:
            raise ValueError("Missing API KEY!")
        self.apiKey = apiKey
        try:
            from deep_translator import DeeplTranslator as DeepLTranslatorLib
            self._translatorLib = DeepLTranslatorLib
        except ImportError:
            logging.error("Missing dependency 'deep-translator'!")
            raise

    def translate(self, text: str, targetLangCode: str, sourceLangCode: str = "es") -> str | None:
        """
        Traduce el texto al idioma de destino.
        DeepL usa códigos de idioma como 'EN-US', 'EN-GB', 'ES', 'FR', 'ZH'.
        Coqui TTS (xtts_v2) usa códigos de 2 letras como 'en', 'es', 'fr', 'zh-cn'.
        """
        logging.info(f"Traduciendo -> '{targetLangCode}'...")
        try:
            deeplCode = targetLangCode.lower()
            if deeplCode == "zh-cn":
                deeplCode = "zh"
            elif len(deeplCode) == 2 and deeplCode != "PT": 
                 pass

            translator = self._translatorLib(api_key=self.apiKey,
                                              target=deeplCode,
                                              source=sourceLangCode.lower())
            translatedTxt = translator.translate(text)
            if translatedTxt:
                logging.info(f"Traduciendo OK -> {translatedTxt}")
                return translatedTxt
            else:
                logging.warning("Traduciendo ERR -> Vacio")
                return None
        except Exception as e:
            logging.error(f"Error durante la traducción con DeepL: {e}")
            return None

class CoquiTextToSpeechService(ITextToSpeech):
    """
    Servicio de síntesis de voz que utiliza Coqui TTS.
    Cumple con SRP: su única responsabilidad es generar audio a partir de texto.
    """
    def __init__(self, modelName: str = COQUI_TTS_MODEL_NAME):
        self.modelName = modelName
        self.ttsInstance = None
        # Intentar importar 'TTS' aquí.
        try:
            from TTS.api import TTS as CoquiTTSLib
            self._coquiTtsLib = CoquiTTSLib
        except ImportError:
            logging.error("Missing dependency 'TTS'! ")
            raise
        self._initializeTts()

    def _initializeTts(self):
        """Inicializa la instancia de Coqui TTS."""
        try:
            logging.info(f"Coqui TTS: {self.modelName}...")
            self.ttsInstance = self._coquiTtsLib(model_name=self.modelName, progress_bar=True, gpu=False)
            logging.info("Coqui TTS OK!")
        except Exception as e:
            logging.error(f"No se pudo cargar el modelo Coqui TTS ({self.modelName}): {e}")
            self.ttsInstance = None


    def synthesize(self, text: str, langCode: str, refAudioPath: str, outputPath: str) -> bool:
        """
        Genera un archivo de audio a partir del texto usando una voz de referencia.
        langCode debe ser el código que Coqui TTS entiende (ej. 'en', 'es', 'fr', 'zh-cn').
        """
        if not self.ttsInstance:
            logging.error("Synthesize -> Missing model TTS")
            return False

        logging.info(f"Synthesize -> Audio en '{langCode}'...")
        logging.info(f"Synthesize -> Texto: {text[:100]}...")
        logging.info(f"Synthesize -> Referencia: {refAudioPath}")
        logging.info(f"Synthesize -> Output: {outputPath}")

        if not os.path.exists(refAudioPath):
            logging.error(f"El archivo de voz de referencia no se encuentra en: {refAudioPath}")
            return False

        try:
            self.ttsInstance.tts_to_file(
                text=text,
                speaker_wav=refAudioPath,
                language=langCode,
                file_path=outputPath
            )
            logging.info(f"Synthesize OK -> {outputPath}")
            return True
        except Exception as e:
            logging.error(f"No se pudo generar el audio con Coqui TTS: {e}")
            return False

def get_voice_reference_for_audio(audio_filename: str) -> str:
    """
    Selecciona dinámicamente la voz de referencia más apropiada 
    según el tipo de audio que se está generando.
    
    Args:
        audio_filename: Nombre del archivo de audio a generar (ej: "Bienvenida.mp3")
    
    Returns:
        Ruta al archivo de voz de referencia más apropiado
    """
    # Mapeo de tipos de audio a voces de referencia específicas
    voice_mapping = {
        # Mensajes de bienvenida e instrucciones - usar voz más cálida y amigable
        'Bienvenida.mp3': 'Bienvenida.mp3',
        'Instrucciones.mp3': 'Instrucciones.mp3',
        
        # Mensajes de proceso - usar voz más neutral y clara
        'Procesando.mp3': 'Procesando.mp3',
        'Bingo.mp3': 'Bingo.mp3',
        'Selecciona-una-opcion.mp3': 'Selecciona-una-opcion.mp3',
        
        # Comandos y direcciones - usar voz directiva
        'Deposita-en.mp3': 'Deposita-en.mp3',
        'Residuo.mp3': 'Residuo.mp3',
        
        # Clasificaciones de materiales - usar voces específicas del material cuando estén disponibles
        'Carton.mp3': 'Carton.mp3',
        'Vidrio.mp3': 'Vidrio.mp3',
        'Metal.mp3': 'Metal.mp3',
        'Papel.mp3': 'Papel.mp3',
        'Unicel.mp3': 'Unicel.mp3',
        'Botella-de-plastico.mp3': 'Botella-de-plastico.mp3',
        'Bolsa-de-Plastico.mp3': 'Bolsa-de-Plastico.mp3',
        'Organica.mp3': 'Organica.mp3',
        'Para-escritura.mp3': 'Para-escritura.mp3',
        'Envoltorio.mp3': 'Envoltorio.mp3',
        'Otro.mp3': 'Otro.mp3'
    }
    
    # Lista de archivos de referencia disponibles en orden de preferencia
    fallback_references = [
        'Bienvenida.mp3',  # Voz más cálida para fallback general
        'Instrucciones.mp3',  # Voz clara para explicaciones
        'Procesando.mp3',  # Voz neutral
        'Residuo.mp3',  # Voz simple y directa
        'Carton.mp3'  # Última opción
    ]
    
    # Intentar usar la voz específica para este audio
    preferred_reference = voice_mapping.get(audio_filename)
    if preferred_reference:
        preferred_path = os.path.join(VOICE_REFERENCE_BASE_PATH, preferred_reference)
        if os.path.exists(preferred_path):
            return preferred_path
    
    # Si no está disponible la voz específica, buscar fallbacks
    for fallback in fallback_references:
        fallback_path = os.path.join(VOICE_REFERENCE_BASE_PATH, fallback)
        if os.path.exists(fallback_path):
            return fallback_path
    
    # Si ninguno está disponible, buscar cualquier archivo .mp3 en la carpeta
    if os.path.exists(VOICE_REFERENCE_BASE_PATH):
        for file in os.listdir(VOICE_REFERENCE_BASE_PATH):
            if file.endswith('.mp3'):
                return os.path.join(VOICE_REFERENCE_BASE_PATH, file)
    
    # Como último recurso, devolver la ruta del archivo original (aunque no exista)
    return os.path.join(VOICE_REFERENCE_BASE_PATH, 'Bienvenida.mp3')

def get_supported_languages_map() -> dict:
    """
    Devuelve un mapeo de nombres de idioma legibles a códigos de idioma
    que Coqui TTS (xtts_v2) suele entender.
    También incluye los códigos que DeepL podría necesitar si son diferentes.
    Formato: "Nombre Idioma": {
        "coqui_code": "xx", 
        "deepl_code": "XX" o "XX-YY",
        "country_code": "XX"
    }
    """
    return {
        "Búlgaro":      {
            "coqui_code": "bg", 
            "deepl_code": "BG",
            "country_code": "BG"
        },
        "Checo":        {
            "coqui_code": "cs", 
            "deepl_code": "CS",
            "country_code": "CZ"
        },
        "Danés":        {
            "coqui_code": "da", 
            "deepl_code": "DA",
            "country_code": "DK"
        },
        "Alemán":       {
            "coqui_code": "de", 
            "deepl_code": "DE",
            "country_code": "DE"
        },
        "Griego":       {
            "coqui_code": "el", 
            "deepl_code": "EL",
            "country_code": "GR"
        },
        "Inglés":       {
            "coqui_code": "en", 
            "deepl_code": "EN",
            "country_code": "US"
        },
        "Español":      {
            "coqui_code": "es", 
            "deepl_code": "ES",
            "country_code": "ES"
        },
        "Estonio":      {
            "coqui_code": "et", 
            "deepl_code": "ET",
            "country_code": "EE"
        },
        "Finlandés":    {
            "coqui_code": "fi", 
            "deepl_code": "FI",
            "country_code": "FI"
        },
        "Francés":      {
            "coqui_code": "fr", 
            "deepl_code": "FR",
            "country_code": "FR"
        },
        "Húngaro":      {
            "coqui_code": "hu", 
            "deepl_code": "HU",
            "country_code": "HU"
        },
        "Indonesio":    {
            "coqui_code": "id", 
            "deepl_code": "ID",
            "country_code": "ID"
        },
        "Italiano":     {
            "coqui_code": "it", 
            "deepl_code": "IT",
            "country_code": "IT"
        },
        "Japonés":      {
            "coqui_code": "ja", 
            "deepl_code": "JA",
            "country_code": "JP"
        },
        "Lituano":      {
            "coqui_code": "lt", 
            "deepl_code": "LT",
            "country_code": "LT"
        },
        "Letón":        {
            "coqui_code": "lv", 
            "deepl_code": "LV",
            "country_code": "LV"
        },
        "Neerlandés":   {
            "coqui_code": "nl", 
            "deepl_code": "NL",
            "country_code": "NL"
        },
        "Polaco":       {
            "coqui_code": "pl", 
            "deepl_code": "PL",
            "country_code": "PL"
        },
        "Portugués":    {
            "coqui_code": "pt", 
            "deepl_code": "PT",
            "country_code": "PT"
        },
        "Rumano":       {
            "coqui_code": "ro", 
            "deepl_code": "RO",
            "country_code": "RO"
        },
        "Ruso":         {
            "coqui_code": "ru", 
            "deepl_code": "RU",
            "country_code": "RU"
        },
        "Eslovaco":     {
            "coqui_code": "sk", 
            "deepl_code": "SK",
            "country_code": "SK"
        },
        "Esloveno":     {
            "coqui_code": "sl", 
            "deepl_code": "SL",
            "country_code": "SI"
        },
        "Sueco":        {
            "coqui_code": "sv", 
            "deepl_code": "SV",
            "country_code": "SE"
        },
        "Turco":        {
            "coqui_code": "tr", 
            "deepl_code": "TR",
            "country_code": "TR"
        },
        "Ucraniano":    {
            "coqui_code": "uk", 
            "deepl_code": "UK",
            "country_code": "UA"
        },
        "Chino":        {
            "coqui_code": "zh", 
            "deepl_code": "ZH",
            "country_code": "CN"
        }
    }

# --- Orquestador del Proceso (Lógica Principal) ---

class AudioController:
    """
    Orquesta el proceso de traducción y síntesis de voz.
    Depende de las abstracciones ITranslator e ITextToSpeech (Principio de Inversión de Dependencias).
    """
    def __init__(self, translator: ITranslator, tts_service: ITextToSpeech):
        self.translator = translator
        self.tts_service = tts_service

    def process(self, textToTranslate: str, targetLangName: str,
                refVoicePath: str, outputBase: str = "audio_generado") -> bool:
        """
        Ejecuta el flujo completo: obtener códigos, traducir, sintetizar.
        """
        langMap = get_supported_languages_map()
        if targetLangName not in langMap:
            logging.error(f"Idioma '{targetLangName}' no soportado o no definido en el mapeo.")
            return False

        codes = langMap[targetLangName]
        coquiCode = codes["coqui_code"]
        deeplCode = codes["deepl_code"]

        # 1. Traducir texto
        translatedText = self.translator.translate(textToTranslate, deeplCode)

        if not translatedText:
            logging.error("Fallo en la traducción. No se procederá con la síntesis de voz.")
            return False

        # 2. Generar audio
        # Limpiar el nombre del idioma para el nombre del archivo
        safeLangName = "".join(c if c.isalnum() else "_" for c in targetLangName.lower())
        outputPath = f"{outputBase}_{safeLangName}.wav"

        success = self.tts_service.synthesize(
            translatedText,
            coquiCode,
            refVoicePath,
            outputPath
        )

        if success:
            logging.info(f"Proceso completado. Audio guardado como {outputPath}")
        else:
            logging.error("Fallo al generar el audio.")
        return success

def getNewLangAudio(text, lang, logger=None):
    if logger is None:
        logger = logging.getLogger(__name__)
        
    if not text:
        logger.error('No se ingresó texto para traducir')
        return jsonify({'error': 'No se ingresó texto para traducir'}), 400

    if not lang:
        logger.error('No se ingreso el idioma de traduccion')
        return jsonify({'error': 'No se ingreso el idioma de traduccion'}), 400

    if not lang in list(get_supported_languages_map().keys()):
        logger.error('Idioma no soportado')
        return jsonify({'error': 'Idioma no soportado'}), 400

    # Usar la nueva función para obtener voz de referencia dinámica
    filename = text.split()[0] if text.strip() else "audio"
    voice_reference = get_voice_reference_for_audio(f"{filename}.mp3")
    
    if not os.path.exists(voice_reference):
        logger.error(f"Archivo de referencia '{voice_reference}' no encontrado")
        return jsonify({'error': 'Referencia no encontrada'}), 500
    
    if not (voice_reference.lower().endswith(".wav") or voice_reference.lower().endswith(".mp3")):
        logger.warning("El archivo de referencia no parece ser WAV o MP3. Coqui TTS podría no procesarlo correctamente.")

    filenameOutput = f"{OUTPATH_FILE_START}{lang}/{filename}"

    try:
        translator = DeepLTranslationService(apiKey=os.getenv("DEEPL_API_KEY"))
        tts_synthesizer = CoquiTextToSpeechService(modelName=COQUI_TTS_MODEL_NAME)
    except Exception as e:
        logger.error(f"Servicios: {e}")
        return jsonify({'error': 'Error al inicializar los servicios'}), 500

    orchestrator = AudioController(translator, tts_synthesizer)
    text = text.strip()   

    logger.info("--- Iniciando proceso de traducción y síntesis ---")
    logger.info(f"Usando voz de referencia: {voice_reference}")
    orchestrator.process(
        text,
        lang,
        voice_reference,
        filenameOutput
    )
    logger.info("--- Proceso finalizado ---")

def get_audio_text_mapping():
    """
    Devuelve el mapeo entre las claves de audio y los textos en español
    basado en el archivo es.txt y el audioMap de JavaScript
    """
    return {
        'Bienvenida.mp3': '¡Bienvenido a BinIt!, donde cada escaneo cuenta para un mundo mas limpio',
        'Instrucciones.mp3': '¿Como usar BinIt? Primero coloca tu residuo en la zona de deteccion para empezar, despues cuando el objeto este quieto se procesara automaticamente. Al final verifique resultado obtenido',
        'Procesando.mp3': 'Procesando manten quieto el objeto para una mejor identificacion, nuestros algoritmos verdes estan trabajando para identificar este residuo',
        'Bingo.mp3': 'Resultado final. ¡Bingo! ¿Es correcto?',
        'Selecciona-una-opcion.mp3': 'Selecciona una opcion para continuar, tienes 120 segundos',
        'Deposita-en.mp3': 'Deposita en',
        'Residuo.mp3': 'Residuo',
        'Carton.mp3': 'Carton',
        'Vidrio.mp3': 'Vidrio',
        'Metal.mp3': 'Metal',
        'Papel.mp3': 'Papel',
        'Unicel.mp3': 'Unicel',
        'Botella-de-plastico.mp3': 'Botella de platico',
        'Bolsa-de-Plastico.mp3': 'Bolsa de platisco',
        'Organica.mp3': 'Organica',
        'Para-escritura.mp3': 'Para escritura, es decir, plumones, lapices, etc',
        'Envoltorio.mp3': 'Envoltorio',
        'Otro.mp3': 'Otro'
    }

def generate_all_audios_for_language(targetLangName: str, logger=None) -> dict:
    """
    Genera todos los audios necesarios para un idioma específico
    usando voces de referencia dinámicas
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    if not targetLangName in list(get_supported_languages_map().keys()):
        logger.error(f'Idioma no soportado: {targetLangName}')
        return {'success': False, 'error': 'Idioma no soportado'}

    # Verificar que exista al menos una voz de referencia
    if not os.path.exists(VOICE_REFERENCE_BASE_PATH):
        logger.error(f"Directorio de referencias '{VOICE_REFERENCE_BASE_PATH}' no encontrado")
        return {'success': False, 'error': 'Directorio de referencias no encontrado'}
    
    # Obtener códigos de idioma
    langMap = get_supported_languages_map()
    codes = langMap[targetLangName]
    countryCode = codes["country_code"].lower()
    
    # Crear directorio si no existe
    outputDir = f"{OUTPATH_FILE_START}{countryCode}"
    os.makedirs(outputDir, exist_ok=True)
    
    # Inicializar servicios
    try:
        translator = DeepLTranslationService(apiKey=os.getenv("DEEPL_API_KEY"))
        tts_synthesizer = CoquiTextToSpeechService(modelName=COQUI_TTS_MODEL_NAME)
    except Exception as e:
        logger.error(f"Error inicializando servicios: {e}")
        return {'success': False, 'error': 'Error al inicializar servicios'}

    orchestrator = AudioController(translator, tts_synthesizer)
    
    # Obtener mapeo de textos
    audioTextMapping = get_audio_text_mapping()
    
    generatedFiles = []
    errors = []
    voiceUsageLog = []
    
    logger.info(f"--- Iniciando generación de {len(audioTextMapping)} audios para {targetLangName} ---")
    
    for filename, spanishText in audioTextMapping.items():
        try:
            outputPath = os.path.join(outputDir, filename.replace('.mp3', '.wav'))
            
            # Obtener voz de referencia específica para este audio
            voice_reference = get_voice_reference_for_audio(filename)
            
            logger.info(f"Generando: {filename}")
            logger.info(f"  Usando voz de referencia: {os.path.basename(voice_reference)}")
            
            voiceUsageLog.append(f"{filename} -> {os.path.basename(voice_reference)}")
            
            # Verificar que la voz de referencia existe
            if not os.path.exists(voice_reference):
                errors.append(f"Voz de referencia no encontrada para {filename}: {voice_reference}")
                logger.error(f"✗ Voz de referencia no encontrada: {voice_reference}")
                continue
            
            # Traducir texto
            deeplCode = codes["deepl_code"]
            translatedText = translator.translate(spanishText, deeplCode)
            
            if not translatedText:
                errors.append(f"Error traduciendo {filename}")
                logger.error(f"✗ Error traduciendo: {filename}")
                continue
            
            # Generar audio
            coquiCode = codes["coqui_code"]
            success = tts_synthesizer.synthesize(
                translatedText,
                coquiCode,
                voice_reference,
                outputPath
            )
            
            if success:
                # Convertir de .wav a .mp3 si es necesario
                mp3Path = outputPath.replace('.wav', '.mp3')
                if os.path.exists(outputPath) and not os.path.exists(mp3Path):
                    os.rename(outputPath, mp3Path)
                
                generatedFiles.append(filename)
                logger.info(f"✓ Generado: {filename}")
            else:
                errors.append(f"Error generando {filename}")
                logger.error(f"✗ Error generando: {filename}")
                
        except Exception as e:
            errors.append(f"Error en {filename}: {str(e)}")
            logger.error(f"✗ Excepción en {filename}: {e}")
    
    logger.info(f"--- Proceso finalizado. Generados: {len(generatedFiles)}, Errores: {len(errors)} ---")
    logger.info("--- Mapeo de voces utilizadas ---")
    for usage in voiceUsageLog:
        logger.info(f"  {usage}")
    
    return {
        'success': len(generatedFiles) > 0,
        'generated_files': generatedFiles,
        'errors': errors,
        'total_generated': len(generatedFiles),
        'total_errors': len(errors),
        'voice_usage': voiceUsageLog
    }