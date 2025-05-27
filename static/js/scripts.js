document.addEventListener("DOMContentLoaded", () => {
  function toggleScreen(hideId, showId) {
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
    } else {
      console.warn(
        `toggleScreen: Elemento a mostrar con id '${showId}' no encontrado.`
      );
    }
  }

  function processFrame() {
    try {
      if (!isCameraInitialized || isInPredictionPhase) {
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
          toggleScreen("standby", "active");
        }
      } else {
        if (
          screens.active &&
          !screens.active.classList.contains("d-none") &&
          !motionStopTimer
        ) {
          motionStopTimer = setTimeout(() => {
            captureAndSendFrame();
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
          if (data.label) {
            toggleScreen("active", "prediction");

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
            toggleScreen("active", "standby");
          }
        })
        .catch((err) => {
          console.error("Error en fetch /predict:", err);
          resetToStandby(false);
          toggleScreen("active", "standby");
        });
    }, "image/jpeg");
  }

  function startFeedbackTimer() {
    let seconds = 120;
    if (feedbackTimer) {
      feedbackTimer.textContent = `Tiempo restante: ${seconds} segundos`;
    }

    if (predictionTimeoutId) clearInterval(predictionTimeoutId);

    predictionTimeoutId = setInterval(() => {
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
      classButtonsElement.classList.add("d-none"); // This still uses d-none
    }
    prevImageData = null;
    isInPredictionPhase = false;
    if (fromButton) {
      toggleScreen("prediction", "standby");
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
    toggleScreen("prediction", "standby");
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
    standby: document.getElementById("standby"),
    active: document.getElementById("active"),
    prediction: document.getElementById("prediction"),
  };

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

  const CLASS_TRANSLATIONS = {
    CARDBOARD: "Cartón",
    GLASS: "Vidrio",
    METAL: "Metal",
    ORGANIC: "Orgánica",
    PAPER: "Papel",
    PEN: "Para escritura",
    PET: "PET",
    PLASTIC_BAG: "Bolsa plástica",
    UNICEL: "Unicel",
    WRAPPER: "Envoltorio",
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
        classButtonsElement.classList.remove("d-none"); // This still uses d-none, ensure it works with opacity or adapt
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
