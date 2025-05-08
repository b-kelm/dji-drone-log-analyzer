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
st.title("🚁 Detaillierte Drohnen-Flugdatenanalyse mit Karte & Multi-Plots")

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
        step=time_step, format=time_format, key="start_time_filter" )
    end_time_main_filter = st.sidebar.number_input(
        f"Endzeit ({time_col} in {time_unit_display})",
        min_value=min_time_val_orig, max_value=max_time_val_orig, value=max_time_val_orig,
        step=time_step, format=time_format, key="end_time_filter")

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

    # --- NEU: Konfiguration für mehrere Zeit-Plots ---
    st.sidebar.header("📈 Zeit-Plot Konfigurationen")
    plot_configurations = []
    available_plot_parameters = []

    if not df_filtered_main.empty:
        # Parameter, die für allgemeine Zeit-Plots verfügbar sind (alle außer der Zeitspalte selbst)
        # GPS/Yaw Spalten werden hier NICHT explizit ausgeschlossen, Nutzer kann sie bei Bedarf plotten.
        available_plot_parameters = [col for col in df_filtered_main.columns if col != time_col]

    if available_plot_parameters:
        num_configurable_plots = 3 # Anzahl der erlaubten Plots
        for i in range(num_configurable_plots):
            with st.sidebar.expander(f"Zeit-Plot {i+1} Parameter", expanded=(i==0)): # Ersten Plot standardmäßig ausklappen
                # Sicherstellen, dass default eine Liste ist, auch wenn available_plot_parameters leer ist
                default_params_for_plot = []
                if i == 0 and available_plot_parameters: # Nur für ersten Plot Standardwerte, falls Parameter da sind
                    default_params_for_plot = available_plot_parameters[:min(len(available_plot_parameters), 1)]
                
                selected_params = st.multiselect(
                    f"Parameter für Plot {i+1}:",
                    options=available_plot_parameters,
                    default=default_params_for_plot,
                    key=f"plot_params_select_{i}" # Eindeutiger Key
                )
                if selected_params: 
                    plot_configurations.append({
                        "plot_id": i+1,
                        "title": f"Zeit-Plot {i+1}: {', '.join(selected_params)}", 
                        "params": selected_params
                    })
    elif df_original is not None and time_col is not None: 
        st.sidebar.info("Keine Parameter für Zeit-Plots verfügbar (möglicherweise ist der gewählte Zeitbereich leer).")

    # --- Hauptbereich: Anzeige der konfigurierten Zeit-Plots ---
    if not df_filtered_main.empty and plot_configurations:
        st.markdown("---") # Trennlinie vor den Plots
        st.subheader("📊 Zeitreihenanalysen")
        for config in plot_configurations:
            selected_plot_parameters = config["params"]
            plot_title_display = config["title"] # Verwende den generierten Titel
            
            st.markdown(f"#### {plot_title_display}")

            plot_df_long = df_filtered_main[[time_col] + selected_plot_parameters].melt(
                id_vars=[time_col], value_vars=selected_plot_parameters,
                var_name='Parameter', value_name='Wert'
            )
            
            plot_axis_title_x = f'Zeit ({time_col} in {time_unit_display})'
            tooltip_time_title_x = f'Zeit ({time_col} in {time_unit_display})'

            try:
                chart = alt.Chart(plot_df_long).mark_line().encode(
                    x=alt.X(field=time_col, type='quantitative', title=plot_axis_title_x, axis=alt.Axis(format='~s')),
                    y=alt.Y('Wert:Q', title='Wert'), 
                    color='Parameter:N', # Farbe nach Parameter unterscheiden
                    tooltip=[alt.Tooltip(field=time_col, type='quantitative', title=tooltip_time_title_x, format=".3f"), 
                             alt.Tooltip('Parameter:N', title='Parameter'), 
                             alt.Tooltip('Wert:Q', title='Wert', format=".3f")]
                ).interactive()
                st.altair_chart(chart, use_container_width=True)
            except Exception as e:
                st.error(f"Fehler beim Erstellen von Plot {config['plot_id']}: {e}")
            st.markdown("---") # Trennlinie nach jedem Plot
            
    elif not df_filtered_main.empty and available_plot_parameters:
        st.info("Bitte wählen Sie Parameter für mindestens einen Zeit-Plot in der Seitenleiste aus, um Diagramme anzuzeigen.")


    # --- Kartenvisualisierung (wie zuvor, aber nach den Zeit-Plots) ---
    st.sidebar.subheader("🗺️ Karten-Parameter (GPS & Ausrichtung)")
    all_available_cols = list(df_original.columns) # df_original für volle Spaltenliste
    map_gps_yaw_columns = [col for col in all_available_cols if col != time_col] 

    default_lat_idx = map_gps_yaw_columns.index(preferred_lat_column_name) if preferred_lat_column_name in map_gps_yaw_columns else (0 if map_gps_yaw_columns else None)
    default_lon_idx = map_gps_yaw_columns.index(preferred_lon_column_name) if preferred_lon_column_name in map_gps_yaw_columns else (1 if len(map_gps_yaw_columns) > 1 else None)
    yaw_options = [None] + map_gps_yaw_columns
    default_yaw_idx = yaw_options.index(preferred_yaw_column_name) if preferred_yaw_column_name in yaw_options else 0

    lat_col_orig_name = st.sidebar.selectbox("Breitengrad-Spalte (Latitude):", options=map_gps_yaw_columns, index=default_lat_idx, key="lat_col_sel_v3")
    lon_col_orig_name = st.sidebar.selectbox("Längengrad-Spalte (Longitude):", options=map_gps_yaw_columns, index=default_lon_idx, key="lon_col_sel_v3")
    yaw_col_orig_name = st.sidebar.selectbox("Ausrichtungs-Spalte (Yaw 0-360°):", options=yaw_options, index=default_yaw_idx, key="yaw_col_sel_v3")

    if lat_col_orig_name and lon_col_orig_name and lat_col_orig_name != lon_col_orig_name:
        # Verwende df_filtered_main für Kartendaten, um den globalen Zeitfilter zu respektieren
        cols_for_map_raw = [time_col, lat_col_orig_name, lon_col_orig_name]
        if yaw_col_orig_name and yaw_col_orig_name in df_filtered_main.columns :
            cols_for_map_raw.append(yaw_col_orig_name)
        
        cols_for_map_raw = [col for col in cols_for_map_raw if col in df_filtered_main.columns] # Nur existierende Spalten
        
        if not cols_for_map_raw or time_col not in cols_for_map_raw or lat_col_orig_name not in cols_for_map_raw or lon_col_orig_name not in cols_for_map_raw:
            st.warning("Benötigte Spalten (Zeit, Lat, Lon) nicht im gefilterten Datensatz für die Karte vorhanden.")
        else:
            map_df_raw = df_filtered_main[list(set(cols_for_map_raw))].copy()
            map_df_raw[lat_col_orig_name] = pd.to_numeric(map_df_raw[lat_col_orig_name], errors='coerce')
            map_df_raw[lon_col_orig_name] = pd.to_numeric(map_df_raw[lon_col_orig_name], errors='coerce')
            map_df_raw.dropna(subset=[lat_col_orig_name, lon_col_orig_name], inplace=True)

            if yaw_col_orig_name and yaw_col_orig_name in map_df_raw.columns:
                map_df_raw[yaw_col_orig_name] = pd.to_numeric(map_df_raw[yaw_col_orig_name], errors='coerce')

            pydeck_col_lat = "latitude"
            pydeck_col_lon = "longitude"
            pydeck_col_time = "time"
            pydeck_col_yaw = "yaw"

            rename_dict = { lat_col_orig_name: pydeck_col_lat, lon_col_orig_name: pydeck_col_lon, time_col: pydeck_col_time }
            if yaw_col_orig_name and yaw_col_orig_name in map_df_raw.columns:
                rename_dict[yaw_col_orig_name] = pydeck_col_yaw
            
            map_df_for_pydeck = map_df_raw.rename(columns=rename_dict)

            if not map_df_for_pydeck.empty and pydeck_col_lat in map_df_for_pydeck and pydeck_col_lon in map_df_for_pydeck:
                st.markdown("---") # Trennlinie vor der Karte
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
                    value=min_map_time, step=map_slider_step, format=time_format, key="map_time_slider_v3" )

                current_pos_on_map_df = map_df_for_pydeck.iloc[(map_df_for_pydeck[pydeck_col_time] - selected_map_time).abs().argsort()[:1]].copy()

                if not current_pos_on_map_df.empty:
                    focus_lat = current_pos_on_map_df[pydeck_col_lat].iloc[0]
                    focus_lon = current_pos_on_map_df[pydeck_col_lon].iloc[0]
                elif not map_df_for_pydeck.empty: 
                    focus_lat = map_df_for_pydeck[pydeck_col_lat].iloc[0]
                    focus_lon = map_df_for_pydeck[pydeck_col_lon].iloc[0]
                else: 
                    focus_lat = 0 
                    focus_lon = 0

                initial_view_state = pdk.ViewState(
                    latitude=focus_lat, longitude=focus_lon,
                    zoom=18, pitch=45, bearing=0 )
                
                path_layer_data = pd.DataFrame({'path_coordinates': [map_df_for_pydeck[[pydeck_col_lon, pydeck_col_lat]].values.tolist()]})
                path_layer = pdk.Layer(
                    'PathLayer', data=path_layer_data, get_path='path_coordinates',
                    get_width=1.5, get_color=[255, 0, 0, 180], pickable=True, width_min_pixels=1 )
                
                layers_to_render = [path_layer]

                if not current_pos_on_map_df.empty:
                    point_layer = pdk.Layer(
                        'ScatterplotLayer', data=current_pos_on_map_df,
                        get_position=f'[{pydeck_col_lon}, {pydeck_col_lat}]',
                        get_color=[0, 255, 0, 255], get_radius=4, 
                        pickable=True, radius_min_pixels=3, radius_max_pixels=8)
                    layers_to_render.append(point_layer)

                    if yaw_col_orig_name and pydeck_col_yaw in current_pos_on_map_df.columns and \
                       pd.notna(current_pos_on_map_df[pydeck_col_yaw].iloc[0]):
                        current_pos_on_map_df.loc[:, 'pydeck_angle'] = 90 - current_pos_on_map_df[pydeck_col_yaw]
                        orientation_layer = pdk.Layer(
                            'TextLayer', data=current_pos_on_map_df, 
                            get_position=f'[{pydeck_col_lon}, {pydeck_col_lat}]',
                            get_text="'^'", get_size=45, get_color=[255, 0, 255, 255], 
                            get_angle='pydeck_angle', font_family="Arial, sans-serif", 
                            font_weight=700, billboard=True )
                        layers_to_render.append(orientation_layer)
                
                tooltip_items = { "Zeit": f"{{{pydeck_col_time}:.2f}} {time_unit_display}", "Lat": f"{{{pydeck_col_lat}}}", "Lon": f"{{{pydeck_col_lon}}}"}
                if yaw_col_orig_name and pydeck_col_yaw in current_pos_on_map_df.columns and \
                   (not current_pos_on_map_df.empty and pd.notna(current_pos_on_map_df[pydeck_col_yaw].iloc[0])):
                     tooltip_items["Yaw"] = f"{{{pydeck_col_yaw}:.1f}}°"
                tooltip_html_parts = [f"<b>{key}:</b> {value}" for key, value in tooltip_items.items()]
                tooltip_config = {"html": "<br/>".join(tooltip_html_parts)}

                st.pydeck_chart(pdk.Deck(
                    layers=layers_to_render, initial_view_state=initial_view_state,
                    map_style='mapbox://styles/mapbox/satellite-streets-v11', tooltip=tooltip_config ))
                st.caption("Karte zoomt auf ersten Punkt der Auswahl. Satellitenkarten (Mapbox) benötigen ggf. MAPBOX_API_KEY.")

            elif lat_col_orig_name and lon_col_orig_name : 
                st.warning("Keine GPS-Daten im ausgewählten Zeitbereich oder nach Bereinigung vorhanden für Karte.")
    elif uploaded_file: 
        st.info("Bitte gültige Lat/Lon-Spalten auswählen für Karte.")

else: 
    if uploaded_file is not None and (df_original is None or time_col is None) :
         st.warning("⚠️ Daten konnten nicht korrekt geladen werden.")

st.sidebar.markdown("---")
st.sidebar.info("App zur Analyse von CSV-Zeitreihendaten mit Kartenvisualisierung und Multi-Plots.")