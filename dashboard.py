# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import json
import os
import requests
import zipfile
import io
from datetime import datetime
import pytz
from dotenv import load_dotenv
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
from gtfs_utils import GTFSLoader

# Charger les variables d'environnement (Local: .env / Cloud: Secrets)
load_dotenv()

st.set_page_config(page_title="GTFS-RT Alerts QA Dashboard", layout="wide")

# --- INITIALISATION DU LOADER ---
# On crée un dossier temporaire pour l'upload sur le Cloud
UPLOAD_DIR = "gtfs_static"
os.makedirs(UPLOAD_DIR, exist_ok=True)

loader = GTFSLoader(UPLOAD_DIR)
is_gtfs_ready = loader.load()

# --- CONFIGURATION DES RÉPERTOIRES ---
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

st.title("🚦 GTFS-RT Alerts Quality Assurance")
st.markdown("Analyse synthétique et validation de la qualité du flux d'alertes.")

# --- FONCTION DE RÉCUPÉRATION API ---
def fetch_alerts_from_api(url, auth_mode, **kwargs):
    headers = {"Accept": "application/x-protobuf, application/octet-stream, application/json"}
    auth = None
    if auth_mode == "Custom Header":
        h_name, h_val = kwargs.get("custom_header_name"), kwargs.get("custom_header_value")
        if h_name and h_val: headers[h_name] = h_val
    elif auth_mode == "API Key (Header)":
        api_key = kwargs.get("api_key")
        if api_key: headers["apikey"] = api_key
    elif auth_mode == "Basic Auth (User/Pass)":
        u, p = kwargs.get("username"), kwargs.get("password")
        if u and p: auth = (u, p)

    try:
        response = requests.get(url, headers=headers, auth=auth, timeout=10)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'protobuf' in content_type or 'octet-stream' in content_type or not content_type:
                try:
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(response.content)
                    data = MessageToDict(feed)
                except:
                    data = response.json()
            else:
                data = response.json()

            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"alerts_snapshot_{ts}.json"
            filepath = os.path.join(DATA_DIR, filename)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            return data, filename
        else:
            st.error(f"Erreur API: {response.status_code}")
            return None, None
    except Exception as e:
        st.error(f"Erreur : {e}")
        return None, None

def load_alerts(file_path):
    if not os.path.exists(file_path): return None
    with open(file_path, 'r') as f:
        try: return json.load(f)
        except: return None

# --- SIDEBAR : ACQUISITION ---
st.sidebar.header("📥 Acquisition")
api_url = st.sidebar.text_input("URL Alerts", os.getenv("ALERTS_API_URL", ""))
auth_mode = st.sidebar.selectbox("Auth", ["Custom Header", "API Key (Header)", "Basic Auth (User/Pass)", "Aucune"])
api_params = {}
if auth_mode == "Custom Header":
    api_params["custom_header_name"] = st.sidebar.text_input("Header", value=os.getenv("ALERTS_CUSTOM_HEADER_NAME", ""))
    api_params["custom_header_value"] = st.sidebar.text_input("Valeur", value=os.getenv("ALERTS_CUSTOM_HEADER_VALUE", ""), type="password")
elif auth_mode == "Basic Auth (User/Pass)":
    api_params["username"] = st.sidebar.text_input("User", value=os.getenv("ALERTS_USERNAME", ""))
    api_params["password"] = st.sidebar.text_input("Pass", value=os.getenv("ALERTS_PASSWORD", ""), type="password")

if st.sidebar.button("🔄 Actualiser"):
    fetch_alerts_from_api(api_url, auth_mode, **api_params)

# --- SIDEBAR : GTFS STATIQUE (UPLOAD) ---
st.sidebar.divider()
st.sidebar.header("🗺️ GTFS Statique")
uploaded_file = st.sidebar.file_uploader("Charger un GTFS (.zip)", type="zip")
if uploaded_file is not None:
    # Sauvegarder le fichier chargé localement pour le loader
    with open(os.path.join(UPLOAD_DIR, "gtfs.zip"), "wb") as f:
        f.write(uploaded_file.getbuffer())
    loader.load() # Recharger les données
    st.sidebar.success("GTFS chargé avec succès !")

if loader.is_loaded:
    st.sidebar.success(f"✅ GTFS Actif ({len(loader.routes) if loader.routes is not None else 0} lignes)")
else:
    st.sidebar.warning("⚠️ Aucun GTFS chargé")

# --- SIDEBAR : FILTRAGE ---
st.sidebar.divider()
st.sidebar.header("📂 Analyse & Filtres")
alert_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
selected_file = st.sidebar.selectbox("Snapshot", sorted(alert_files, reverse=True)) if alert_files else None

filter_route = st.sidebar.text_input("Filtrer par Route ID", "").strip()
filter_stop = st.sidebar.text_input("Filtrer par Stop ID", "").strip()

if selected_file:
    data = load_alerts(os.path.join(DATA_DIR, selected_file))
else:
    data = None

