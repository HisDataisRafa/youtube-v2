import streamlit as st
from playwright.sync_api import sync_playwright
import time
from datetime import datetime
import json
import os

# Instalar playwright al inicio
if not os.path.exists("/usr/lib/chromium-browser/chromedriver"):
    os.system("playwright install chromium")

# Configuración de la página
st.set_page_config(
    page_title="Downsub Scraper", 
    layout="wide",
    menu_items={
        'About': 'Descargador de subtítulos de YouTube usando downsub.com'
    }
)

def extract_video_id(url):
    """Extrae el ID del video de una URL de YouTube"""
    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]
    elif "youtube.com" in url:
        if "watch?v=" in url:
            return url.split("watch?v=")[1].split("&")[0]
        elif "shorts/" in url:
            return url.split("shorts/")[1].split("?")[0]
    return url

def get_subtitles(url, page):
    """Obtiene los subtítulos de un video específico"""
    try:
        # Limpiar la URL y obtener el ID del video
        video_id = extract_video_id(url)
        if not video_id:
            return {
                'title': 'Error',
                'subtitles': "URL inválida",
                'language': 'None'
            }

        # Navegar a downsub
        page.goto('https://downsub.com/', timeout=60000)
        time.sleep(2)

        # Ingresar la URL
        input_selector = 'input[type="text"]'
        page.wait_for_selector(input_selector, timeout=30000)
        input_box = page.locator(input_selector)
        input_box.fill(f"https://www.youtube.com/watch?v={video_id}")
        
        # Hacer clic en el botón de descarga
        download_button = page.locator('button.rounded-lg')
        download_button.click()
        
        # Esperar a que aparezcan los resultados
        page.wait_for_selector('.flex.flex-col.space-y-4', timeout=60000)
        time.sleep(3)
        
        # Obtener el título
        title_element = page.locator('h1.text-xl')
        title = title_element.inner_text() if title_element.count() > 0 else "Sin título"
        
        # Buscar subtítulos en español o inglés
        subtitle_buttons = page.locator('button.bg-white').all()
        subtitle_text = None
        language_found = 'None'
        
        for button in subtitle_buttons:
            text = button.inner_text()
            if 'Spanish' in text or 'English' in text:
                button.click()
                time.sleep(2)
                
                # Obtener el texto
                text_area = page.locator('textarea')
                if text_area.count() > 0:
                    subtitle_text = text_area.input_value()
                    language_found = 'Spanish' if 'Spanish' in text else 'English'
                
                # Cerrar el diálogo
                page.keyboard.press('Escape')
                break
        
        return {
            'title': title,
            'subtitles': subtitle_text if subtitle_text else "No se encontraron subtítulos",
            'language': language_found
        }
        
    except Exception as e:
        st.error(f"Error procesando {url}: {str(e)}")
        return {
            'title': 'Error',
            'subtitles': f"Error: {str(e)}",
            'language': 'None'
        }

def process_urls(urls):
    """Procesa una lista de URLs y obtiene sus subtítulos"""
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        with sync_playwright() as p:
            # Iniciar navegador con configuración especial para Streamlit Cloud
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            context = browser.new_context()
            page = context.new_page()
            
            # Procesar cada URL
            for i, url in enumerate(urls):
                status_text.text(f"Procesando video {i+1} de {len(urls)}")
                progress_bar.progress((i + 1)/len(urls))
                
                result = get_subtitles(url, page)
                results.append({
                    'url': url,
                    **result
                })
                time.sleep(1)
            
            browser.close()
    
    except Exception as e:
        st.error(f"Error general: {str(e)}")
    
    finally:
        progress_bar.empty()
        status_text.empty()
    
    return results

def main():
    st.title("📝 Descargador de Subtítulos de YouTube")
    st.markdown("""
    Este programa obtiene subtítulos de videos de YouTube usando downsub.com.
    
    **Instrucciones:**
    1. Pega las URLs de los videos (una por línea)
    2. Haz clic en "Obtener Subtítulos"
    3. Espera a que se procesen todos los videos
    4. Descarga los resultados en JSON o TXT
    """)
    
    # Área para ingresar URLs
    urls_text = st.text_area(
        "URLs de YouTube (una por línea):",
        placeholder="https://www.youtube.com/watch?v=...\nhttps://youtu.be/...\nhttps://www.youtube.com/shorts/...",
        height=150
    )
    
    if st.button("🔍 Obtener Subtítulos"):
        if not urls_text.strip():
            st.warning("⚠️ Por favor ingresa al menos una URL")
            return
            
        # Limpiar y validar URLs
        urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
        
        with st.spinner('Procesando videos...'):
            results = process_urls(urls)
            
            if results:
                st.success(f"✅ Se procesaron {len(results)} videos!")
                
                # Preparar archivos para descarga
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                col1, col2 = st.columns(2)
                
                # JSON con toda la información
                with col1:
                    json_str = json.dumps(results, ensure_ascii=False, indent=2)
                    st.download_button(
                        "⬇️ Descargar datos (JSON)",
                        json_str,
                        f"subtitles_{timestamp}.json",
                        "application/json"
                    )
                
                # TXT solo con subtítulos
                with col2:
                    subtitles_text = ""
                    for result in results:
                        subtitles_text += f"\n=== {result['title']} ===\n"
                        subtitles_text += f"URL: {result['url']}\n"
                        subtitles_text += f"Idioma: {result['language']}\n\n"
                        subtitles_text += f"{result['subtitles']}\n"
                        subtitles_text += "="*50 + "\n"
                    
                    st.download_button(
                        "⬇️ Descargar subtítulos (TXT)",
                        subtitles_text,
                        f"subtitles_{timestamp}.txt",
                        "text/plain"
                    )
                
                # Mostrar resultados
                st.subheader("📋 Resultados")
                for result in results:
                    st.write("---")
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        st.markdown(f"**Título:**")
                        st.markdown(f"**URL:**")
                        st.markdown(f"**Idioma:**")
                    
                    with col2:
                        st.markdown(result['title'])
                        st.markdown(f"[{result['url']}]({result['url']})")
                        st.markdown(result['language'])
                    
                    with st.expander("Ver subtítulos"):
                        st.text_area(
                            "",
                            result['subtitles'],
                            height=200,
                            key=f"text_{result['url']}"
                        )

if __name__ == "__main__":
    main()
