import streamlit as st
import pandas as pd
import altair as alt
import pydeck as pdk

# Funktion zum Laden und Vorbereiten der Daten
def load_data(uploaded_file_obj, specific_time_col_name):
    # ... (Funktion bleibt wie in der vorherigen Antwort)
    if uploaded_file_obj is None:
        return None, None, False 

    try:
        df = pd.read_csv(uploaded_file_obj)
        time_col_to_use = None
        scaled_to_seconds = False

        if specific_time_col_name in df.columns:
            time_col_to_use = specific_time_col_name
            df[time_col_to_use] = pd.to_numeric(df[time_col_to_use], errors='coerce')
            df.dropna(subset=[time_col_to_use], inplace=True)

            if not df.empty:
                df[time_col_to_use] = df[time_col_to_use] / 1000000.0 # Mikrosekunden -> Sekunden
                scaled_to_seconds = True
                st.sidebar.success(f"Zeitachse: '{time_col_to_use}' (in Sekunden) wird verwendet.")
            else:
                st.sidebar.warning(f"Zeitspalte '{time_col_to_use}' enthält nach Bereinigung keine gültigen Werte mehr.")
        else:
            st.sidebar.warning(f"Spalte '{specific_time_col_name}' nicht gefunden. Index ('Index_als_Zeit') als Zeitachse.")
            df['Index_als_Zeit'] = df.index # DataFrame-Index als Fallback
            time_col_to_use = 'Index_als_Zeit'
        
        if df.empty: 
            st.warning(f"Nach Verarbeitung der Zeitspalte ('{time_col_to_use}') keine gültigen Daten.")
            return None, None, False
            
        return df, time_col_to_use, scaled_to_seconds
        
    except Exception as e:
        st.error(f"Fehler beim Lesen/Verarbeiten der CSV: {e}")
        return None, None, False

# Hauptanwendung
st.set_page_config(layout="wide")
st.title("🚁 Detaillierte Drohnen-Flugdatenanalyse mit Karte")

preferred_time_column_name = "Clock:Tick#"
preferred_lat_column_name = "GPS:Lat"
preferred_lon_column_name = "GPS:Long"
preferred_yaw_column_name = "IMU_ATTI(1):yaw360:C"


st.sidebar.header("📂 Datei hochladen")
uploaded_file = st.sidebar.file_uploader("Wählen Sie eine CSV-Datei", type=["csv"])

df_original = None
time_col = None 
was_scaled_to_seconds = False

if uploaded_file is not None:
    st.sidebar.info(f"Datei '{uploaded_file.name}' wird verarbeitet...")
    df_original, time_col, was_scaled_to_seconds = load_data(uploaded_file, preferred_time_column_name)
else:
    st.info("ℹ️ Bitte laden Sie eine CSV-Datei über die Seitenleiste hoch.")
    st.sidebar.info(f"Erwartet CSV mit Zeit ('{preferred_time_column_name}' in µs), GPS- und optional Yaw-Spalten.")