# --- LOGIQUE D'AFFICHAGE ---
if data:
    entities = data.get('entity', [])
    alerts_list = []
    all_routes_affected = []
    all_stops_affected = []

    for ent in entities:
        alert = ent.get('alert', {})
        def get_text(obj, key_s, key_c):
            target = obj.get(key_s) or obj.get(key_c)
            if not target: return "N/A"
            translations = target.get('translation', [])
            if not translations: return "N/A"
            for tr in translations:
                if tr.get('language') == 'fr': return tr.get('text', 'N/A')
            return translations[0].get('text', 'N/A') if translations else "N/A"

        header = get_text(alert, 'header_text', 'headerText')
        description = get_text(alert, 'description_text', 'descriptionText')
        informed = alert.get('informed_entity', alert.get('informedEntity', []))
        
        routes_in_alert = list(set([inf.get('routeId') or inf.get('route_id') for inf in informed if (inf.get('routeId') or inf.get('route_id'))]))
        stops_in_alert = list(set([inf.get('stopId') or inf.get('stop_id') for inf in informed if (inf.get('stopId') or inf.get('stop_id'))]))
        
        keep = True
        if filter_route and filter_route not in routes_in_alert: keep = False
        if keep and filter_stop and filter_stop not in stops_in_alert: keep = False

        if keep:
            alerts_list.append({
                "ID": ent.get('id'), "Titre": header, "Cause": alert.get('cause', 'UNKNOWN'),
                "Effet": alert.get('effect', 'UNKNOWN'), "Lignes": ", ".join(routes_in_alert) if routes_in_alert else "Système",
                "Arrêts": ", ".join(stops_in_alert) if stops_in_alert else "-", "Description": description,
                "informed": informed, "periods": alert.get('active_period', alert.get('activePeriod', [])),
                "informed_count": len(informed), "periods_count": len(alert.get('active_period', alert.get('activePeriod', [])))
            })
            all_routes_affected.extend(routes_in_alert)
            all_stops_affected.extend(stops_in_alert)

    df_alerts = pd.DataFrame(alerts_list)
    if df_alerts.empty:
        st.warning("Aucune alerte trouvée.")
        st.stop()

    # --- RAPPORT DE SANTÉ ---
    all_invalid_routes = set()
    all_invalid_stops = set()
    alerts_with_errors = 0
    for _, row in df_alerts.iterrows():
        has_err = False
        for inf in row['informed']:
            r, s = inf.get('routeId') or inf.get('route_id'), inf.get('stopId') or inf.get('stop_id')
            if r and not loader.validate_route_id(r): all_invalid_routes.add(r); has_err = True
            if s and not loader.validate_stop_id(s): all_invalid_stops.add(s); has_err = True
        if has_err: alerts_with_errors += 1

    # --- TABS ---
    t1, t2, t3, t4 = st.tabs(["📊 Synthèse", "📋 Liste", "🔍 Deep Dive", "🏥 Santé GTFS"])

    with t1:
        c1, c2 = st.columns(2)
        c1.metric("Alertes Actives", len(df_alerts))
        c2.metric("Alertes Invalides", alerts_with_errors)
        st.divider()
        col_ca, col_ef = st.columns(2)
        col_ca.subheader("Causes")
        col_ca.bar_chart(df_alerts['Cause'].value_counts())
        col_ef.subheader("Effets")
        col_ef.bar_chart(df_alerts['Effet'].value_counts())

    with t2:
        st.dataframe(df_alerts[["ID", "Titre", "Cause", "Effet", "Lignes", "Arrêts"]], use_container_width=True, hide_index=True)

    with t3:
        alert_opt = {f"{r['ID']} - {r['Titre'][:60]}...": r['ID'] for _, r in df_alerts.iterrows()}
        sel_id = st.selectbox("Alerte", options=list(alert_opt.keys()))
        if sel_id:
            row = df_alerts[df_alerts['ID'] == alert_opt[sel_id]].iloc[0]
            st.info(f"**Description :**\n{row['Description']}")
            cp, ci = st.columns(2)
            with cp:
                st.subheader("📅 Périodes")
                for p in row['periods']:
                    s, e = p.get('start'), p.get('end')
                    st.write(f"- Du {datetime.fromtimestamp(int(s)).strftime('%d/%m %H:%M') if s else '?'} au {datetime.fromtimestamp(int(e)).strftime('%d/%m %H:%M') if e else '?'}")
            with ci:
                st.subheader("🎯 Impacts")
                inf_list = []
                for inf in row['informed']:
                    r, s = inf.get('routeId') or inf.get('route_id'), inf.get('stopId') or inf.get('stop_id')
                    inf_list.append({
                        "Route": f"{r} " + ("✅" if loader.validate_route_id(r) else "❌") if r else "-",
                        "Stop": f"{s} " + ("✅" if loader.validate_stop_id(s) else "❌") if s else "-"
                    })
                st.table(inf_list)

    with t4:
        if not loader.is_loaded: st.error("GTFS Statique non chargé.")
        else:
            health = int(((len(df_alerts) - alerts_with_errors) / len(df_alerts)) * 100)
            st.metric("Score de Cohérence", f"{health}%")
            er1, er2 = st.columns(2)
            with er1:
                st.markdown("#### ❌ Routes Fantômes")
                st.code("\n".join(sorted(list(all_invalid_routes))) if all_invalid_routes else "Aucune")
            with er2:
                st.markdown("#### ❌ Arrêts Fantômes")
                st.code("\n".join(sorted(list(all_invalid_stops))) if all_invalid_stops else "Aucune")
else:
    st.info("Utilisez la barre latérale pour acquérir des données.")
