import streamlit as st
import pandas as pd
import os
import re
import urllib.parse
import base64
import datetime
from sheets_services import read_sheet_data, GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME, append_sheet_data

GOOGLE_ERROR_LOG_SHEET_ID = GOOGLE_SHEET_ID # Usando la misma hoja para el log de errores
GOOGLE_ERROR_LOG_SHEET_NAME = "logs" # El usuario debe crear esta pestaña en la hoja de cálculo

from drive_services import list_pdfs_in_folder, GOOGLE_DRIVE_FOLDER_ID

# Configuración de la página de Streamlit
def get_image_as_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

img_base64 = get_image_as_base64("Guardafauna - 1.png")

st.set_page_config(layout="wide", page_title="Panel Caza 2026")

if 'show_dev_section_main' not in st.session_state:
    st.session_state.show_dev_section_main = False

st.markdown("""
    <style>
    div[data-testid="stTextInput"] input {
        background-color: #FFFFFF; /* White background */
        color: #262730; /* Dark text */
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    /* Contenedor de la barra de pestañas */
    div[role="tablist"] {
        display: flex;
        width: 100%; /* Mantener el 100% de ancho */
        margin-bottom: 20px;
    }

    /* Estilo para cada pestaña individual */
    div[role="tab"] {
        padding: 10px 20px;
        font-size: 18px;
        font-weight: 900 !important;  /* Forzar la fuente aún más negrita */
        border-radius: 8px; /* Bordes un poco más redondeados */
        margin: 0 8px;      /* Más espacio entre pestañas */
        border: 2px solid #A8C289; /* Borde más grueso y con primaryColor */
        background-color: #E6EFF2; /* Fondo muy claro de nuestro color corporativo (teal) */
        color: #2E5661; /* Texto con nuestro color corporativo (dark teal) */
        flex-grow: 1;
        text-align: center;
        transition: all 0.3s ease-in-out; /* Transición suave para hover/active */
    }

    /* Efecto hover para las pestañas inactivas */
    div[role="tab"]:hover {
        background-color: #D3E0E4; /* Un tono un poco más oscuro al pasar el ratón */
    }

    /* Estilo para la pestaña activa */
    div[role="tab"][aria-selected="true"] {
        background-color: #2E5661; /* Fondo de la pestaña activa (dark teal) */
        color: #FFFFFF;     /* Texto blanco para pestaña activa */
        border-color: #2E5661; /* Borde del mismo color que el fondo activo */
    }
    </style>
""", unsafe_allow_html=True)



col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.markdown(f"<div style='text-align: center;'><img src='data:image/png;base64,{img_base64}' width='200'></div>", unsafe_allow_html=True)
st.title("Tablero de Control Caza 2026")

# Definición de las pestañas del menú superior
tab1, tab2, tab3 = st.tabs(["Inscripciones", "Permiso de Caza (próximamente)", "Dashboard"])

