/**
 * Puente web <-> nativo.
 *
 * En el navegador no hace nada: todas las funciones degradan al comportamiento
 * original. Dentro de Capacitor (iOS/Android) aporta permisos en tiempo de
 * ejecucion, share nativo y gestion del boton atras de Android.
 *
 * Se carga antes que el resto de la app. No usa imports: es un script clasico.
 */
(function (global) {
  "use strict";

  var cap = global.Capacitor || null;
  var plugins = (cap && cap.Plugins) || {};
  var IS_NATIVE = !!(cap && cap.isNativePlatform && cap.isNativePlatform());
  var PLATFORM = IS_NATIVE ? cap.getPlatform() : "web";

  /**
   * Comparte texto. En iOS el WKWebView no implementa navigator.share, asi que
   * se cae al plugin Share y, si tampoco esta, al clipboard + toast.
   */
  function share(payload) {
    if (!IS_NATIVE) {
      if (global.navigator.share) {
        return global.navigator.share(payload).catch(function () {});
      }
      return copyToClipboard(payload.text || "").then(function () {
        notify("Copiado al portapapeles");
      });
    }

    if (plugins.Share && plugins.Share.share) {
      return plugins.Share.share({
        title: payload.title || "",
        text: payload.text || "",
        url: payload.url || "",
        dialogTitle: payload.title || "Compartir",
      }).catch(function () {});
    }

    return copyToClipboard((payload.text || "") + " " + (payload.url || "")).then(function () {
      notify("Copiado al portapapeles");
    });
  }

  function copyToClipboard(text) {
    if (global.navigator.clipboard && global.navigator.clipboard.writeText) {
      return global.navigator.clipboard.writeText(text);
    }
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      return Promise.resolve();
    } catch (e) {
      return Promise.resolve();
    }
  }

  /**
   * Posicion actual. Pide el permiso en el momento de usarla (Android lo exige),
   * y delega en el plugin cuando existe para evitar el puente web lento de
   * WKWebView. Rechaza con un motivo legible.
   */
  function currentPosition() {
    if (IS_NATIVE && plugins.Geolocation) {
      return plugins.Geolocation.checkPermissions().then(function (status) {
        var want = "location";
        if (status.location === "denied") {
          return Promise.reject(new Error("Permiso de ubicacion denegado"));
        }
        if (status.location !== "granted") {
          return plugins.Geolocation.requestPermissions({ permissions: [want] }).then(function (res) {
            if (res.location !== "granted") {
              return Promise.reject(new Error("Permiso de ubicacion denegado"));
            }
            return readNativePosition();
          });
        }
        return readNativePosition();
      });
    }

    return new Promise(function (resolve, reject) {
      if (!global.navigator.geolocation) {
        reject(new Error("Ubicacion no disponible"));
        return;
      }
      global.navigator.geolocation.getCurrentPosition(resolve, function () {
        reject(new Error("No se pudo obtener la ubicacion"));
      }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 });
    });
  }

  function readNativePosition() {
    return plugins.Geolocation.getCurrentPosition({
      enableHighAccuracy: true,
      timeout: 15000,
    }).then(function (pos) {
      // Normaliza a la forma de W3C PositionError que espera la app.
      return {
        coords: { latitude: pos.coords.latitude, longitude: pos.coords.longitude },
      };
    });
  }

  function notify(message) {
    if (typeof global.showToast === "function") {
      global.showToast(message);
    }
  }

  // En Android el boton fisico atras debe cerrar las hojas antes de salir.
  function bindBackButton(onBack) {
    if (PLATFORM !== "android" || !plugins.App) return;
    plugins.App.addListener("backButton", function () {
      if (onBack && onBack() === true) return;
      plugins.App.minimizeApp();
    });
  }

  global.BW = {
    IS_NATIVE: IS_NATIVE,
    PLATFORM: PLATFORM,
    share: share,
    currentPosition: currentPosition,
    bindBackButton: bindBackButton,
  };
})(window);
