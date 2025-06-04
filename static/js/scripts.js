document.addEventListener("DOMContentLoaded", () => {
  class AudioManager {
    constructor() {
      this.enabled = true;
      this.volume = 1;
      this.audioCache = new Map();
      this.currentLanguage = 'es';
      this.isPlaying = false;
      this.currentAudio = null;
    }
    
    preloadAudio(audioFiles) {
      audioFiles.forEach(file => {
        const audio = new Audio(file);
        audio.preload = 'auto';
        this.audioCache.set(file, audio);
      });
    }
    
    play(audioFile, volume = this.volume, onEndCallback = null) {
      if (!this.enabled) return;
      
      // No reproducir audio si el overlay está activo
      if (isOverlayActive) {
        console.log('Audio cancelado: Overlay de idiomas activo');
        return;
      }
      
      if (this.currentAudio && !this.currentAudio.paused) {
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
        this.currentAudio.onended = null;
        this.currentAudio.onerror = null;
      }
      
      let audio = this.audioCache.get(audioFile);
      if (!audio) {
        audio = new Audio(audioFile);
        this.audioCache.set(audioFile, audio);
      }
      
      audio.volume = volume;
      audio.currentTime = 0;
      this.currentAudio = audio;
      this.isPlaying = true;
      
      // Configurar eventos de fin de audio
      audio.onended = () => {
        this.isPlaying = false;
        this.currentAudio = null;
        // Verificar que el overlay siga inactivo antes de ejecutar callback
        if (onEndCallback && !isOverlayActive) {
          onEndCallback();
        }
      };
      
      audio.onerror = () => {
        this.isPlaying = false;
        this.currentAudio = null;
        console.warn(`Error en audio ${audioFile}`);
      };
      
      // Usar un pequeño delay para evitar conflictos
      setTimeout(() => {
        // Verificar nuevamente que el overlay no esté activo antes de reproducir
        if (this.currentAudio === audio && !isOverlayActive) {
          audio.play().catch(error => {
            // Ignorar errores de AbortError que son normales durante transiciones
            if (error.name !== 'AbortError') {
              console.warn(`Error reproduciendo audio ${audioFile}:`, error);
            }
            this.isPlaying = false;
            this.currentAudio = null;
          });
        }
      }, 50);
    }
    
    playByKey(audioKey, volume = this.volume, onEndCallback = null) {
      const audioMap = {
        'welcome': `/static/audios/${this.currentLanguage}/Bienvenida.mp3`,
        'instructions': `/static/audios/${this.currentLanguage}/Instrucciones.mp3`,
        'processing': `/static/audios/${this.currentLanguage}/Procesando.mp3`,
        'bingo': `/static/audios/${this.currentLanguage}/Bingo.mp3`,
        'select_option': `/static/audios/${this.currentLanguage}/Selecciona-una-opcion.mp3`,
        'deposit_in': `/static/audios/${this.currentLanguage}/Deposita-en.mp3`,
        'waste': `/static/audios/${this.currentLanguage}/Residuo.mp3`,
        'cardboard': `/static/audios/${this.currentLanguage}/Carton.mp3`,
        'glass': `/static/audios/${this.currentLanguage}/Vidrio.mp3`,
        'metal': `/static/audios/${this.currentLanguage}/Metal.mp3`,
        'paper': `/static/audios/${this.currentLanguage}/Papel.mp3`,
        'unicel': `/static/audios/${this.currentLanguage}/Unicel.mp3`,
        'pet': `/static/audios/${this.currentLanguage}/Botella-de-plastico.mp3`,
        'plastic_bag': `/static/audios/${this.currentLanguage}/Bolsa-de-Plastico.mp3`,
        'organic': `/static/audios/${this.currentLanguage}/Organica.mp3`,
        'pen': `/static/audios/${this.currentLanguage}/Para-escritura.mp3`,
        'wrapper': `/static/audios/${this.currentLanguage}/Envoltorio.mp3`,
        'other': `/static/audios/${this.currentLanguage}/Otro.mp3`
      };
      
      if (audioMap[audioKey]) {
        this.play(audioMap[audioKey], volume, onEndCallback);
      }
    }
    
    setLanguage(langCode) {
      this.currentLanguage = langCode.toLowerCase();
    }
    
    setVolume(volume) {
      this.volume = Math.max(0, Math.min(1, volume));
    }
    
    toggle() {
      this.enabled = !this.enabled;
    }

    canChangeScreen() {
      return !this.isPlaying;
    }

    stopCurrentAudio() {
      if (this.currentAudio && !this.currentAudio.paused) {
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
        this.currentAudio.onended = null;
        this.currentAudio.onerror = null;
      }
      this.isPlaying = false;
      this.currentAudio = null;
    }
  }

  class LanguageDropdown {
    constructor() {
      this.dropdown = document.getElementById('langDropdown');
      this.selected = document.getElementById('dropdownSelected');
      this.options = document.getElementById('dropdownOptions');
      this.currentLang = 'es';
      this.languages = [];
      
      this.init();
    }

    async init() {
      try {
        const response = await fetch("/binit/lang", {method: "GET"});
        const allLanguages = await response.json();
        
        for (let [strLang, isoCode] of Object.entries(allLanguages)) {
          this.languages.push({
            displayName: strLang,
            iso: isoCode.country_code
          });
        }

        this.renderOptions();
        this.bindEvents();
      } catch (error) {
        console.error('Error cargando idiomas:', error);
      }
    }

    renderOptions() {
      this.options.innerHTML = '';
      
      this.languages.forEach(lang => {
        const imgPath = `../static/images/lang/${lang.iso.toLowerCase()}.png`
        const option = document.createElement('div');
        option.className = `dropdown-option ${lang.iso === this.currentLang ? 'selected' : ''}`;
        option.dataset.lang = lang.iso;
        
        option.innerHTML = `
          <div class="lang-option">
            <span class="lang-flag">
              <img src="${imgPath}" alt="${lang.iso.toUpperCase()}">
            </span>
            <div class="lang-text">
              <p class="lang-name">${lang.displayName}</p>
              <p class="isoLang">(${lang.iso.toUpperCase()})</p>
            </div>
          </div>
        `;
        
        option.addEventListener('click', () => this.selectLanguage(lang));
        this.options.appendChild(option);
      });
    }

    bindEvents() {
      this.selected.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggle();
      });

      document.addEventListener('click', (e) => {
        if (!this.dropdown.contains(e.target)) {
          this.close();
        }
      });

      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.close();
        }
      });
    }

    toggle() {
      const isOpen = this.options.classList.contains('show');
      if (isOpen) {
        this.close();
      } else {
        this.open();
      }
    }

    open() {
      this.options.classList.add('show');
      this.selected.classList.add('active');
    }

    close() {
      this.options.classList.remove('show');
      this.selected.classList.remove('active');
    }

    async selectLanguage(lang) {
      this.currentLang = lang.iso;
      
      const selectedLangName = this.selected.querySelector('.lang-name');
      const selectedIsoLang = this.selected.querySelector('.isoLang');
      
      selectedLangName.textContent = lang.displayName;
      selectedIsoLang.textContent = `(${lang.iso.toUpperCase()})`;
      
      this.renderOptions();
      
      this.close();
      
      // Verificar si existen los audios para este idioma
      const audioExists = await this.checkAudioExists(lang.iso);
      
      if (!audioExists) {
        // Mostrar overlay y generar audios
        await this.generateLanguageAudios(lang);
      }
      
      this.reproduceAudio(lang.iso);
    }

    async checkAudioExists(langCode) {
      try {
        const testAudioUrl = `/static/audios/${langCode.toLowerCase()}/Bienvenida.mp3`;
        const response = await fetch(testAudioUrl, { method: 'HEAD' });
        return response.ok;
      } catch (error) {
        console.log(`Audio no encontrado para idioma ${langCode}`);
        return false;
      }
    }

    async generateLanguageAudios(lang) {
      const progressText = document.getElementById('progressText');
      
      try {
        // Activar el overlay y detener todas las transiciones y audios
        showAudioGenerationOverlay();
        progressText.textContent = 'Iniciando generación de audios...';
        
        // Encontrar el nombre del idioma para el backend
        const languageName = lang.displayName;
        
        // Llamar al endpoint de generación
        const response = await fetch('/binit/voice', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            lang: languageName
          })
        });

        if (!response.ok) {
          throw new Error(`Error en generación: ${response.status}`);
        }

        const result = await response.json();
        progressText.textContent = 'Audios generados exitosamente';
        
        // Pequeño delay para mostrar el mensaje de éxito antes de ocultar
        setTimeout(() => {
          hideAudioGenerationOverlay();
        }, 1000);

      } catch (error) {
        console.error('Error generando audios:', error);
        progressText.textContent = 'Error al generar audios. Usando español por defecto.';
        
        setTimeout(() => {
          hideAudioGenerationOverlay();
          // Fallback a español
          this.currentLang = 'es';
          audioManager.setLanguage('es');
        }, 2000);
      }
    }

    reproduceAudio(langCode) {
      // No reproducir audio si el overlay está activo
      if (!canPerformTransitions()) {
        console.log('reproduceAudio: Cancelado - Overlay activo');
        return;
      }
      
      audioManager.setLanguage(langCode);
      audioManager.playByKey('welcome');
    }
  }

  const audioManager = new AudioManager();
  new LanguageDropdown();

  // Variables globales para controlar el estado del overlay y transiciones
  let isOverlayActive = false;
  let overlayElement = null;

  // Funciones para manejar el overlay de generación de audios
  function showAudioGenerationOverlay() {
    isOverlayActive = true;
    overlayElement = document.getElementById('audioGenerationOverlay');
    
    // Detener cualquier audio que esté reproduciéndose
    audioManager.stopCurrentAudio();
    
    // Cancelar cualquier timer de transición
    if (motionStopTimer) {
      clearTimeout(motionStopTimer);
      motionStopTimer = null;
    }
    
    // Cancelar timer de feedback si existe
    if (predictionTimeoutId) {
      clearInterval(predictionTimeoutId);
      predictionTimeoutId = null;
    }
    
    // Mostrar overlay
    if (overlayElement) {
      overlayElement.classList.remove('d-none');
    }
    
    console.log('Overlay activado: Todas las transiciones y audios detenidos');
  }

  function hideAudioGenerationOverlay() {
    isOverlayActive = false;
    
    // Ocultar overlay
    if (overlayElement) {
      overlayElement.classList.add('d-none');
    }
    
    console.log('Overlay desactivado: Transiciones y audios habilitados');
  }

  // Función para verificar si se pueden realizar transiciones
  function canPerformTransitions() {
    return !isOverlayActive;
  }

  // Función para transiciones automáticas del sistema (permite interrumpir audio)
  function systemToggleScreen(hideId, showId) {
    // Verificar si el overlay está activo
    if (!canPerformTransitions()) {
      console.log(`systemToggleScreen: Cancelado - Overlay activo`);
      return;
    }
    
    console.log(`systemToggleScreen: Transición automática de '${hideId}' a '${showId}'`);
    forceToggleScreen(hideId, showId);
  }

  function toggleScreen(hideId, showId) {
    // Verificar si el overlay está activo
    if (!canPerformTransitions()) {
      console.log(`toggleScreen: Cancelado - Overlay activo`);
      return;
    }
    
    if (audioManager.isPlaying) {
      console.log(`toggleScreen: Bloqueado - Audio reproduciéndose. Transición de '${hideId}' a '${showId}' cancelada.`);
      return;
    }

    const hideElement = screens[hideId];
    const showElement = screens[showId];

    if (hideElement) {
      hideElement.classList.remove("screen-active");
      hideElement.classList.add("d-none");
    } else {
      console.warn(
        `toggleScreen: Elemento a ocultar con id '${hideId}' no encontrado.`
      );
    }

    if (showElement) {
      showElement.classList.remove("d-none");
      showElement.offsetHeight;
      showElement.classList.add("screen-active");
      playScreenAudio(showId);
    } else {
      console.warn(
        `toggleScreen: Elemento a mostrar con id '${showId}' no encontrado.`
      );
    }
  }

  function forceToggleScreen(hideId, showId) {
    // Verificar si el overlay está activo
    if (!canPerformTransitions()) {
      console.log(`forceToggleScreen: Cancelado - Overlay activo`);
      return;
    }
    
    const wasPlaying = audioManager.isPlaying;
    if (wasPlaying) {
      console.log(`forceToggleScreen: Deteniendo audio para forzar transición de '${hideId}' a '${showId}'`);
      audioManager.stopCurrentAudio();
    }

    const hideElement = screens[hideId];
    const showElement = screens[showId];

    if (hideElement) {
      hideElement.classList.remove("screen-active");
      hideElement.classList.add("d-none");
    } else {
      console.warn(
        `forceToggleScreen: Elemento a ocultar con id '${hideId}' no encontrado.`
      );
    }

    if (showElement) {
      showElement.classList.remove("d-none");
      showElement.offsetHeight;
      showElement.classList.add("screen-active");
      
      if (wasPlaying) {
        setTimeout(() => {
          playScreenAudio(showId);
        }, 100);
      } else {
        playScreenAudio(showId);
      }
    } else {
      console.warn(
        `forceToggleScreen: Elemento a mostrar con id '${showId}' no encontrado.`
      );
    }
  }

  function processFrame() {
    try {
      // No procesar si el overlay está activo
      if (!isCameraInitialized || isInPredictionPhase || !canPerformTransitions()) {
        requestAnimationFrame(processFrame);
        return;
      }

      const w = video.videoWidth,
        h = video.videoHeight;
      if (w === 0 || h === 0) {
        requestAnimationFrame(processFrame);
        return;
      }

      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }

      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      ctx.drawImage(video, 0, 0, w, h);
      const currentImageData = ctx.getImageData(0, 0, w, h);

      if (detectMotion(currentImageData, prevImageData)) {
        if (motionStopTimer) {
          clearTimeout(motionStopTimer);
          motionStopTimer = null;
        }
        if (screens.standby && !screens.standby.classList.contains("d-none")) {
          toggleScreen("standby", "use");
        }
      } else {
        if (
          screens.active &&
          !screens.active.classList.contains("d-none") &&
          !motionStopTimer
        ) {
          motionStopTimer = setTimeout(() => {
            // Verificar nuevamente si se pueden realizar transiciones antes de capturar
            if (canPerformTransitions()) {
              captureAndSendFrame();
            }
            motionStopTimer = null;
            isInPredictionPhase = true;
          }, 1500);
        }
      }
      prevImageData = currentImageData;
    } catch (e) {
      console.error("Error en processFrame:", e);
    }
    requestAnimationFrame(processFrame);
  }

  function captureAndSendFrame() {
    // No procesar si el overlay está activo
    if (!canPerformTransitions()) {
      console.log('captureAndSendFrame: Cancelado - Overlay activo');
      return;
    }
    
    sendCtx.drawImage(video, 0, 0, sendCanvas.width, sendCanvas.height);
    // if (capturedImage) {
    //   capturedImage.src = sendCanvas.toDataURL();
    // }

    sendCanvas.toBlob((blob) => {
      fetch("/binit/predict", {
        method: "POST",
        body: blob,
      })
        .then((res) => res.json())
        .then((data) => {
          // Verificar nuevamente si el overlay está activo antes de procesar la respuesta
          if (!canPerformTransitions()) {
            console.log('Respuesta de predicción ignorada: Overlay activo');
            return;
          }
          
          if (data.label) {
            forceToggleScreen("active", "prediction");

            const gradcamImage = document.getElementById("gradcamImage");
            if (gradcamImage) {
              gradcamImage.src = `data:image/jpeg;base64,${data.gradcam}`;
            }

            currentPredictionLabel = data.label;
            if (predictedClass) {
              predictedClass.textContent =
                CLASS_TRANSLATIONS[data.label] || data.label;
            }
            
            startFeedbackTimer();
          } else {
            console.warn("Predicción recibida sin etiqueta (label).");
            resetToStandby(false);

            const currentScreen = Object.keys(screens).find(key => 
              !screens[key].classList.contains("d-none")
            );
            if (currentScreen) {
              forceToggleScreen(currentScreen, "standby");
            }
          }
        })
        .catch((err) => {
          console.error("Error en fetch /predict:", err);
          resetToStandby(false);
          // Si viene desde active, regresar a standby (forzar por error)
          const currentScreen = Object.keys(screens).find(key => 
            !screens[key].classList.contains("d-none")
          );
          if (currentScreen) {
            forceToggleScreen(currentScreen, "standby");
          }
        });
    }, "image/jpeg");
  }

  function startFeedbackTimer() {
    // No iniciar timer si el overlay está activo
    if (!canPerformTransitions()) {
      console.log('startFeedbackTimer: Cancelado - Overlay activo');
      return;
    }
    
    let seconds = 120;
    if (feedbackTimer) {
      feedbackTimer.textContent = `Tiempo restante: ${seconds} segundos`;
    }

    if (predictionTimeoutId) clearInterval(predictionTimeoutId);

    predictionTimeoutId = setInterval(() => {
      // Verificar en cada tick si el overlay sigue inactivo
      if (!canPerformTransitions()) {
        clearInterval(predictionTimeoutId);
        predictionTimeoutId = null;
        console.log('Feedback timer cancelado: Overlay activado');
        return;
      }
      
      seconds--;
      if (feedbackTimer) {
        feedbackTimer.textContent = `Tiempo restante: ${seconds} segundos`;
      }

      if (seconds <= 0) {
        clearInterval(predictionTimeoutId);
        handleUserResponse(false, null);
      }
    }, 1000);
  }

  function resetToStandby(fromButton) {
    if (predictionTimeoutId) clearInterval(predictionTimeoutId);
    if (motionStopTimer) {
      clearTimeout(motionStopTimer);
      motionStopTimer = null;
    }
    if (classButtonsElement) {
      classButtonsElement.classList.add("d-none");
    }
    prevImageData = null;
    isInPredictionPhase = false;
    if (fromButton) {
      forceToggleScreen("prediction", "standby");
    }
  }

  function handleUserResponse(isCorrect, correctedClassFromUser) {
    resetToStandby(false);

    let classToSave = null;
    if (isCorrect) {
      classToSave = currentPredictionLabel;
    } else if (correctedClassFromUser) {
      classToSave = correctedClassFromUser;
    }

    if (classToSave) {
      sendCanvas.toBlob((blob) => {
        const formData = new FormData();
        formData.append("image", blob, "image.jpg");
        formData.append("correct_class", classToSave);
        fetch("/binit/save_image", { method: "POST", body: formData })
          .then((res) => res.json())
          .then((data) => console.log("Respuesta de /save_image:", data))
          .catch((err) => console.error("Error en fetch /save_image:", err));
      }, "image/jpeg");
    }
    forceToggleScreen("prediction", "standby");
  }

  function detectMotion(curr, prev) {
    if (!prev) return false;

    let changedPixels = 0;
    const totalPixels = curr.width * curr.height;
    if (totalPixels === 0) return false;

    const currData = curr.data;
    const prevData = prev.data;

    for (let i = 0; i < currData.length; i += 4) {
      const grayCurr =
        0.299 * currData[i] + 0.587 * currData[i + 1] + 0.114 * currData[i + 2];
      const grayPrev =
        0.299 * prevData[i] + 0.587 * prevData[i + 1] + 0.114 * prevData[i + 2];
      if (Math.abs(grayCurr - grayPrev) > pixelThreshold) {
        changedPixels++;
      }
    }
    return changedPixels / totalPixels > motionPercent;
  }

  function playScreenAudio(screenId) {
    // Verificar si el overlay está activo
    if (!canPerformTransitions()) {
      console.log(`playScreenAudio: Cancelado - Overlay activo`);
      return;
    }
    
    switch(screenId) {
      case 'standby':
        audioManager.playByKey('welcome');
        break;
      case 'use':
        audioManager.playByKey('instructions', audioManager.volume, () => {
          if (!screens.use.classList.contains("d-none") && canPerformTransitions()) {
            systemToggleScreen('use', 'active');
          }
        });
        break;
      case 'active':
        audioManager.playByKey('processing');
        break;
      case 'prediction':
        audioManager.playByKey('bingo', audioManager.volume, () => {
          if (currentPredictionLabel && !screens.prediction.classList.contains("d-none") && canPerformTransitions()) {
            playClassificationAudio(currentPredictionLabel);
          }
        });
        break;
    }
  }

  function playClassificationAudio(label) {
    // FIXIT: More shorter
    const audioKeyMap = {
      'CARDBOARD': 'cardboard',
      'GLASS': 'glass',
      'METAL': 'metal',
      'PAPER': 'paper',
      'UNICEL': 'unicel',
      'PET': 'pet',
      'PLASTIC_BAG': 'plastic_bag',
      'ORGANIC': 'organic',
      'PEN': 'pen',
      'WRAPPER': 'wrapper',
      'OTHER': 'other'
    };
    
    const audioKey = audioKeyMap[label];
    if (audioKey) {
      audioManager.playByKey('waste', audioManager.volume, () => {
        audioManager.playByKey(audioKey, audioManager.volume, () => {
          audioManager.playByKey('select_option');
        });
      });
    }
  }

  const video = document.getElementById("video");
  const canvas = document.getElementById("canvas");
  // const capturedImage = document.getElementById("capturedImage");
  const predictedClass = document.getElementById("predictedClass");
  const feedbackTimer = document.getElementById("feedbackTimer");
  const classButtonsElement = document.getElementById("classButtons");
  const classButtonsContainer = document.getElementById(
    "classButtonsPlaceholder"
  );

  const screens = {
    loading: document.getElementById("loading"),
    use: document.getElementById("use"),
    standby: document.getElementById("standby"),
    active: document.getElementById("active"),
    prediction: document.getElementById("prediction"),
  };

  // FIXIT: More shorter
  const CLASS_NAMES = [
    "CARDBOARD",
    "GLASS",
    "METAL",
    "ORGANIC",
    "PAPER",
    "PEN",
    "PET",
    "PLASTIC_BAG",
    "UNICEL",
    "WRAPPER",
    "OTHER",
  ];

  // FIXIT: More shorter
  const CLASS_TRANSLATIONS = {
    CARDBOARD: "Cartón",
    GLASS: "Vidrio",
    METAL: "Metal",
    PAPER: "Papel",
    UNICEL: "Unicel",
    PET: "Botella plástica",
    PLASTIC_BAG: "Bolsa plástica",
    ORGANIC: "Orgánica/Restos de comida",
    PEN: "Lapiz, plumas, plumones, etc.",
    WRAPPER: "Envoltorio (Papas, dulces, etc.)",
    OTHER: "Otro",
  };

  let motionStopTimer = null;
  let isInPredictionPhase = false;
  let isCameraInitialized = false;
  let predictionTimeoutId = null;
  let currentPredictionLabel = null;
  let prevImageData = null;
  const pixelThreshold = 35;
  const motionPercent = 0.05;

  const sendCanvas = document.createElement("canvas");
  sendCanvas.width = 255;
  sendCanvas.height = 255;
  const sendCtx = sendCanvas.getContext("2d");

  // Inicializar botones de clases
  if (classButtonsContainer) {
    CLASS_NAMES.forEach((className) => {
      const button = document.createElement("button");
      button.className = "btn-custom";
      const translatedName = CLASS_TRANSLATIONS[className] || className;
      button.textContent = translatedName;
      button.addEventListener("click", () =>
        handleUserResponse(false, className)
      );
      classButtonsContainer.appendChild(button);
    });
  } else {
    console.error(
      "Error: El contenedor para los botones de clase (classButtonsPlaceholder) no fue encontrado."
    );
  }

  // Event listeners
  const confirmCorrectButton = document.getElementById("confirmCorrect");
  if (confirmCorrectButton) {
    confirmCorrectButton.addEventListener("click", () =>
      handleUserResponse(true, null)
    );
  }

  const confirmIncorrectButton = document.getElementById("confirmIncorrect");
  if (confirmIncorrectButton) {
    confirmIncorrectButton.addEventListener("click", () => {
      if (classButtonsElement) {
        classButtonsElement.classList.remove("d-none");
      }
    });
  }

  const repeatButton = document.getElementById("repeatButton");
  if (repeatButton) {
    repeatButton.addEventListener("click", () => resetToStandby(true));
  }

  navigator.mediaDevices
    .getUserMedia({ video: { facingMode: "environment" } })
    .then((stream) => {
      video.srcObject = stream;
      video
        .play()
        .then(() => {
          setTimeout(() => {
            isCameraInitialized = true;
            toggleScreen("loading", "standby");
            requestAnimationFrame(processFrame);
          }, 1000);
        })
        .catch((playError) => {
          console.error("Error al intentar reproducir el video:", playError);
          if (screens.loading) {
            screens.loading.innerHTML = `
                      <div class="error-message">
                          Error al iniciar la reproducción de la cámara.
                      </div>`;
          }
        });
    })
    .catch((err) => {
      console.error("Error al acceder a la cámara:", err);
      if (screens.loading) {
        screens.loading.innerHTML = `
                  <div class="error-message">
                      Error al acceder a la cámara. Asegúrate de conceder los permisos necesarios.
                  </div>`;
      }
    });
});
