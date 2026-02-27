import sqlite3
import streamlit as st
import streamlit.components.v1 as components
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
    page_icon="⚙️", 
    initial_sidebar_state="expanded" 
)

# URL de sonido "pop" sutil para interacciones (Estilo UI PS)
BUBBLE_POP = "https://www.soundjay.com/buttons_c2026/sounds/beep-23.mp3"

# --- LÓGICA DE SESIÓN ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- CSS PLAYSTATION XMB THEME (PS3/PS4/PSVITA/PS5) + DARK/LIGHT MODE ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=SST:wght@400;600;700&family=Segoe+UI:wght@400;600;700&display=swap');
    
    /* DEFINICIÓN DE VARIABLES PARA MODO CLARO Y OSCURO */
    :root, [data-theme="dark"] {{
        --bg-gradient: linear-gradient(-45deg, #080c14, #001f3f, #000000, #0a192f);
        --text-main: #94a3b8;
        --text-heading: #ffffff;
        --card-bg: rgba(20, 25, 40, 0.4);
        --card-bg-hover: rgba(30, 45, 75, 0.8);
        --card-border: rgba(255, 255, 255, 0.15);
        --border-hover: rgba(255, 255, 255, 0.9);
        --accent-glow: 0 0 25px rgba(0, 112, 204, 0.7);
        --btn-bg: linear-gradient(to bottom, #00439c 0%, #002766 100%);
        --btn-border: #0070cc;
        --btn-text: #ffffff;
        --receipt-bg: linear-gradient(to bottom, #1e293b 0%, #0f172a 100%);
        --receipt-text: #38bdf8;
        --input-bg: rgba(255, 255, 255, 0.1);
        --input-text: #ffffff;
        --sidebar-bg: rgba(0, 0, 0, 0.3);
    }}

    [data-theme="light"] {{
        --bg-gradient: linear-gradient(-45deg, #e6f0fa, #ffffff, #f0f2f5, #dbeafe);
        --text-main: #475569;
        --text-heading: #0f172a;
        --card-bg: rgba(255, 255, 255, 0.65);
        --card-bg-hover: rgba(255, 255, 255, 0.95);
        --card-border: rgba(0, 0, 0, 0.1);
        --border-hover: rgba(0, 112, 204, 0.6);
        --accent-glow: 0 10px 30px rgba(0, 0, 0, 0.15);
        --btn-bg: linear-gradient(to bottom, #3b82f6 0%, #2563eb 100%);
        --btn-border: #60a5fa;
        --btn-text: #ffffff;
        --receipt-bg: linear-gradient(to bottom, #f8fafc 0%, #e2e8f0 100%);
        --receipt-text: #0369a1;
        --input-bg: rgba(255, 255, 255, 0.8);
        --input-text: #0f172a;
        --sidebar-bg: rgba(255, 255, 255, 0.3);
    }}

    /* TRANSICIÓN GLOBAL SUAVE */
    body, .stApp, .login-box-container, p, div, span, h1, h2, h3, button, input {{
        transition: background 0.5s ease-in-out, color 0.5s ease-in-out, border-color 0.5s ease-in-out, box-shadow 0.5s ease-in-out !important;
        font-family: 'Segoe UI', 'SST', sans-serif;
    }}

    /* FIX: Quitar el borde y padding extra del formulario de Streamlit */
    [data-testid="stForm"] {{ border: none !important; padding: 0 !important; }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    .stAppDeployButton {{display:none;}}
    [data-testid="stHeader"] {{background: rgba(0,0,0,0);}}
    
    .block-container {{
        padding-top: 2rem !important;
        padding-bottom: 0rem !important;
    }}

    .element-container:has(#stHeader) + div button {{
        display: none !important;
    }}

    /* 1. Fondo Gradiente Animado (Base para el Canvas JS) */
    #ps-bg-canvas {{
        background: var(--bg-gradient) !important;
        background-size: 300% 300% !important;
        animation: gradientBG 25s ease infinite;
    }}

    /* Volvemos transparentes las capas base de Streamlit para dejar ver el canvas */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background: transparent !important;
        overflow-x: hidden;
    }}

    @keyframes gradientBG {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    /* 2. Animación de Transición Slide In */
    @keyframes slideIn {{
        0% {{ opacity: 0; transform: translateX(50px) scale(0.98); }}
        100% {{ opacity: 1; transform: translateX(0) scale(1); }}
    }}

    .order-card, .order-card-compact {{
        animation: slideIn 0.5s cubic-bezier(0.25, 1, 0.5, 1) forwards;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
    }}

    /* Efecto Hover (Interacción) */
    .order-card:hover, .order-card-compact:hover {{
        transform: scale(1.02) translateY(-5px);
        z-index: 10;
        box-shadow: 0 20px 40px rgba(0,0,0,0.15), inset 0 0 20px rgba(255,255,255,0.6);
        border-color: var(--border-hover);
        background: var(--card-bg-hover);
    }}

    /* Estructuras de Tarjetas */
    .order-card {{
        background: var(--card-bg);
        backdrop-filter: blur(15px);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 25px;
        position: relative;
        overflow: hidden;
        border: 1px solid var(--card-border);
    }}

    .order-card-compact {{
        background: var(--card-bg);
        border-radius: 12px;
        padding: 12px 20px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border: 1px solid var(--card-border);
        backdrop-filter: blur(10px);
    }}

    /* --- LOGIN PORTAL HORIZONTAL --- */
    [data-testid="stHorizontalBlock"] > div:has(.login-box-container) {{
        background: var(--card-bg);
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 1px solid var(--card-border);
        border-radius: 20px;
        padding: 40px 60px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.2);
        animation: portalFloat 6s ease-in-out infinite;
        text-align: center;
        max-width: 550px !important; 
        margin: 100px auto !important;
        position: relative;
        overflow: hidden;
    }}

    @keyframes portalFloat {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(-10px); }}
    }}

    .stTextInput input {{
        background: var(--input-bg) !important;
        border-radius: 12px !important;
        text-align: left !important;
        height: 45px !important;
        border: 1px solid var(--card-border) !important;
        font-weight: 600 !important;
        color: var(--input-text) !important;
    }}

    .receipt-id {{
        font-family: 'Segoe UI', sans-serif;
        position: relative;
        background: var(--receipt-bg);
        color: var(--receipt-text);
        padding: 10px 18px;
        border-radius: 8px;
        font-weight: 700;
        border: 1px solid var(--card-border);
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        display: inline-block;
    }}

    .sku-tag {{
        background: rgba(255,255,255,0.1);
        color: var(--text-heading);
        padding: 6px 14px;
        border-radius: 5px;
        font-weight: 700;
        font-size: 11px;
        border: 1px solid var(--card-border);
        backdrop-filter: blur(5px);
    }}

    .sku-tag-disabled {{
        opacity: 0.3;
        background: rgba(100,100,100,0.2) !important;
        text-decoration: line-through;
        color: var(--text-main) !important;
    }}

    .badge {{
        padding: 6px 14px;
        border-radius: 5px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        border: 1px solid rgba(255,255,255,0.2);
        color: white;
    }}
    /* Colores estilo Trofeos/Notificaciones */
    .badge-nc {{ background: linear-gradient(135deg, #e53e3e 0%, #c53030 100%); }}
    .badge-pending {{ background: linear-gradient(135deg, #d69e2e 0%, #b7791f 100%); }}
    .badge-success {{ background: linear-gradient(135deg, #3182ce 0%, #2b6cb0 100%); }}

    .qr-glass-container {{
        background: rgba(255, 255, 255, 0.8);
        padding: 8px;
        border-radius: 12px;
        border: 1px solid var(--card-border);
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        display: inline-block;
    }}

    /* ESTILO DE BOTONES */
    .stButton button, div[data-testid="stFormSubmitButton"] button {{
        background: var(--btn-bg) !important;
        border-radius: 25px !important;
        border: 1px solid var(--btn-border) !important;
        color: var(--btn-text) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        height: 45px !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }}
    .stButton button:hover, div[data-testid="stFormSubmitButton"] button:hover {{
        box-shadow: var(--accent-glow) !important;
        transform: scale(1.03);
    }}

    [data-testid="stSidebar"] {{
        background: var(--sidebar-bg) !important;
        backdrop-filter: blur(25px);
        border-right: 1px solid var(--card-border);
    }}
    
    /* Toggle Button Flotante */
    .theme-toggle-btn {{
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 999999;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        border: 1px solid var(--card-border);
        background: var(--card-bg);
        backdrop-filter: blur(10px);
        cursor: pointer;
        font-size: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
        color: var(--text-heading);
    }}
    .theme-toggle-btn:hover {{
        transform: scale(1.1);
        box-shadow: var(--accent-glow);
    }}
    </style>
    
    <audio id="popAudio">
      <source src="{BUBBLE_POP}" type="audio/mpeg">
    </audio>
""", unsafe_allow_html=True)

# --- INYECCIÓN DE JS SEGURA (PARTÍCULAS PS VITA + ONDAS PS3) ---
components.html("""
    <script>
    if (!window.parent.psThemeInjected) {
        window.parent.psThemeInjected = true;
        const parentDoc = window.parent.document;

        // 1. Lógica de Sonido Pop
        parentDoc.addEventListener('click', function(e) {
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
                var audio = parentDoc.getElementById('popAudio');
                if (audio) {
                    audio.currentTime = 0;
                    audio.play().catch(err => console.log("Audio autoplay blocked by browser"));
                }
            }
        });

        // 2. Lógica de Cambio de Tema (Light / Dark)
        const btn = parentDoc.createElement('button');
        btn.className = 'theme-toggle-btn';
        btn.innerHTML = '🌓';
        parentDoc.body.appendChild(btn);

        const doc = parentDoc.documentElement;
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        let isDark = window.parent.localStorage.getItem('ps-theme') ? window.parent.localStorage.getItem('ps-theme') === 'dark' : prefersDark;

        const applyTheme = () => {
            doc.setAttribute('data-theme', isDark ? 'dark' : 'light');
        };
        applyTheme();

        btn.onclick = () => {
            isDark = !isDark;
            window.parent.localStorage.setItem('ps-theme', isDark ? 'dark' : 'light');
            applyTheme();
        };

        // 3. EFECTOS DINÁMICOS: ONDAS PS3 + PARTÍCULAS PS VITA
        const canvas = parentDoc.createElement('canvas');
        canvas.id = 'ps-bg-canvas';
        Object.assign(canvas.style, {
            position: 'fixed', top: '0', left: '0', width: '100vw', height: '100vh',
            zIndex: '-1', pointerEvents: 'none', transition: 'background 0.5s'
        });
        parentDoc.body.prepend(canvas);
        const ctx = canvas.getContext('2d');

        let width, height;
        function resize() {
            width = canvas.width = parentDoc.defaultView.innerWidth;
            height = canvas.height = parentDoc.defaultView.innerHeight;
        }
        parentDoc.defaultView.addEventListener('resize', resize);
        resize();

        // Crear array de partículas Vita
        const particles = Array.from({length: 40}, () => ({
            x: Math.random() * width,
            y: Math.random() * height,
            radius: Math.random() * 4 + 1,
            vx: (Math.random() - 0.5) * 0.8,
            vy: (Math.random() - 0.5) * 0.8,
            opacity: Math.random() * 0.4 + 0.1
        }));

        let time = 0;
        function drawPSBackground() {
            ctx.clearRect(0, 0, width, height);
            const isDarkTheme = doc.getAttribute('data-theme') === 'dark';
            
            // Colores basados en el tema
            const waveColor = isDarkTheme ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 112, 204, 0.15)';
            const particleColor = isDarkTheme ? '255, 255, 255' : '0, 112, 204';

            // Dibujar ondas PS3 (Sine waves matemáticos entrelazados)
            ctx.lineWidth = 1.5;
            for(let i = 0; i < 4; i++) {
                ctx.beginPath();
                ctx.strokeStyle = waveColor;
                for(let x = 0; x < width; x += 20) {
                    // Combinación de senos para lograr la onda orgánica del XMB
                    let y = height * 0.5 + 
                            Math.sin(x * 0.003 + time + i) * 80 + 
                            Math.sin(x * 0.001 + time * 0.5) * 50;
                    if(x === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();
            }

            // Dibujar Partículas PS Vita (Burbujas flotantes suaves)
            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;

                // Rebotar orgánicamente en los bordes
                if (p.x < 0 || p.x > width) p.vx *= -1;
                if (p.y < 0 || p.y > height) p.vy *= -1;

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(${particleColor}, ${p.opacity})`;
                ctx.shadowBlur = 10;
                ctx.shadowColor = `rgba(${particleColor}, 0.5)`;
                ctx.fill();
                ctx.shadowBlur = 0; // Reset para las ondas
            });

            time += 0.005;
            requestAnimationFrame(drawPSBackground);
        }
        drawPSBackground();
    }
    </script>
""", height=0, width=0)

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
        with st.form("login_form", clear_on_submit=False):
            icon_path = os.path.join(BASE_DIR, "media", "icon06.png")
            icon_html = "⚙️"
            if os.path.exists(icon_path):
                img_base_64 = get_local_img_base64(icon_path)
                icon_html = f'<img src="data:image/png;base64,{img_base_64}" width="80">'

            st.markdown('<div class="login-box-container"></div>', unsafe_allow_html=True)
            st.markdown(f"<div style='text-align: center; margin-bottom: 10px; font-size: 3rem;'>{icon_html}</div>", unsafe_allow_html=True)
            
            st.markdown("<div style='color: var(--text-heading); text-align: center; font-size: 1.75rem; font-weight: 700; margin-bottom: 20px; letter-spacing: 2px;'>RECEIPT TRACKER</div>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                user_login = st.text_input("Usuario", placeholder="Usuario", label_visibility="collapsed")
            with c2:
                pass_login = st.text_input("Contraseña", placeholder="Contraseña", type="password", label_visibility="collapsed")
            
            st.write("")
            submit_button = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            
            if submit_button:
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
    st.markdown("<div style='color: var(--text-heading); font-size: 1.5rem; font-weight: 700; font-family: Segoe UI;'>⚙️ Panel de Control</div>", unsafe_allow_html=True)
    st.write("")
    view_compact = st.toggle("Vista Compacta", value=False)
    
    conn = sqlite3.connect(DB_PATH)
    o_count = conn.execute("SELECT COUNT(*) FROM ordenes").fetchone()[0]
    f_count = conn.execute("SELECT COUNT(DISTINCT receipt_number) FROM facturas").fetchone()[0]
    conn.close()
    
    stats_html = f"""
        <div style='background: var(--card-bg); padding: 20px; border-radius: 16px; border: 1px solid var(--card-border); position: relative; overflow: hidden; margin-bottom: 20px;'>
            <p style='margin:0; font-size:12px; font-weight:700; color:var(--text-main); letter-spacing: 1px;'>ÓRDENES</p>
            <h2 style='margin:0; color:var(--text-heading); border:none;'>{o_count}</h2>
            <hr style='margin:10px 0; border:0; border-top:1px solid var(--card-border);'>
            <p style='margin:0; font-size:11px; font-weight:700; color:var(--text-main); letter-spacing: 1px;'>FACTURAS</p>
            <h2 style='margin:0; color:var(--text-heading); border:none;'>{f_count}</h2>
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

# Header Principal
st.markdown("<div style='text-align: center; color: var(--text-heading); font-size: 2.5rem; font-weight: 800; letter-spacing: 2px; margin-bottom: 20px;'>RECEIPT TRACKER</div>", unsafe_allow_html=True)
search = st.text_input("", placeholder="🔍 Buscar ID de orden...", label_visibility="collapsed")

full_df = load_base_df()
df_to_show = full_df[full_df["order_id"].str.contains(search.strip(), case=False)] if search else full_df.copy()

if "current_page" not in st.session_state: st.session_state.current_page = 1
pages = max(1, (len(df_to_show) + PAGE_SIZE - 1) // PAGE_SIZE)
df_page = df_to_show.iloc[(st.session_state.current_page-1)*PAGE_SIZE : st.session_state.current_page*PAGE_SIZE]

# RENDER DE CARDS (Se renderiza una u otra según el estado del Toggle)
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
                    <b style="color:var(--text-heading); font-size:14px;">#{order}</b>
                    <span style="font-size:12px; color:var(--text-main);">{f_creacion or "—"}</span>
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
                        <div style="margin:8px 0 0 0; color:var(--text-heading); font-size: 1.5rem; font-weight: 700; letter-spacing: 1px;">Orden #{order}</div>
                        <p style="margin:2px 0; font-size:12px; color:var(--text-main);">📅 {f_creacion or "—"} · ⏱️ Ventana: {DIAS_VENTANA_ESTANDAR + bonus}d</p>
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
    st.markdown(f"<p style='text-align:center; color:var(--text-heading); font-weight:700; font-size:14px; letter-spacing: 2px;'>{st.session_state.current_page} / {pages}</p>", unsafe_allow_html=True)
with p3:
    if st.button("Siguiente ➡️", use_container_width=True) and st.session_state.current_page < pages:
        st.session_state.current_page += 1; st.rerun()
