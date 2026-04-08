import streamlit as st

import pandas as pd

import plotly.graph_objects as go

import sqlite3

 

# -----------------------------

# 1. Instellingen

# -----------------------------

DB_FILE = "roadmap.db"

START_JAAR = 2025

STREEFJAAR = 2035

 

st.set_page_config(page_title="Stoom Projecten Roadmap", layout="wide")

st.title("📉 Projectgebaseerde Roadmap: Stoomvrij 2035")

 

# -----------------------------

# 2. Database helpers

# -----------------------------

def get_conn():

    return sqlite3.connect(DB_FILE, check_same_thread=False)

 

def init_db():

    conn = get_conn()

    c = conn.cursor()

    c.execute("""

    CREATE TABLE IF NOT EXISTS roadmap (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        jaar INTEGER,

        besparing REAL,

        project TEXT,

        ref_verbruik REAL

    )

    """)

    conn.commit()

    conn.close()

 

def laad_data():

    conn = get_conn()

    df = pd.read_sql("SELECT jaar, besparing, project, ref_verbruik FROM roadmap", conn)

    conn.close()

 

    if df.empty:

        # startdata

        df = pd.DataFrame({

            "Jaar": [2025],

            "Besparing (Ton)": [0.0],

            "Project / Maatregel": ["Eerste project..."],

            "Ref_Verbruik": [5000.0]

        })

        ref = 5000.0

    else:

        df = df.rename(columns={

            "jaar": "Jaar",

            "besparing": "Besparing (Ton)",

            "project": "Project / Maatregel"

        })

        ref = float(df["ref_verbruik"].iloc[0])

        df = df.drop(columns=["ref_verbruik"])

 

    return df, ref

 

def opslaan_data(df, ref):

    conn = get_conn()

    c = conn.cursor()

 

    # Alles resetten (gedeelde tabel)

    c.execute("DELETE FROM roadmap")

 

    for _, row in df.iterrows():

        c.execute(

            "INSERT INTO roadmap (jaar, besparing, project, ref_verbruik) VALUES (?, ?, ?, ?)",

            (int(row["Jaar"]), float(row["Besparing (Ton)"]), row["Project / Maatregel"], ref)

        )

 

    conn.commit()

    conn.close()

 

# -----------------------------

# 3. Init

# -----------------------------

init_db()

 

if "df_roadmap" not in st.session_state:

    df, ref = laad_data()

    st.session_state.df_roadmap = df

    st.session_state.ref_verbruik = ref

 

# -----------------------------

# 4. Sidebar

# -----------------------------

st.sidebar.header("⚙️ Basisinstellingen")

huidig_ref = st.sidebar.number_input(

    "Huidig verbruik (Referentie 2024)",

    value=float(st.session_state.ref_verbruik),

    step=100.0

)

 

# -----------------------------

# 5. Data editor

# -----------------------------

st.subheader("Voeg projecten toe per jaar")

st.info("Gebruik de tabel hieronder om projecten toe te voegen. Je kunt meerdere regels voor hetzelfde jaar maken.")

 

column_cfg = {

    "Jaar": st.column_config.SelectboxColumn(

        "Jaar",

        options=list(range(START_JAAR, STREEFJAAR + 1)),

        width="small",

        required=True

    ),

    "Besparing (Ton)": st.column_config.NumberColumn(

        "Besparing (Ton)",

        min_value=0.0,

        format="%.1f"

    ),

    "Project / Maatregel": st.column_config.TextColumn(

        "Project / Maatregel",

        width="large"

    )

}

 

edited_df = st.data_editor(

    st.session_state.df_roadmap,

    num_rows="dynamic",

    hide_index=True,

    use_container_width=True,

    column_config=column_cfg,

    key="project_editor"

)

 

# -----------------------------

# 6. Opslaan (SQLite)

# -----------------------------

if st.sidebar.button("💾 Alles Opslaan"):

    opslaan_data(edited_df, huidig_ref)

    st.session_state.df_roadmap = edited_df

    st.session_state.ref_verbruik = huidig_ref

    st.sidebar.success("✅ Opgeslagen in SQLite")

    st.rerun()

 

# -----------------------------

# 7. Berekeningen grafiek

# -----------------------------

df_grouped = edited_df.groupby("Jaar")["Besparing (Ton)"].sum().reset_index()

 

alle_jaren = pd.DataFrame({"Jaar": range(START_JAAR, STREEFJAAR + 1)})

df_plot = pd.merge(alle_jaren, df_grouped, on="Jaar", how="left").fillna(0)

 

df_plot["Restverbruik"] = huidig_ref - df_plot["Besparing (Ton)"].cumsum()

df_plot["Restverbruik"] = df_plot["Restverbruik"].clip(lower=0)

 

jaren_v = [START_JAAR - 1] + df_plot["Jaar"].tolist()

verbruik_v = [huidig_ref] + df_plot["Restverbruik"].tolist()

 

fig = go.Figure()

fig.add_trace(go.Scatter(

    x=jaren_v,

    y=verbruik_v,

    mode="lines+markers",

    name="Prognose",

    fill="tozeroy"

))

fig.update_layout(

    title=f"Afbouwpad op basis van projecten (Start: {huidig_ref} Ton)",

    xaxis=dict(tickmode="linear", dtick=1)

)

 

st.plotly_chart(fig, use_container_width=True)

 

# -----------------------------

# 8. Metrics

# -----------------------------

tot_besparing = edited_df["Besparing (Ton)"].sum()

st.metric(

    "Totale projectbesparing",

    f"{round(tot_besparing, 1)} Ton",

    delta=f"{len(edited_df)} projecten"

)