# --- Contenido de la pestaña "Inscripciones" ---
with tab1:
    # --- Lógica de Carga y Procesamiento de Datos ---
    def load_and_process_data():
        with st.spinner("Conectando con Google y cargando datos..."):
            sheet_df = pd.DataFrame() # Initialize sheet_df
            try:
                sheet_df = read_sheet_data(GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME)
                st.write(f"DEBUG: Columnas originales de sheet_df: {sheet_df.columns.tolist()}") # DEBUG
            except Exception as e:
                st.error(f"Error al leer la hoja de cálculo principal: {e}")
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                error_message = f"{timestamp} - Error al leer la hoja principal ({GOOGLE_SHEET_NAME}): {e}"
                try:
                    append_sheet_data(GOOGLE_ERROR_LOG_SHEET_ID, GOOGLE_ERROR_LOG_SHEET_NAME, [[error_message]])
                except Exception as sheet_e:
                    st.warning(f"No se pudo registrar el error de lectura de hoja en Google Sheet: {sheet_e}")
                st.session_state.filtered_df = pd.DataFrame()
                return # Stop processing if sheet reading failed

            # Continue with processing only if sheet_df was loaded successfully
            try:
                pdf_list = list_pdfs_in_folder(GOOGLE_DRIVE_FOLDER_ID)

                if sheet_df.empty:
                    st.warning("No se encontraron datos en la Hoja de Cálculo.")
                    st.session_state.filtered_df = pd.DataFrame()
                    return
                
                st.success("¡Datos cargados y procesados exitosamente!")
                
                pdf_link_map = {}
                if pdf_list:
                    for pdf in pdf_list:
                        name_part, extension = os.path.splitext(pdf['name'])
                        cleaned_name = name_part.strip() + extension
                        pdf_link_map[cleaned_name] = pdf['link']

                columnas_deseadas = ['nombre_establecimiento', 'razon_social', 'email', 'celular', 'Fecha']
                columnas_existentes = [col for col in columnas_deseadas if col in sheet_df.columns]
                st.write(f"DEBUG: Columnas existentes después de filtrado: {columnas_existentes}") # DEBUG

                if not columnas_existentes:
                    st.error("El DataFrame no contiene ninguna de las columnas deseadas.")
                    st.session_state.filtered_df = pd.DataFrame()
                    return

                filtered_df = sheet_df[columnas_existentes].copy()
                if 'email' in filtered_df.columns: # DEBUG
                    st.write(f"DEBUG: Primeros 5 emails en filtered_df: {filtered_df['email'].head().tolist()}") # DEBUG

                def vincular_pdf(row):
                    nombre_establecimiento = str(row.get('nombre_establecimiento', '')).strip()
                    pdf_name = f"Planilla_Inscripción_Establecimiento_{nombre_establecimiento}.pdf"
                    pdf_link = pdf_link_map.get(pdf_name)
                    return f"[Ver PDF]({pdf_link})" if pdf_link else "No encontrado"
                
                if 'nombre_establecimiento' in filtered_df.columns:
                    filtered_df['link_pdf'] = filtered_df.apply(vincular_pdf, axis=1)
                
                st.session_state.filtered_df = filtered_df

            except Exception as e:
                st.error(f"Ocurrió un error general al procesar los datos: {e}")
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                error_message = f"{timestamp} - Error en procesamiento de datos: {e}"
                try:
                    append_sheet_data(GOOGLE_ERROR_LOG_SHEET_ID, GOOGLE_ERROR_LOG_SHEET_NAME, [[error_message]])
                except Exception as sheet_e:
                    st.warning(f"No se pudo registrar el error de procesamiento en Google Sheet: {sheet_e}")
                st.session_state.filtered_df = pd.DataFrame()

    # --- Control de Flujo Principal ---
    # Inicializar el session state si no existe
    if 'filtered_df' not in st.session_state:
        st.session_state.filtered_df = None

    # Botón para recargar los datos
    if st.button("Recargar Datos"):
        load_and_process_data()

    # Cargar datos la primera vez que se abre la app
    if st.session_state.filtered_df is None:
        load_and_process_data()

    # Buscador
    search_query = st.text_input("Buscar por nombre de establecimiento, razón social, etc.", "")

    # --- Lógica de Visualización (siempre se ejecuta si hay datos) ---
    if st.session_state.filtered_df is not None and not st.session_state.filtered_df.empty:
        
        # Aplicar filtro de búsqueda si hay una consulta
        if search_query:
            # Filtrar el DataFrame
            mask = st.session_state.filtered_df.apply(lambda row: any(row.astype(str).str.contains(search_query, case=False)), axis=1)
            display_df = st.session_state.filtered_df[mask]
        else:
            display_df = st.session_state.filtered_df

        st.subheader(f"Mostrando {len(display_df)} Registros")
        
        for index, row in display_df.iterrows():
            with st.expander(f"Registro: {row.get('nombre_establecimiento', 'N/A')}"):
                st.write(f"**Nombre Establecimiento:** {row.get('nombre_establecimiento', 'N/A')}")
                st.write(f"**Razón Social:** {row.get('razon_social', 'N/A')}")
                st.write(f"**Fecha:** {row.get('Fecha', 'N/A')}")
                st.write(f"**Email:** {row.get('email', 'N/A')}")
                st.write(f"**Celular:** {row.get('celular', 'N/A')}")
                
                pdf_display = row.get('link_pdf', "No encontrado")
                col1, col2, col3 = st.columns(3)

                with col1:
                    if "Ver PDF" in pdf_display:
                        match = re.search(r'\((.*?)\)', pdf_display)
                        if match:
                            st.link_button("Ver PDF", match.group(1))
                    else:
                        st.write("PDF no encontrado.")
                
                with col2:
                    recipient_email = row.get('email')
                    if recipient_email: # Mostrar el botón si existe cualquier email
                        subject = f"Contacto desde Panel Caza para {row.get('nombre_establecimiento', '')}"
                        encoded_subject = urllib.parse.quote(subject)
                        encoded_to = urllib.parse.quote(recipient_email)
                        gmail_compose_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={encoded_to}&su={encoded_subject}&from=faunapescaycaza@gmail.com"
                        st.link_button("Enviar Email", gmail_compose_url)
                    else:
                        st.write("Email no disponible o no es Gmail.")
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        error_message = f"{timestamp} - Intento de enviar email a '{row.get('nombre_establecimiento', 'N/A')}' sin dirección de correo o no es Gmail."
                        try:
                            append_sheet_data(GOOGLE_ERROR_LOG_SHEET_ID, GOOGLE_ERROR_LOG_SHEET_NAME, [[error_message]])
                        except Exception as sheet_e:
                            st.warning(f"No se pudo registrar el aviso de email no disponible en Google Sheet: {sheet_e}")
                
                with col3:
                    if st.button("Enviar Pago", key=f"send_payment_{index}"):
                        try:
                            # Aquí iría la lógica de procesamiento de pagos
                            st.toast(f"Iniciando envío de pago para {row.get('nombre_establecimiento', '')}...")
                            # Simulación de un posible error
                            # raise ValueError("Error de prueba en el procesamiento de pago")
                        except Exception as e:
                            st.error(f"Error al procesar el pago: {e}")
                            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            error_message = f"{timestamp} - Error en pago para '{row.get('nombre_establecimiento', 'N/A')}': {e}"
                            try:
                                append_sheet_data(GOOGLE_ERROR_LOG_SHEET_ID, GOOGLE_ERROR_LOG_SHEET_NAME, [[error_message]])
                            except Exception as sheet_e:
                                st.warning(f"No se pudo registrar el error de pago en Google Sheet: {sheet_e}")

    elif st.session_state.filtered_df is not None:
        st.info("No se encontraron registros para mostrar. Presiona 'Recargar Datos' para intentar de nuevo.")

