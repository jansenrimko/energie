import streamlit as st

import pandas as pd

import plotly.graph_objects as go

import sqlite3

import os

 

# =============================

# 1. INSTELLINGEN

# =============================

DB_FILE = "roadmap.db"

BACKUP_FILE = "roadmap_backup.csv"

START_JAAR = 2025

STREEFJAAR = 2035

 

st.set_page_config(page_title="Stoom Projecten Roadmap", layout="wide")

st.title("📉 Projectgebaseerde Roadmap: Stoomvrij 2035")

 

# =============================

# 2. DATABASE FUNCTIES

# =============================

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

        return (

            pd.DataFrame(

                {"Jaar": [START_JAAR],

                 "Besparing (Ton)": [0.0],

                 "Project / Maatregel": ["Eerste project..."]}

            ),

            5000.0

        )

 

    ref = float(df["ref_verbruik"].iloc[0])

    df = df.rename(columns={

        "jaar": "Jaar",

        "besparing": "Besparing (Ton)",

        "project": "Project / Maatregel"

    }).drop(columns=["ref_verbruik"])

 

    return df, ref

 

def opslaan_data(df, ref):

    conn = get_conn()

    c = conn.cursor()

    c.execute("DELETE FROM roadmap")

    for _, row in df.iterrows():

        c.execute(

            "INSERT INTO roadmap (jaar, besparing, project, ref_verbruik) VALUES (?, ?, ?, ?)",

            (int(row["Jaar"]),

             float(row["Besparing (Ton)"]),

             row["Project / Maatregel"],

             ref)

        )

    conn.commit()

    conn.close()

 

def maak_csv_backup(df, ref):

    backup = df.copy()

    backup["Ref_Verbruik"] = ref

    backup.to_csv(BACKUP_FILE, index=False)

 

# =============================

# 3. INITIALISATIE

# =============================

init_db()

if "df" not in st.session_state:

    df, ref = laad_data()

    st.session_state.df = df

    st.session_state.ref = ref

 

# =============================

# 4. SIDEBAR

# =============================

st.sidebar.header("⚙️ Basisinstellingen")

huidig_ref = st.sidebar.number_input(

    "Huidig verbruik (Referentie 2024)",

    value=float(st.session_state.ref),

    step=100.0

)

 

st.sidebar.divider()

st.sidebar.subheader("💾 Back-up")

 

if os.path.exists(BACKUP_FILE):

    with open(BACKUP_FILE, "rb") as f:

        st.sidebar.download_button(

            "⬇️ Download CSV-backup",

            f,

            file_name="roadmap_backup.csv",

            mime="text/csv"

        )

else:

    st.sidebar.caption("Nog geen backup beschikbaar")

 

# 👉 BACKUP HERSTELLEN

st.sidebar.divider()

st.sidebar.subheader("♻️ Backup terugzetten")

 

uploaded = st.sidebar.file_uploader("Upload CSV-backup", type="csv")

 

if uploaded is not None:

    if st.sidebar.button("⚠️ Herstel backup (overschrijft alles)"):

        restore_df = pd.read_csv(uploaded)

 

        if "Ref_Verbruik" not in restore_df.columns:

            st.sidebar.error("❌ Ongeldige backup")

        else:

            ref_restore = float(restore_df["Ref_Verbruik"].iloc[0])

            restore_df = restore_df.drop(columns=["Ref_Verbruik"])

 

            opslaan_data(restore_df, ref_restore)

            maak_csv_backup(restore_df, ref_restore)

 

            st.session_state.df = restore_df

            st.session_state.ref = ref_restore

 

            st.sidebar.success("✅ Backup hersteld")

            st.rerun()

 

# =============================

# 5. DATA EDITOR

# =============================

st.subheader("📋 Projecten")

 

edited_df = st.data_editor(

    st.session_state.df,

    num_rows="dynamic",

    hide_index=True,

    use_container_width=True,

    column_config={

        "Jaar": st.column_config.SelectboxColumn(

            "Jaar",

            options=list(range(START_JAAR, STREEFJAAR + 1)),

            required=True,

            width="small"

        ),

        "Besparing (Ton)": st.column_config.NumberColumn(

            "Besparing (Ton)", min_value=0.0, format="%.1f"

        ),

        "Project / Maatregel": st.column_config.TextColumn(width="large")

    }

)

 

# =============================

# 6. OPSLAAN

# =============================

if st.sidebar.button("💾 Alles opslaan"):

    opslaan_data(edited_df, huidig_ref)

    maak_csv_backup(edited_df, huidig_ref)

 

    st.session_state.df = edited_df

    st.session_state.ref = huidig_ref

 

    st.sidebar.success("✅ Opgeslagen + backup gemaakt")

    st.rerun()

 

# =============================

# 7. GRAFIEK

# =============================

df_grouped = edited_df.groupby("Jaar")["Besparing (Ton)"].sum().reset_index()

jaren = pd.DataFrame({"Jaar": range(START_JAAR, STREEFJAAR + 1)})

df_plot = jaren.merge(df_grouped, on="Jaar", how="left").fillna(0)

 

df_plot["Restverbruik"] = huidig_ref - df_plot["Besparing (Ton)"].cumsum()

df_plot["Restverbruik"] = df_plot["Restverbruik"].clip(lower=0)

 

fig = go.Figure()

fig.add_trace(go.Scatter(

    x=[START_JAAR - 1] + df_plot["Jaar"].tolist(),

    y=[huidig_ref] + df_plot["Restverbruik"].tolist(),

    mode="lines+markers",

    fill="tozeroy"

))

fig.update_layout(

    title="Afbouwpad stoomverbruik",

    xaxis=dict(tickmode="linear", dtick=1)

)

 

st.plotly_chart(fig, use_container_width=True)

 

# =============================

# 8. METRICS

# =============================

st.metric(

    "Totale projectbesparing",

    f"{edited_df['Besparing (Ton)'].sum():.1f} Ton",

    delta=f"{len(edited_df)} projecten"

)
