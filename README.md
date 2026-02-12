
# LoL-MetaScraper: Dashboard de Inteligencia Competitiva

## Descripción General

**LoL-MetaScraper** es un sistema automatizado de inteligencia competitiva para League of Legends. Funciona como un "Coach Virtual" basado en datos, diseñado para optimizar la fase de draft mediante estadística pura.

El sistema utiliza una arquitectura híbrida: un script de Python extrae datos en tiempo real del meta actual (Winrates, Banrates, Counters) y los inyecta en una Hoja de Cálculo Maestra (Google Sheets), que actúa como la interfaz de usuario y cerebro estratégico.

## Arquitectura del Sistema

El proyecto no tiene interfaz gráfica tradicional; la interfaz es el propio Excel en la nube.

* **Motor (Python):** `update_lol_data.py` - Realiza el scraping web usando Selenium y mapea los nombres de campeones.
* **Launcher:** `launcher.bat` - Ejecutable de un solo clic para actualizar los datos.
* **Base de Datos/UI:** Google Sheets - Donde se visualizan los datos y se calculan las sinergias.
* **Seguridad:** `credentials.json` - Llave de acceso a la API de Google Cloud.

## Requisitos Previos

1.  Tener instalado **Google Chrome**.
2.  Tener una cuenta de Google (para el Sheet).
3.  Python 3.8 o superior instalado.

## Instalación y Configuración

### 1. Preparación del Entorno
Si tienes el archivo `launcher.bat`, este se encargará de instalar las dependencias automáticamente. Si prefieres hacerlo manual:

    pip install pandas selenium gspread oauth2client webdriver-manager beautifulsoup4

### 2. Configuración de Google Cloud (CRÍTICO)
Para que el script pueda escribir en tu Excel, necesitas autorizarlo:

1.  Consigue el archivo de credenciales JSON de tu Service Account de Google Cloud.
2.  Renombra ese archivo a: `credentials.json`
3.  Colócalo en la **misma carpeta** que el script `update_lol_data.py`.
4.  Abre tu Google Sheet y dale acceso de "Editor" al email que aparece dentro del archivo json (el `client_email`).

## Cómo Usar

1.  Haz doble clic en **`launcher.bat`**.
2.  Se abrirá una ventana negra (consola) y verás cómo el navegador se abre y cierra trabajando en segundo plano.
3.  Espera a que la consola diga que ha terminado o se cierre.
4.  Ve a tu **Google Sheet**.
    * La pestaña **"CRUDO"** tendrá los datos frescos del día.
    * La pestaña **"HOJA BUENA"** (tu Dashboard) se habrá actualizado automáticamente con las nuevas estadísticas.

## Lógica del Dashboard

El sistema no solo vuelca datos, los procesa para tomar decisiones:

* **Winrate:** ¿Está fuerte el campeón en este parche?
* **Counter Pick:** ¿Anula mecánicamente al rival de línea?
* **Sinergia:** ¿Combina con la composición de mi equipo (ej. Wombo Combo, Poke)?

## Estructura de Archivos

/raiz-del-proyecto
│
├── update_lol_data.py    # Código fuente del scraper
├── launcher.bat          # Ejecutable para usuario final
├── credentials.json      # [TU ARCHIVO] Llave de seguridad (NO SUBIR A GITHUB)
└── README.md             # Este archivo

---
Desarrollado por Iván García Miranda
