import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# 1. Instellingen
ROADMAP_FILE = "roadmap_stoom_dynamisch.csv"
START_JAAR = 2025
STREEFJAAR = 2035

st.set_page_config(page_title="Stoom Projecten Roadmap", layout="wide")
st.title("📉 Projectgebaseerde Roadmap: Stoomvrij 2035")

# 2. Data laden functie
def laad_data():
    if os.path.exists(ROADMAP_FILE):
        df = pd.read_csv(ROADMAP_FILE)
        ref = float(df['Ref_Verbruik'].iloc[0]) if 'Ref_Verbruik' in df.columns else 5000.0
        return df, ref
    else:
        # Start met één lege regel voor 2025
        df = pd.DataFrame({
            'Jaar': [2025], 
            'Besparing (Ton)': [0.0],
            'Project / Maatregel': ["Eerste project..."],
            'Ref_Verbruik': [5000.0]
        })
        return df, 5000.0

# 3. Initialisatie
if 'df_roadmap' not in st.session_state:
    df, ref = laad_data()
    st.session_state.df_roadmap = df
    st.session_state.ref_verbruik = ref

# 4. Sidebar
st.sidebar.header("⚙️ Basisinstellingen")
huidig_ref = st.sidebar.number_input("Huidig verbruik (Referentie 2024)", value=float(st.session_state.ref_verbruik), step=100.0)

# 5. Dynamische Tabel (Data Editor)
st.subheader("Voeg projecten toe per jaar")
st.info("Gebruik de tabel hieronder om projecten toe te voegen. Je kunt meerdere regels voor hetzelfde jaar maken.")

# Configuratie voor de kolommen
column_cfg = {
    "Jaar": st.column_config.SelectboxColumn("Jaar", options=list(range(2025, 2036)), width="small", required=True),
    "Besparing (Ton)": st.column_config.NumberColumn("Besparing (Ton)", min_value=0.0, format="%.1f", width="medium"),
    "Project / Maatregel": st.column_config.TextColumn("Project / Maatregel", width="large")
}

# De editor met 'num_rows="dynamic"' staat toe dat je regels toevoegt/verwijdert
edited_df = st.data_editor(
    st.session_state.df_roadmap[['Jaar', 'Besparing (Ton)', 'Project / Maatregel']],
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config=column_cfg,
    key="project_editor"
)

# 6. Opslaan
if st.sidebar.button("💾 Alles Opslaan"):
    finale_df = edited_df.copy()
    finale_df['Ref_Verbruik'] = huidig_ref
    finale_df.to_csv(ROADMAP_FILE, index=False)
    st.session_state.df_roadmap = finale_df
    st.session_state.ref_verbruik = huidig_ref
    st.sidebar.success("✅ Projecten opgeslagen!")
    st.rerun()

# 7. Berekening voor Grafiek (Groeperen per jaar)
# We tellen alle besparingen per jaar op om de lijn te tekenen
df_grouped = edited_df.groupby('Jaar')['Besparing (Ton)'].sum().reset_index()

# Zorg dat alle jaren tussen 2025 en 2035 aanwezig zijn in de plot
alle_jaren = pd.DataFrame({'Jaar': range(START_JAAR, STREEFJAAR + 1)})
df_plot = pd.merge(alle_jaren, df_grouped, on='Jaar', how='left').fillna(0)

# Bereken cumulatief restverbruik
df_plot['Restverbruik'] = huidig_ref - df_plot['Besparing (Ton)'].cumsum()
df_plot['Restverbruik'] = df_plot['Restverbruik'].clip(lower=0)

# Grafiek data inclusief startpunt 2024
jaren_v = [START_JAAR - 1] + df_plot['Jaar'].tolist()
verbruik_v = [huidig_ref] + df_plot['Restverbruik'].tolist()

fig = go.Figure()
fig.add_trace(go.Scatter(x=jaren_v, y=verbruik_v, mode='lines+markers', name='Prognose', line=dict(color='cyan', width=4), fill='tozeroy'))
fig.update_layout(title=f"Afbouwpad op basis van projecten (Start: {huidig_ref} Ton)", template="plotly_dark", xaxis=dict(tickmode='linear', dtick=1))
st.plotly_chart(fig, use_container_width=True)

# 8. Metrics
tot_besparing = edited_df['Besparing (Ton)'].sum()
st.metric("Totale projectbesparing", f"{round(tot_besparing, 1)} Ton", delta=f"{len(edited_df)} projecten")
