import sqlite3
import streamlit as st
import pandas as pd
import qrcode
import base64
from io import BytesIO
import os
import json
from datetime import datetime

# ================== CONFIGURACIÓN Y CONSTANTES ==================
st.set_page_config(
    page_title="Receipt Tracker", 
    layout="centered", 
    page_icon="🎯", 
    initial_sidebar_state="collapsed" 
)

# URL de sonido "pop" sutil para interacciones
BUBBLE_POP = "https://www.soundjay.com/buttons_c2026/sounds/button-19.mp3"

# --- LÓGICA DE SESIÓN ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- CSS FRUTIGER AERO FULL EXPERIENCE + LIMPIEZA INTERFAZ ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
    
    /* 0. LIMPIEZA DE INTERFAZ STREAMLIT (Oculta Deploy, Menu y Footer) */
    header {{visibility: hidden;}}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    .stAppDeployButton {{display:none;}}
    [data-testid="stHeader"] {{background: rgba(0,0,0,0);}}
    
    /* Eliminar espacio superior */
    .block-container {{
        padding-top: 2rem !important;
        padding-bottom: 0rem !important;
    }}

    /* Ocultar iconos de enlace en títulos */
    .element-container:has(#stHeader) + div button {{
        display: none !important;
    }}

    /* 1. Fondo Aurora Animado */
    .stApp {{
        background: linear-gradient(-45deg, #a7f3d0, #34d399, #3b82f6, #60a5fa);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
        overflow-x: hidden;
    }}
    @keyframes gradientBG {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    /* 2. Burbujas Flotantes */
    .stApp::before, .stApp::after {{
        content: "";
        position: absolute;
        width: 150px;
        height: 150px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 50%;
        filter: blur(20px);
        z-index: -1;
        animation: floatBubbles 20s linear infinite;
    }}
    .stApp::after {{
        width: 100px;
        height: 100px;
        left: 80%;
        animation-duration: 25s;
        animation-direction: reverse;
    }}
    @keyframes floatBubbles {{
        0% {{ transform: translate(0, 100vh) scale(1); }}
        100% {{ transform: translate(100px, -100px) scale(1.5); }}
    }}

    /* 3. Animación de entrada y Modo Enfoque */
    @keyframes slideIn {{
        0% {{ opacity: 0; transform: translateX(50px) scale(0.98); }}
        100% {{ opacity: 1; transform: translateX(0) scale(1); }}
    }}

    .order-card, .order-card-compact {{
        animation: slideIn 0.5s cubic-bezier(0.25, 1, 0.5, 1) forwards;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }}

    /* MODO ENFOQUE Y GLASSMORPHISM */
    .order-card:hover, .order-card-compact:hover {{
        transform: scale(1.02) translateY(-5px);
        z-index: 10;
        box-shadow: 0 20px 40px rgba(0,0,0,0.15), inset 0 0 20px rgba(255,255,255,0.6);
        border-color: rgba(255, 255, 255, 1);
        background: rgba(255, 255, 255, 0.7);
    }}

    /* --- LOGIN PORTAL HORIZONTAL --- */
    [data-testid="stHorizontalBlock"] > div:has(.login-box-container) {{
        background: rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 2px solid rgba(255, 255, 255, 0.5);
        border-radius: 40px;
        padding: 40px 60px;
        box-shadow: 0 25px 50px rgba(0,0,0,0.1), inset 0 0 30px rgba(255,255,255,0.3);
        animation: portalFloat 6s ease-in-out infinite;
        text-align: center;
        max-width: 550px !important; 
        margin: 100px auto !important;
        position: relative;
        overflow: hidden;
    }}

    @keyframes portalFloat {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(-15px); }}
    }}

    .stTextInput input {{
        background: rgba(255, 255, 255, 0.6) !important;
        border-radius: 25px !important;
        text-align: left !important;
        height: 45px !important;
        border: 1px solid rgba(255,255,255,0.8) !important;
        font-weight: 600 !important;
        color: #1e3a8a !important;
    }}

    .order-card {{
        background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.5) 100%);
        backdrop-filter: blur(10px);
        border-radius: 30px;
        padding: 24px;
        margin-bottom: 25px;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.8);
        box-shadow: 0 15px 30px rgba(31, 38, 135, 0.08), inset 0 0 15px rgba(255, 255, 255, 0.5);
    }}

    .order-card-compact {{
        background: rgba(255, 255, 255, 0.7);
        border-radius: 18px;
        padding: 12px 20px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border: 1px solid rgba(255, 255, 255, 0.6);
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        backdrop-filter: blur(5px);
    }}

    .receipt-id {{
        font-family: 'Segoe UI', sans-serif;
        position: relative;
        background: linear-gradient(to bottom, #2d3748 0%, #1a202c 100%);
        color: #7dd3fc;
        padding: 10px 18px;
        border-radius: 12px;
        font-weight: 700;
        border: 1px solid #4a5568;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        display: inline-block;
    }}

    .sku-tag {{
        background: linear-gradient(to bottom, #ffffff 0%, #e2e8f0 100%);
        color: #2563eb;
        padding: 6px 14px;
        border-radius: 50px;
        font-weight: 700;
        font-size: 11px;
        border: 1px solid rgba(59, 130, 246, 0.3);
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }}

    .sku-tag-disabled {{
        opacity: 0.4;
        background: #cbd5e1 !important;
        text-decoration: line-through;
        color: #64748b !important;
    }}

    .badge {{
        padding: 6px 14px;
        border-radius: 50px;
        font-size: 11px;
        font-weight: 700;
        text-shadow: 0 1px 1px rgba(0,0,0,0.2);
        box-shadow: inset 0 -2px 4px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.4);
        color: white;
    }}
    .badge-nc {{ background: linear-gradient(135deg, #f87171 0%, #ef4444 100%); }}
    .badge-pending {{ background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); color: #451a03; }}
    .badge-success {{ background: linear-gradient(135deg, #34d399 0%, #10b981 100%); }}

    .qr-glass-container {{
        background: white;
        padding: 8px;
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.8);
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        display: inline-block;
    }}

    .stButton button {{
        background: linear-gradient(to bottom, #60a5fa 0%, #2563eb 100%) !important;
        border-radius: 20px !important;
        border: 1px solid #1d4ed8 !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        transition: transform 0.2s ease;
    }}

    [data-testid="stSidebar"] {{
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255, 255, 255, 0.2);
    }}
    </style>
    
    <audio id="popAudio">
      <source src="{BUBBLE_POP}" type="audio/mpeg">
    </audio>

    <script>
    document.addEventListener('click', function(e) {{
      if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {{
        var audio = document.getElementById("popAudio");
        audio.currentTime = 0;
        audio.play();
      }}
    }});
    </script>
""", unsafe_allow_html=True)

# ================== FUNCIONES LOGIC & AUTH ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(BASE_DIR, "source")
DB_PATH = os.path.join(BASE_DIR, "data.db")
NC_FILE = os.path.join(BASE_DIR, "estado_nc.json")
FILE_ORDENES = os.path.join(SOURCE_DIR, "ordenes.xlsx")
FILE_FACTURAS = os.path.join(SOURCE_DIR, "facturas.xlsx")

SKU_ENVIO = "5966673"
PAGE_SIZE = 10 
DIAS_VENTANA_ESTANDAR = 12 

def init_users_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS usuarios (user TEXT PRIMARY KEY, password TEXT)")
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO usuarios VALUES (?, ?)", ("admin", "1234"))
    conn.commit()
    conn.close()

def check_login(user, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE user = ? AND password = ?", (user, password))
    result = c.fetchone()
    conn.close()
    return result is not None

def clean_sku(sku):
    if pd.isna(sku): return ""
    sku_str = str(sku).strip()
    if sku_str.endswith('.0'):
        sku_str = sku_str[:-2]
    return sku_str.lstrip('0')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS ordenes (order_id TEXT PRIMARY KEY, fecha_creacion TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS ordenes_sku (order_id TEXT, sku TEXT, PRIMARY KEY (order_id, sku))")
    c.execute("CREATE TABLE IF NOT EXISTS facturas (receipt_number TEXT, sku TEXT, fecha TEXT)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_o_id ON ordenes(order_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_f_sku ON facturas(sku)")
    conn.commit()
    conn.close()

def sync_data():
    with st.spinner("🚀 Sincronizando datos..."):
        try:
            df_o = pd.read_excel(FILE_ORDENES, dtype={'SKU': str})
            df_f = pd.read_excel(FILE_FACTURAS, dtype={'f_item_code': str})
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM ordenes"); c.execute("DELETE FROM ordenes_sku"); c.execute("DELETE FROM facturas")
            for _, r in df_o.iterrows():
                oid = str(r["N de orden"]).strip()
                sku = clean_sku(r["SKU"])
                f = pd.to_datetime(r["Fecha de creación"], dayfirst=True, errors="coerce")
                f_s = f.strftime("%Y-%m-%d") if pd.notna(f) else None
                c.execute("INSERT OR IGNORE INTO ordenes VALUES (?,?)", (oid, f_s))
                c.execute("INSERT OR IGNORE INTO ordenes_sku VALUES (?,?)", (oid, sku))
            for _, r in df_f.iterrows():
                rec = str(r["v_receipt_number"]).strip()
                sku = clean_sku(r["f_item_code"])
                if rec.startswith("D"): continue
                f = pd.to_datetime(r["b_transaction_date"], dayfirst=True, errors="coerce")
                f_s = f.strftime("%Y-%m-%d") if pd.notna(f) else None
                c.execute("INSERT INTO facturas VALUES (?,?,?)", (rec, sku, f_s))
            conn.commit()
            conn.close()
            st.sidebar.success("✅ Sincronizado")
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

@st.cache_data(show_spinner=False)
def load_base_df():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT o.order_id, o.fecha_creacion, GROUP_CONCAT(os.sku) AS skus FROM ordenes o JOIN ordenes_sku os ON o.order_id = os.order_id GROUP BY o.order_id ORDER BY o.fecha_creacion DESC", conn)
    conn.close()
    return df

def find_matching_factura(sku_list, fecha_orden, dias_extra=0):
    if not fecha_orden or fecha_orden == "—" or not sku_list: return None
    ventana = DIAS_VENTANA_ESTANDAR + dias_extra
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(sku_list))
    query = f"""
        SELECT receipt_number FROM facturas 
        WHERE fecha >= date(?, '-2 days') AND fecha <= date(?, '+{ventana} days') 
        AND sku IN ({placeholders})
        GROUP BY receipt_number 
        HAVING COUNT(DISTINCT CASE WHEN sku != '{SKU_ENVIO}' THEN sku END) = ? 
           AND (SELECT COUNT(DISTINCT sku) FROM facturas f2 
                WHERE f2.receipt_number = facturas.receipt_number 
                AND f2.sku != '{SKU_ENVIO}') = ?
        ORDER BY ABS(julianday(fecha) - julianday(?)) ASC
        LIMIT 1
    """
    params = [fecha_orden, fecha_orden] + sku_list + [len(sku_list), len(sku_list), fecha_orden]
    row = conn.execute(query, params).fetchone()
    conn.close()
    return row[0] if row else None

def get_qr_base64(data):
    qr = qrcode.make(data or "Sin Datos")
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def get_local_img_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

def load_nc_state():
    return json.load(open(NC_FILE)) if os.path.exists(NC_FILE) else {}

# ================== CONTROL DE ACCESO (LOGIN) ==================
init_users_db()

if not st.session_state.authenticated:
    _, col_mid, _ = st.columns([0.1, 5, 0.1])
    with col_mid:
        with st.container():
            icon_path = os.path.join(BASE_DIR, "media", "icon06.png")
            icon_html = "🎯"
            if os.path.exists(icon_path):
                img_base_64 = get_local_img_base64(icon_path)
                icon_html = f'<img src="data:image/png;base64,{img_base_64}" width="80">'

            st.markdown('<div class="login-box-container"></div>', unsafe_allow_html=True)
            st.markdown(f"<div style='text-align: center; margin-bottom: 10px;'>{icon_html}</div>", unsafe_allow_html=True)
            
            # Título sin etiqueta 'h3' para evitar icono de enlace de Streamlit
            st.markdown("<div style='color: #1e3a8a; text-align: center; font-size: 1.75rem; font-weight: 700; font-family: Segoe UI; margin-bottom: 20px;'>Receipt Tracker</div>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                user_login = st.text_input("Usuario", placeholder="Usuario", label_visibility="collapsed")
            with c2:
                pass_login = st.text_input("Contraseña", placeholder="Contraseña", type="password", label_visibility="collapsed")
            
            st.write("")
            if st.button("Acceder", use_container_width=True):
                if check_login(user_login, pass_login):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Credenciales Incorrectas")
    st.stop()

# ================== UI PRINCIPAL (POST-LOGIN) ==================
init_db()
if "extra_days" not in st.session_state: st.session_state.extra_days = {}
if "disabled_skus" not in st.session_state: st.session_state.disabled_skus = {}

nc_state = load_nc_state()

# SIDEBAR
with st.sidebar:
    st.markdown("<div style='color: #1e3a8a; font-size: 1.5rem; font-weight: 700; text-shadow: 0 1px 2px white; font-family: Segoe UI;'>📊 Panel de Control</div>", unsafe_allow_html=True)
    st.write("")
    view_compact = st.toggle("Vista Compacta", value=False)
    
    conn = sqlite3.connect(DB_PATH)
    o_count = conn.execute("SELECT COUNT(*) FROM ordenes").fetchone()[0]
    f_count = conn.execute("SELECT COUNT(DISTINCT receipt_number) FROM facturas").fetchone()[0]
    conn.close()
    
    stats_html = f"""
        <div style='background: rgba(255, 255, 255, 0.4); padding: 20px; border-radius: 25px; border: 1px solid rgba(255, 255, 255, 0.8); position: relative; overflow: hidden;'>
            <p style='margin:0; font-size:12px; font-weight:700; color:#1e40af;'>ÓRDENES</p>
            <h2 style='margin:0; color:#1e3a8a; border:none;'>{o_count}</h2>
            <hr style='margin:10px 0; border:0; border-top:1px solid rgba(255,255,255,0.6);'>
            <p style='margin:0; font-size:11px; font-weight:700; color:#1e40af;'>FACTURAS</p>
            <h2 style='margin:0; color:#1e3a8a; border:none;'>{f_count}</h2>
        </div>
    """
    st.markdown(stats_html, unsafe_allow_html=True)
    
    if st.button("🔄 Sincronizar Excel", use_container_width=True):
        sync_data(); st.cache_data.clear(); st.rerun()
    st.divider()
    filtro = st.radio("Filtro de vista:", ["Todas", "Solo NC"], label_visibility="collapsed")
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# Header Principal sin h1 para evitar icono de ancla
st.markdown("<div style='text-align: center; color: #1e3a8a; font-size: 2.5rem; font-weight: 800; text-shadow: 0 2px 4px white; margin-bottom: 20px;'>🎯 Receipt Tracker</div>", unsafe_allow_html=True)
search = st.text_input("", placeholder="🔍 Buscar ID de orden...", label_visibility="collapsed")

full_df = load_base_df()
df_to_show = full_df[full_df["order_id"].str.contains(search.strip(), case=False)] if search else full_df.copy()

if "current_page" not in st.session_state: st.session_state.current_page = 1
pages = max(1, (len(df_to_show) + PAGE_SIZE - 1) // PAGE_SIZE)
df_page = df_to_show.iloc[(st.session_state.current_page-1)*PAGE_SIZE : st.session_state.current_page*PAGE_SIZE]

# RENDER DE CARDS
for _, r in df_page.iterrows():
    order, f_creacion, skus_raw = r["order_id"], r["fecha_creacion"], r["skus"]
    es_nc = nc_state.get(order, False)
    if filtro == "Solo NC" and not es_nc: continue

    all_skus = [s.strip() for s in skus_raw.split(',') if s.strip() != ""]
    if order not in st.session_state.disabled_skus: st.session_state.disabled_skus[order] = []
    active_skus = [s for s in all_skus if s not in st.session_state.disabled_skus[order] and s != SKU_ENVIO]
    
    bonus = st.session_state.extra_days.get(order, 0)
    factura = None if es_nc else find_matching_factura(active_skus, f_creacion, bonus)
    
    badge_class = "badge-nc" if es_nc else ("badge-success" if factura else "badge-pending")
    badge_text = "Nota de Crédito" if es_nc else ("Sincronizado" if factura else "Pendiente")

    if view_compact:
        st.markdown(f"""
            <div class="order-card-compact">
                <div style="display:flex; align-items:center; gap:15px; flex:1;">
                    <span class="badge {badge_class}" style="min-width:90px; text-align:center;">{badge_text}</span>
                    <b style="color:#1e293b; font-size:14px;">#{order}</b>
                    <span style="font-size:12px; color:#64748b;">{f_creacion or "—"}</span>
                </div>
                <div class="receipt-id" style="font-size:11px; padding:4px 10px;">🧾 {factura or "Sin Factura"}</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        qr_img = get_qr_base64(str(factura or "PENDIENTE"))
        tags_html = "".join([f'<span class="sku-tag {"sku-tag-disabled" if s in st.session_state.disabled_skus[order] else ""}">{s}</span>' for s in all_skus])
        
        st.markdown(f"""
            <div class="order-card">
                <div style="display:flex; justify-content:space-between; align-items:start;">
                    <div style="flex:1;">
                        <span class="badge {badge_class}">{badge_text}</span>
                        <div style="margin:8px 0 0 0; color:#1e293b; font-size: 1.5rem; font-weight: 700;">Orden #{order}</div>
                        <p style="margin:2px 0; font-size:12px; color:#64748b;">📅 {f_creacion or "—"} · ⏱️ Ventana: {DIAS_VENTANA_ESTANDAR + bonus}d</p>
                        <div style="margin: 15px 0;"><div class="receipt-id">🧾 {factura if factura else ("CANCELADO (NC)" if es_nc else "BUSCANDO...")}</div></div>
                        <div style="margin-top:12px; display:flex; flex-wrap:wrap; gap:6px;">{tags_html}</div>
                    </div>
                    <div class="qr-glass-container">
                        <img src="data:image/png;base64,{qr_img}" width="80" style="border-radius:10px;">
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    if not factura and not es_nc:
        c1, c2, c3 = st.columns([1, 1, 1.5])
        with c1:
            with st.popover("⚙️ Stock", use_container_width=True):
                for s in [sku for sku in all_skus if sku != SKU_ENVIO]:
                    is_disabled = s in st.session_state.disabled_skus[order]
                    if st.checkbox(f"SKU {s}", value=not is_disabled, key=f"stock_{order}_{s}") == is_disabled:
                        if is_disabled: st.session_state.disabled_skus[order].remove(s)
                        else: st.session_state.disabled_skus[order].append(s)
                        st.rerun()
        with c2:
            if st.button(f"🔍 +5 Días", key=f"btn_{order}", use_container_width=True):
                st.session_state.extra_days[order] = bonus + 5; st.rerun()
        with c3:
            with st.expander("🛠️ Diag"):
                conn = sqlite3.connect(DB_PATH)
                if active_skus:
                    ps = ",".join(['?'] * len(active_skus))
                    df_diag = pd.read_sql(f"SELECT receipt_number, fecha, sku FROM facturas WHERE sku IN ({ps}) ORDER BY fecha DESC LIMIT 3", conn, params=active_skus)
                    st.dataframe(df_diag, hide_index=True)
                conn.close()

# PAGINACIÓN
st.markdown("<br>", unsafe_allow_html=True)
p1, p2, p3 = st.columns([1, 2, 1])
with p1:
    if st.button("⬅️ Anterior", use_container_width=True) and st.session_state.current_page > 1:
        st.session_state.current_page -= 1; st.rerun()
with p2:
    st.markdown(f"<p style='text-align:center; color:#1e3a8a; font-weight:700; font-size:14px;'>{st.session_state.current_page} / {pages}</p>", unsafe_allow_html=True)
with p3:
    if st.button("Siguiente ➡️", use_container_width=True) and st.session_state.current_page < pages:
        st.session_state.current_page += 1; st.rerun()