if df_original is not None and time_col is not None:
    st.subheader(f"Vorschau Rohdaten aus '{uploaded_file.name}'")
    st.dataframe(df_original.head())

    time_unit_display = "Sekunden" if was_scaled_to_seconds else "Index"

    min_time_val_orig = df_original[time_col].min()
    max_time_val_orig = df_original[time_col].max()
    
    time_step = 1.0 
    is_effectively_integer = pd.api.types.is_integer_dtype(df_original[time_col]) and not was_scaled_to_seconds
    
    if is_effectively_integer: time_step = 1 
    elif max_time_val_orig > min_time_val_orig:
        time_step = (max_time_val_orig - min_time_val_orig) / 100
        if time_step <= 0: time_step = 0.001 if was_scaled_to_seconds else 1.0
    else: time_step = 0.01 if was_scaled_to_seconds else 1.0
    time_format = "%.0f" if is_effectively_integer else "%.3f"

    st.sidebar.subheader(f"⏱️ Zeitbereich einschränken ({time_unit_display})")
    start_time_main_filter = st.sidebar.number_input(
        f"Startzeit ({time_col} in {time_unit_display})",
        min_value=min_time_val_orig, max_value=max_time_val_orig, value=min_time_val_orig,
        step=time_step, format=time_format )
    end_time_main_filter = st.sidebar.number_input(
        f"Endzeit ({time_col} in {time_unit_display})",
        min_value=min_time_val_orig, max_value=max_time_val_orig, value=max_time_val_orig,
        step=time_step, format=time_format)

    if start_time_main_filter > end_time_main_filter:
        st.sidebar.error("Startzeit muss vor/gleich Endzeit liegen.")
        df_filtered_main = pd.DataFrame(columns=df_original.columns) 
    else:
        df_filtered_main = df_original[
            (df_original[time_col] >= start_time_main_filter) & 
            (df_original[time_col] <= end_time_main_filter)
        ].copy()

    if df_filtered_main.empty and not (start_time_main_filter > end_time_main_filter) :
        st.warning(f"Im Haupt-Zeitbereich keine Datenpunkte.")

    st.sidebar.header("⚙️ Parameter-Auswahl (Zeit-Plot)")
    available_plot_parameters = [col for col in df_filtered_main.columns if col not in [time_col, preferred_lat_column_name, preferred_lon_column_name, preferred_yaw_column_name]]
    
    if available_plot_parameters:
        selected_plot_parameters = st.sidebar.multiselect(
            "Parameter für Zeit-Plot:", options=available_plot_parameters,
            default=available_plot_parameters[:min(len(available_plot_parameters), 3)] )

        if selected_plot_parameters and not df_filtered_main.empty:
            st.subheader("📈 Zeitreihenanalyse der ausgewählten Parameter")
            # ... (Altair Plot Code - unverändert)
            plot_axis_title = f'Zeit ({time_col} in {time_unit_display})'
            tooltip_time_title = f'Zeit ({time_col} in {time_unit_display})'
            plot_df_long = df_filtered_main[[time_col] + selected_plot_parameters].melt(
                id_vars=[time_col], value_vars=selected_plot_parameters,
                var_name='Parameter', value_name='Wert'
            )
            chart = alt.Chart(plot_df_long).mark_line().encode(
                x=alt.X(field=time_col, type='quantitative', title=plot_axis_title, axis=alt.Axis(format='~s')),
                y=alt.Y('Wert:Q', title='Wert'), color='Parameter:N',
                tooltip=[alt.Tooltip(field=time_col, type='quantitative', title=tooltip_time_title, format=".3f"), 
                         alt.Tooltip('Parameter:N', title='Parameter'), alt.Tooltip('Wert:Q', title='Wert', format=".3f")]
            ).interactive()
            st.altair_chart(chart, use_container_width=True)

        elif not df_filtered_main.empty:
            st.info("Bitte Parameter für den Zeit-Plot auswählen.")

    # --- Kartenvisualisierung ---
    st.sidebar.subheader("🗺️ Karten-Parameter (GPS & Ausrichtung)")
    all_available_cols = list(df_original.columns)
    map_gps_yaw_columns = [col for col in all_available_cols if col != time_col] 

    default_lat_idx = map_gps_yaw_columns.index(preferred_lat_column_name) if preferred_lat_column_name in map_gps_yaw_columns else (0 if map_gps_yaw_columns else None)
    default_lon_idx = map_gps_yaw_columns.index(preferred_lon_column_name) if preferred_lon_column_name in map_gps_yaw_columns else (1 if len(map_gps_yaw_columns) > 1 else None)
    # Für Yaw None als Option hinzufügen, um es optional zu machen
    yaw_options = [None] + map_gps_yaw_columns
    default_yaw_idx = yaw_options.index(preferred_yaw_column_name) if preferred_yaw_column_name in yaw_options else 0


    lat_col_orig_name = st.sidebar.selectbox("Breitengrad-Spalte (Latitude):", options=map_gps_yaw_columns, index=default_lat_idx, key="lat_col_sel")
    lon_col_orig_name = st.sidebar.selectbox("Längengrad-Spalte (Longitude):", options=map_gps_yaw_columns, index=default_lon_idx, key="lon_col_sel")
    yaw_col_orig_name = st.sidebar.selectbox("Ausrichtungs-Spalte (Yaw 0-360°):", options=yaw_options, index=default_yaw_idx, key="yaw_col_sel")


    if lat_col_orig_name and lon_col_orig_name and lat_col_orig_name != lon_col_orig_name:
        cols_for_map_raw = [time_col, lat_col_orig_name, lon_col_orig_name]
        if yaw_col_orig_name:
            cols_for_map_raw.append(yaw_col_orig_name)
        
        map_df_raw = df_filtered_main[list(set(cols_for_map_raw))].copy() # list(set(...)) um Duplikate zu vermeiden, falls time_col etc. auch GPS-Spalten sind
        map_df_raw[lat_col_orig_name] = pd.to_numeric(map_df_raw[lat_col_orig_name], errors='coerce')
        map_df_raw[lon_col_orig_name] = pd.to_numeric(map_df_raw[lon_col_orig_name], errors='coerce')
        map_df_raw.dropna(subset=[lat_col_orig_name, lon_col_orig_name], inplace=True)

        if yaw_col_orig_name:
            map_df_raw[yaw_col_orig_name] = pd.to_numeric(map_df_raw[yaw_col_orig_name], errors='coerce')
            # NaNs in Yaw nicht unbedingt droppen, Pfeil wird dann halt nicht gezeichnet oder mit Standardwinkel

        pydeck_col_lat = "latitude"
        pydeck_col_lon = "longitude"
        pydeck_col_time = "time"
        pydeck_col_yaw = "yaw"

        rename_dict = {
            lat_col_orig_name: pydeck_col_lat,
            lon_col_orig_name: pydeck_col_lon,
            time_col: pydeck_col_time 
        }
        if yaw_col_orig_name:
            rename_dict[yaw_col_orig_name] = pydeck_col_yaw
        
        map_df_for_pydeck = map_df_raw.rename(columns=rename_dict)

        if not map_df_for_pydeck.empty and pydeck_col_lat in map_df_for_pydeck and pydeck_col_lon in map_df_for_pydeck:
            st.subheader("🛰️ Drohnen-Flugroute und Position")

            min_map_time = map_df_for_pydeck[pydeck_col_time].min()
            max_map_time = map_df_for_pydeck[pydeck_col_time].max()
            
            map_slider_step = time_step 
            if was_scaled_to_seconds and (max_map_time - min_map_time) > 0:
                 map_slider_step = (max_map_time - min_map_time) / 200 
                 if map_slider_step <=0: map_slider_step = 0.001
            elif not was_scaled_to_seconds: map_slider_step = 1

            selected_map_time = st.slider(
                f"Zeitpunkt auf Karte auswählen ({time_unit_display}):",
                min_value=min_map_time, max_value=max_map_time,
                value=min_map_time, step=map_slider_step, format=time_format, key="map_time_slider" )

            current_pos_on_map_df = map_df_for_pydeck.iloc[(map_df_for_pydeck[pydeck_col_time] - selected_map_time).abs().argsort()[:1]].copy() # .copy() to avoid SettingWithCopyWarning

            # Initialer View auf den ersten Punkt der Route oder den aktuell ausgewählten Punkt
            focus_lat = current_pos_on_map_df[pydeck_col_lat].iloc[0] if not current_pos_on_map_df.empty else map_df_for_pydeck[pydeck_col_lat].iloc[0]
            focus_lon = current_pos_on_map_df[pydeck_col_lon].iloc[0] if not current_pos_on_map_df.empty else map_df_for_pydeck[pydeck_col_lon].iloc[0]

            initial_view_state = pdk.ViewState(
                latitude=focus_lat, longitude=focus_lon,
                zoom=18, # Stark erhöhter Zoom für ca. 100m Ansicht (experimentell)
                pitch=45, bearing=0 )
            
            path_layer_data = pd.DataFrame({'path_coordinates': [map_df_for_pydeck[[pydeck_col_lon, pydeck_col_lat]].values.tolist()]})
            path_layer = pdk.Layer(
                'PathLayer', data=path_layer_data, get_path='path_coordinates',
                get_width=0.5, # Feinere Routendarstellung
                get_color=[255, 0, 0, 180], pickable=True, width_min_pixels=1 )
            
            layers_to_render = [path_layer]

            if not current_pos_on_map_df.empty:
                point_layer = pdk.Layer(
                    'ScatterplotLayer', data=current_pos_on_map_df,
                    get_position=f'[{pydeck_col_lon}, {pydeck_col_lat}]',
                    get_color=[0, 255, 0, 255], get_radius=3, # Radius kleiner für Zoom
                    pickable=True, radius_min_pixels=4, radius_max_pixels=8)
                layers_to_render.append(point_layer)

                # Ausrichtungs-Pfeil (Yaw) hinzufügen, wenn Yaw-Daten vorhanden sind
                if yaw_col_orig_name and pydeck_col_yaw in current_pos_on_map_df.columns and not current_pos_on_map_df[pydeck_col_yaw].isnull().all():
                    # Pydeck Winkel: 0° = Ost (Rechts), positiv = gegen UZS. Yaw: 0° = Nord, positiv = UZS.
                    # Pydeck Angle = 90 - Yaw (damit 0° Yaw nach oben zeigt)
                    current_pos_on_map_df['pydeck_angle'] = 90 - current_pos_on_map_df[pydeck_col_yaw]
                    
                    orientation_layer = pdk.Layer(
                        'TextLayer',
                        data=current_pos_on_map_df,
                        get_position=f'[{pydeck_col_lon}, {pydeck_col_lat}]',
                        text='▲',  # Pfeil-Zeichen (ggf. '▲' oder '▶' testen)
                        get_size=500, # Größe des Pfeils anpassen
                        get_color=[255, 0, 0, 255], # Rot für gute Sichtbarkeit
                        get_angle='pydeck_angle', # Spalte mit dem berechneten Winkel
                        font_family="sans-serif", # Generische Schriftart
                        font_weight=700,
                        billboard=True # Pfeil richtet sich zur Kamera aus, bleibt aber auf der Karte rotiert
                    )
                    layers_to_render.append(orientation_layer)
            
            tooltip_items = {
                "Zeit": f"{{{pydeck_col_time}:.2f}} {time_unit_display}",
                "Lat": f"{{{pydeck_col_lat}}}",
                "Lon": f"{{{pydeck_col_lon}}}"
            }
            if yaw_col_orig_name and pydeck_col_yaw in current_pos_on_map_df.columns:
                 tooltip_items["Yaw"] = f"{{{pydeck_col_yaw}:.1f}}°"
            
            tooltip_html_parts = [f"<b>{key}:</b> {value}" for key, value in tooltip_items.items()]
            tooltip_config = {"html": "<br/>".join(tooltip_html_parts)}


            st.pydeck_chart(pdk.Deck(
                layers=layers_to_render, initial_view_state=initial_view_state,
                map_style='mapbox://styles/mapbox/satellite-streets-v11', tooltip=tooltip_config ))
            st.caption("Karte zoomt auf ersten Punkt der Auswahl. Satellitenkarten (Mapbox) benötigen ggf. MAPBOX_API_KEY.")

        elif lat_col_orig_name and lon_col_orig_name:
            st.warning("Keine GPS-Daten im ausgewählten Zeitbereich oder nach Bereinigung vorhanden für Karte.")
    elif uploaded_file: 
        st.info("Bitte gültige Lat/Lon-Spalten auswählen für Karte.")

else: 
    if uploaded_file is not None and (df_original is None or time_col is None) :
         st.warning("⚠️ Daten konnten nicht korrekt geladen werden.")

st.sidebar.markdown("---")
st.sidebar.info("App zur Analyse von CSV-Zeitreihendaten mit Kartenvisualisierung.")