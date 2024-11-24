import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time

# Configuración de la página
st.set_page_config(page_title="Gestión de Parkings", layout="wide")

# Variables de la API
API_BASE_URL = "http://172.25.2.116:80"

# Funciones para obtener datos de la API
def get_parkings():
    response = requests.get(f"{API_BASE_URL}/list_parkings")
    return response.json()

def get_parking_info(parking_id):
    response = requests.get(f"{API_BASE_URL}/parking/{parking_id}")
    return response.json()

def get_parking_historic(parking_id):
    response = requests.get(f"{API_BASE_URL}/historic/{parking_id}")
    return response.json()

# Inicializar estado de la aplicación si no existe
if 'update_counter' not in st.session_state:
    st.session_state.update_counter = 0

# Título principal
st.title("Sistema de Gestión de Parkings")

# Sidebar para selección de parking
st.sidebar.header("Selección de Parking")

# Obtener lista de parkings
parkings = get_parkings()
parking_names = {p["parking_id"]: p["name"] for p in parkings}
selected_parking = st.sidebar.selectbox(
    "Escoge un parking",
    options=list(parking_names.keys()),
    format_func=lambda x: parking_names[x],
    key='parking_selector'
)

if selected_parking:
    # Contenedor para datos en tiempo real
    real_time_container = st.empty()
    stats_container = st.empty()

    # Función para actualizar datos en tiempo real
    def update_real_time_data():
        parking_info = get_parking_info(selected_parking)
        
        with real_time_container.container():
            st.header(f"Parking: {parking_info['name']}")
            
            # Crear un medidor visual de ocupación
            progress = parking_info['occupied_spots'] / parking_info['max_spots']
            st.progress(progress)
            
            # Mostrar estadísticas actuales
            st.metric(
                "Plazas Ocupadas",
                f"{parking_info['occupied_spots']}/{parking_info['max_spots']}",
                f"Disponibles: {parking_info['max_spots'] - parking_info['occupied_spots']}"
            )
            
            # Mostrar mapa
            df_map = pd.DataFrame([{"name": parking_info['name'], "latitude": float(parking_info['coordinates'].split(",")[0]), "longitude": float(parking_info['coordinates'].split(",")[1])}])
            st.map(data=df_map, latitude='latitude', longitude='longitude')
            st.text(f"Coordenadas: {parking_info['coordinates']}")
            
        return parking_info

    # Función para actualizar estadísticas
    def update_stats(parking_info):
        with stats_container.container():
            st.header("Estadísticas Históricas")
            
            # Obtener datos históricos
            historic_data = get_parking_historic(selected_parking)
            df_historic = pd.DataFrame(historic_data['history'])
            
            # Convertir la columna 'hour' a datetime
            df_historic['hour'] = pd.to_datetime(df_historic['hour'])
            
            # Filtros de fecha
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Fecha inicial",
                    value=min(df_historic['hour']).date(),
                    key=f'start_date_{st.session_state.update_counter}'
                )
            with col2:
                end_date = st.date_input(
                    "Fecha final",
                    value=max(df_historic['hour']).date(),
                    key=f'end_date_{st.session_state.update_counter}'
                )
            
            # Filtrar datos según el rango seleccionado
            mask = (df_historic['hour'].dt.date >= start_date) & (df_historic['hour'].dt.date <= end_date)
            filtered_df = df_historic.loc[mask]
            
            if not filtered_df.empty:
                fig = px.line(
                    filtered_df,
                    x='hour',
                    y='occupied_spots',
                    title=f'Ocupación del Parking "{parking_info["name"]}" a lo largo del tiempo'
                )
                
                fig.update_layout(
                    xaxis_title="Fecha y Hora",
                    yaxis_title="Plazas Ocupadas",
                    hovermode='x'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Estadísticas adicionales
                st.subheader("Resumen Estadístico")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Ocupación Media", 
                             f"{filtered_df['occupied_spots'].mean():.1f}")
                with col2:
                    st.metric("Ocupación Máxima", 
                             filtered_df['occupied_spots'].max())
                with col3:
                    st.metric("Ocupación Mínima", 
                             filtered_df['occupied_spots'].min())
            else:
                st.warning("No hay datos disponibles para el rango de fechas seleccionado.")

    # Actualización automática usando st.empty()
    while True:
        parking_info = update_real_time_data()
        
        # Actualizar estadísticas solo cada minuto (cada 20 actualizaciones)
        if st.session_state.update_counter % 20 == 0:
            update_stats(parking_info)
        
        st.session_state.update_counter += 1
        time.sleep(3)
        
else:
    st.info("Por favor, selecciona un parking en el menú lateral para ver sus detalles.")

