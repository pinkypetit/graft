# GRAFT: Generative Resource for Academic and Fluency Techniques

GRAFT es una aplicación local, de código abierto y gratuita diseñada para **democratizar y acelerar el dominio del inglés técnico y profesional para hablantes no nativos**.

A diferencia de los cursos tradicionales que enseñan inglés general, GRAFT te permite crear **mazos de Anki altamente personalizados** basados en colecciones de papers científicos o de la industria que realmente necesitas estudiar.

---

## 🚀 ¿Para quién es GRAFT?

1. **Estudiantes y Profesionales Técnicos/Científicos:** Que necesitan leer papers en inglés, comprender terminología avanzada y colaborar globalmente en su área de estudio (energía, estadística, ciencia de datos, clima).
2. **Inmigrantes Recientes y Trabajadores Especializados:** Que buscan trabajar en sectores específicos (como la viticultura, la hostelería o la agricultura) y necesitan aprender rápidamente la jerga laboral del día a día.
3. **Mentes Curiosas:** Autodidactas que desean dominar el vocabulario riguroso de cualquier nicho del conocimiento de forma consistente.

---

## ✨ Características Principales

*   **100% Local & Privado:** Ejecuta la curación lingüística en tu propia computadora usando **Ollama (`qwen2.5:14b`)** y síntesis de voz sin costos, llaves de API externas ni suscripciones.
*   **Filtrado Estadístico TF-IDF:** Extrae las palabras clave más significativas de un lote de papers, filtrando de forma inteligente siglas ruidosas (como GCM) y nombres propios.
*   **Contexto del Mundo Real:** Extrae ejemplos de oraciones reales directamente de tus documentos, eliminando citas bibliográficas, corchetes y errores de conversión.
*   **Audio Neuronal de Alta Fidelidad (SOTA):** Genera audios neuronales en inglés con Microsoft Edge-TTS para cada palabra, significado y oración de ejemplo, empaquetándolos nativamente en el archivo `.apkg`.

---

## 🛠️ Requisitos e Instalación

### 1. Modelos Locales (Ollama)
Debes tener instalado [Ollama](https://ollama.com/) en tu máquina y descargar el modelo Qwen de 14B:

```bash
ollama run qwen2.5:14b
```

### 2. Configurar el Entorno de Python
Clona el repositorio e instala las dependencias necesarias dentro de un entorno virtual:

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

*Nota: Las dependencias clave incluyen `fastapi`, `uvicorn`, `edge-tts`, `genanki`, `markitdown` y `requests`.*

---

## 💻 Ejecución de la Web App

Para lanzar el servidor local de GRAFT y su interfaz de usuario:

```bash
python web_app.py
```

El servidor se iniciará en `http://localhost:8000` y abrirá automáticamente una pestaña de tu navegador web. Desde la interfaz podrás:
*   Ingresar el nombre de tu mazo técnico.
*   Subir archivos PDF (papers) relacionados.
*   Elegir la voz de lectura en inglés y el límite de palabras.
*   Escribir una temática para que el sistema descargue artículos desde arXiv automáticamente si te faltan papers.
*   Ver en tiempo real la terminal con el log de ejecución de la IA.
*   Descargar el archivo `.apkg` directamente en tu equipo.

---

## 🌐 Demo y GitHub Pages

Visita nuestra página oficial del proyecto en GitHub Pages para conocer el flujo de trabajo detallado y descargar un mazo de demostración enfocado en el área de **Vinos y Enología** con 30 términos curados:

👉 **[https://pinkypetit.github.io/graft/](https://pinkypetit.github.io/graft/)**

---

## 📄 Licencia
Este proyecto es de código abierto y está licenciado bajo la Licencia MIT.
