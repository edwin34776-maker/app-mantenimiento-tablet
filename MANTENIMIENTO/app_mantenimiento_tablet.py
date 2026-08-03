function doGet(e) {
  // ============================================
  // CONFIGURACIÓN: Cambia esta URL por la de tu app en Streamlit Cloud
  // ============================================
  var streamlitUrl = "https://app-mantenimiento-tablet-npbmgfsqxf9yphk7zlcvw4.streamlit.app/";

  // También puedes pasar la URL como parámetro: ?url=https://tu-app.streamlit.app/
  if (e.parameter.url) {
    streamlitUrl = e.parameter.url;
  }

  var htmlContent = `<!DOCTYPE html>
<html lang="es">
<head>
  <base target="_top">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>App Tablet Mtto Preventivo</title>
  <style>
    * { 
      margin: 0; 
      padding: 0; 
      box-sizing: border-box; 
    }
    html, body { 
      width: 100%; 
      height: 100%; 
      overflow: hidden; 
      background: #0F172A;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Contenedor principal */
    .app-wrapper {
      position: relative;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      background: linear-gradient(160deg, #0F172A 0%, #1E3A5F 40%, #0EA5E9 100%);
    }

    /* ===== MÁSCARA SUPERIOR: Oculta header de Streamlit ===== */
    .mask-header {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 60px;
      background: linear-gradient(135deg, #0EA5E9 0%, #38BDF8 100%);
      z-index: 9999;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      box-shadow: 0 4px 20px rgba(14, 165, 233, 0.4);
    }
    .mask-header-icon {
      font-size: 24px;
    }
    .mask-header-title {
      color: white;
      font-size: 16px;
      font-weight: 800;
      letter-spacing: 0.3px;
      text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .mask-header-badge {
      background: rgba(255,255,255,0.2);
      color: white;
      font-size: 10px;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: 12px;
      margin-left: 8px;
      backdrop-filter: blur(4px);
    }

    /* ===== IFRAME: Carga la app de Streamlit ===== */
    .iframe-container {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: calc(100% + 60px);
      z-index: 1;
    }
    iframe {
      width: 100%;
      height: 100%;
      border: none;
      margin-top: -60px;  /* ← Desplaza hacia arriba para ocultar header Streamlit */
      display: block;
    }

    /* ===== MÁSCARA INFERIOR: Oculta botones flotantes ===== */
    .mask-footer {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 45px;
      background: #F1F5F9;
      z-index: 9999;
      display: flex;
      align-items: center;
      justify-content: center;
      border-top: 1px solid #E2E8F0;
    }
    .mask-footer-text {
      color: #94A3B8;
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.5px;
    }

    /* ===== PANTALLA DE CARGA ===== */
    .loading-screen {
      position: absolute;
      top: 60px;
      left: 0;
      right: 0;
      bottom: 45px;
      background: linear-gradient(160deg, #0F172A 0%, #1E3A5F 40%, #0EA5E9 100%);
      z-index: 5000;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
      transition: opacity 0.5s ease;
    }
    .loading-screen.hidden {
      opacity: 0;
      pointer-events: none;
    }
    .loading-icon {
      font-size: 48px;
      animation: pulse 1.5s ease-in-out infinite;
    }
    @keyframes pulse {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.1); opacity: 0.7; }
    }
    .loading-title {
      color: white;
      font-size: 18px;
      font-weight: 800;
    }
    .loading-subtitle {
      color: rgba(255,255,255,0.7);
      font-size: 12px;
    }
    .loading-bar {
      width: 200px;
      height: 4px;
      background: rgba(255,255,255,0.2);
      border-radius: 2px;
      overflow: hidden;
      margin-top: 8px;
    }
    .loading-bar-fill {
      width: 0%;
      height: 100%;
      background: #38BDF8;
      border-radius: 2px;
      animation: load 2s ease-in-out forwards;
    }
    @keyframes load {
      0% { width: 0%; }
      50% { width: 60%; }
      100% { width: 100%; }
    }

    /* ===== RESPONSIVE ===== */
    @media (max-width: 480px) {
      .mask-header { height: 50px; }
      .mask-header-title { font-size: 14px; }
      .iframe-container { height: calc(100% + 50px); }
      iframe { margin-top: -50px; }
      .loading-screen { top: 50px; }
      .mask-footer { height: 40px; }
    }
  </style>
</head>
<body>
  <div class="app-wrapper">

    <!-- Header personalizado que tapa el de Streamlit -->
    <div class="mask-header">
      <span class="mask-header-icon">🔧</span>
      <span class="mask-header-title">App Tablet Mtto Preventivo</span>
      <span class="mask-header-badge">v2.1</span>
    </div>

    <!-- Pantalla de carga -->
    <div class="loading-screen" id="loadingScreen">
      <div class="loading-icon">🔧</div>
      <div class="loading-title">Mantenimiento Preventivo</div>
      <div class="loading-subtitle">Cargando sistema de órdenes de trabajo...</div>
      <div class="loading-bar">
        <div class="loading-bar-fill"></div>
      </div>
    </div>

    <!-- Iframe con la app de Streamlit -->
    <div class="iframe-container">
      <iframe 
        id="streamlitFrame"
        src="${streamlitUrl}" 
        allow="camera; microphone; clipboard-read; clipboard-write; fullscreen"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-downloads"
      ></iframe>
    </div>

    <!-- Footer que tapa los botones flotantes -->
    <div class="mask-footer">
      <span class="mask-footer-text">© 2026 Sistema de Mantenimiento Preventivo</span>
    </div>

  </div>

  <script>
    // Ocultar pantalla de carga después de 3 segundos
    setTimeout(function() {
      document.getElementById('loadingScreen').classList.add('hidden');
    }, 3000);

    // Si el iframe carga antes, ocultar inmediatamente
    document.getElementById('streamlitFrame').addEventListener('load', function() {
      setTimeout(function() {
        document.getElementById('loadingScreen').classList.add('hidden');
      }, 1500);
    });
  </script>

</body>
</html>`;

  return HtmlService.createHtmlOutput(htmlContent)
    .setTitle("App Tablet Mtto Preventivo")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}
