import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import time

# Pagina-instellingen
st.set_page_config(page_title="Live LBK Dashboard", layout="wide")

# Functie om data vers uit de DB te halen
def get_data():
    # 'check_same_thread=False' is nodig omdat Streamlit met threads werkt
    conn = sqlite3.connect("mijn_metingen.db", check_same_thread=False)
    query = "SELECT timestamp, punt_naam, waarde FROM metingen"
    df = pd.read_sql_query(query, conn)
    conn.close()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

st.title("🌡️ Live Temperatuur Dashboard")

# Maak een plekje in het dashboard dat we telkens leegmaken en vullen
placeholder = st.empty()

# De "Live" loop
while True:
    with placeholder.container():
        try:
            df = get_data()

            if df.empty:
                st.warning("Wachten op data uit logger script...")
            else:
                # Actuele waarden tonen
                cols = st.columns(2)
                for i, sensor in enumerate(["B_01'Plt'T", "B_01'Plt'T(1)"]):
                    # Pak de allerlaatste meting voor deze sensor
                    sensor_data = df[df['punt_naam'] == sensor]
                    if not sensor_data.empty:
                        laatste = sensor_data.iloc[-1]
                        cols[i].metric(label=sensor, value=f"{laatste['waarde']:.2f} °C")

                # Grafiek (toon laatste 100 metingen voor de snelheid)
                st.subheader("Temperatuurverloop (laatste metingen)")
                fig = px.line(df.tail(200), x="timestamp", y="waarde", color="punt_naam",
                              template="plotly_dark",
                              labels={"waarde": "Temp °C", "timestamp": "Tijd"})
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.caption(f"Laatste update: {pd.Timestamp.now().strftime('%H:%M:%S')}")

        except Exception as e:
            st.error(f"Fout bij inlezen: {e}")

        # Wacht 5 seconden voor de volgende verversing
        time.sleep(5)
        st.rerun()
