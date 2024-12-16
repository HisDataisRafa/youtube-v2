import streamlit as st
from playwright.sync_api import sync_playwright
import time
import json
from datetime import datetime

def get_subtitles_from_downsub(video_urls):
    """
    Obtiene subtítulos de múltiples videos usando downsub.com
    """
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # headless=False para ver el navegador
        context = browser.new_context()
        page = context.new_page()
        
        for i, url in enumerate(video_urls):
            status_text.text(f"Procesando video {i+1} de {len(video_urls)}")
            progress_bar.progress((i + 1)/len(video_urls))
            
            try:
                # Navegar a downsub
                page.goto('https://downsub.com/')
                page.wait_for_load_state('networkidle')
                
                # Ingresar la URL del video
                input_box = page.locator('input[type="text"]')
                input_box.fill(url)
                
                # Hacer clic en el botón de descarga
                page.click('button.rounded-lg')
                
                # Esperar a que aparezcan los resultados
                page.wait_for_selector('.flex.flex-col.space-y-4', timeout=10000)
                
                # Obtener el título del video
                title = page.locator('h1.text-xl').inner_text()
                
                # Encontrar el botón de español o inglés
                subtitle_buttons = page.locator('button.bg-white').all()
                
                subtitle_text = None
                for button in subtitle_buttons:
                    button_text = button.inner_text()
                    if 'Spanish' in button_text or 'English' in button_text:
                        button.click()
                        
                        # Esperar a que se cargue el diálogo
                        time.sleep(2)
                        
                        # Obtener el texto de los subtítulos
                        text_area = page.locator('textarea')
                        subtitle_text = text_area.input_value()
                        
                        # Cerrar el diálogo
                        page.keyboard.press('Escape')
                        break
                
                results.append({
                    'url': url,
                    'title': title,
                    'subtitles': subtitle_text if subtitle_text else "No se encontraron subtítulos"
                })
                
            except Exception as e:
                st.error(f"Error procesando {url}: {str(e)}")
                results.append({
                    'url': url,
                    'title': 'Error',
                    'subtitles': f"Error: {str(e)}"
                })
            
            time.sleep(1)  # Pequeña pausa entre videos
        
        browser.close()
    
    progress_bar.empty()
    status_text.empty()
    return results

def main():
    st.title("🎥 Descargador de Subtítulos - downsub.com")
    st.write("Ingresa las URLs de YouTube (una por línea)")
    
    urls_text = st.text_area("URLs de videos:", height=200)
    
    if st.button("Obtener Subtítulos"):
        if not urls_text.strip():
            st.warning("Por favor ingresa al menos una URL")
            return
        
        # Procesar las URLs
        urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
        
        with st.spinner('Obteniendo subtítulos...'):
            results = get_subtitles_from_downsub(urls)
            
            if results:
                st.success(f"¡Se procesaron {len(results)} videos!")
                
                # Guardar resultados
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # JSON con toda la información
                json_str = json.dumps(results, ensure_ascii=False, indent=2)
                st.download_button(
                    "⬇️ Descargar resultados (JSON)",
                    json_str,
                    f"subtitles_{timestamp}.json",
                    "application/json"
                )
                
                # Archivo de texto solo con subtítulos
                subtitles_text = ""
                for result in results:
                    subtitles_text += f"\n=== {result['title']} ===\n"
                    subtitles_text += f"URL: {result['url']}\n\n"
                    subtitles_text += f"{result['subtitles']}\n"
                    subtitles_text += "="*50 + "\n"
                
                st.download_button(
                    "⬇️ Descargar subtítulos (TXT)",
                    subtitles_text,
                    f"subtitles_{timestamp}.txt",
                    "text/plain"
                )
                
                # Mostrar resultados en la interfaz
                for result in results:
                    st.write("---")
                    st.markdown(f"### {result['title']}")
                    st.write(f"URL: {result['url']}")
                    with st.expander("Ver subtítulos"):
                        st.text_area("", result['subtitles'], height=200)

if __name__ == "__main__":
    main()