# --- Contenido de la pestaña 2 (placeholder) ---
with tab2:
    st.header("Aquí irá otro contenido en el futuro.")
    st.write("Esta es la segunda pestaña del menú superior.")

with tab3:
    st.header("Dashboard (próximamente)")
    st.write("Aquí irá el contenido del Dashboard.")


# --- Sección de Desarrollo al final de la página ---
st.markdown("---")
if st.button("Desarrollo"):
    st.session_state.show_dev_section_main = not st.session_state.show_dev_section_main

if st.session_state.show_dev_section_main:
    st.header("Sección de Desarrollo")
    
    password = st.text_input("Ingresa la contraseña:", type="password", key="dev_password_main")
    
    if password == "admin123":
        st.success("Acceso concedido.")
        
        st.subheader("Registro de Errores")
        if st.button("Ver/Actualizar Log de Errores", key="btn_ver_errores_main"):
            try:
                error_df = read_sheet_data(GOOGLE_ERROR_LOG_SHEET_ID, GOOGLE_ERROR_LOG_SHEET_NAME)
                if not error_df.empty:
                    st.dataframe(error_df)
                else:
                    st.info("No hay errores registrados.")
            except Exception as e:
                st.error(f"No se pudo cargar el registro de errores: {e}")

        st.subheader("Tabla de Precios")
        if st.button("Ver/Actualizar Precios", key="btn_ver_precios_main"):
            try:
                precios_df = read_sheet_data("1Hl99DUx5maPEHkC5JNJqq2SZLa8UgVQBJbeia5jk1VI", "precios")
                st.dataframe(precios_df)
            except Exception as e:
                st.error(f"No se pudo cargar la tabla de precios: {e}")
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                error_message = f"{timestamp} - Error al cargar precios (desde botón principal): {e}"
                try:
                    append_sheet_data(GOOGLE_ERROR_LOG_SHEET_ID, GOOGLE_ERROR_LOG_SHEET_NAME, [[error_message]])
                except Exception as sheet_e:
                    st.warning(f"No se pudo registrar el error en Google Sheet: {sheet_e}")
            
    elif password:
        st.error("Contraseña incorrecta.")