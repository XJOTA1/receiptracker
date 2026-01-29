import sqlite3
import streamlit as st
import pandas as pd
import qrcode
import base64
from io import BytesIO
import os
import json
from datetime import datetime

mantenimiento = True  # Cambia a False para abrir la app

if mantenimiento:
    st.title("🚧 App en mantenimiento")
    st.info("Estamos realizando actualizaciones. Volveremos pronto.")
    st.stop() # Esto detiene todo lo que sigue abajo

# ================== CONFIGURACIÓN Y CONSTANTES ==================
st.set_page_config(
    page_title="Receipt Tracker", 
    layout="centered",  # CENTRALIZADO
    page_icon="🎯", 
    initial_sidebar_state="collapsed" 
)

# --- CSS PARA DISEÑO CENTRALIZADO Y PREMIUM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }

    /* Limitar ancho máximo para que no se estire en monitores ultra-wide */
    .block-container {
        max-width: 800px !important;
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    .main {
        background-color: #f8fafc;
    }

    /* Tarjeta de Orden */
    .order-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border: 1px solid #f1f5f9;
        transition: transform 0.2s ease;
    }
    
    .order-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }

    /* Status Badges */
    .badge {
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-nc { background: #dcfce7; color: #166534; }
    .badge-alert { background: #fee2e2; color: #991b1b; }
    .badge-pending { background: #f1f5f9; color: #475569; }

    /* SKUs */
    .sku-container {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 12px;
    }
    .sku-tag {
        background: #eff6ff;
        color: #1e40af;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 500;
        border: 1px solid #dbeafe;
    }
    .sku-tag-disabled {
        background: #f1f5f9;
        color: #94a3b8;
        text-decoration: line-through;
        border: 1px solid #e2e8f0;
    }

    /* Factura Code */
    .receipt-id {
        font-family: 'Monaco', monospace;
        background: #1e293b;
        color: #38bdf8;
        padding: 6px 12px;
        border-radius: 8px;
        font-size: 14px;
        display: inline-block;
        margin-top: 8px;
    }

    /* Streamlit Components */
    .stButton button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        height: 32px !important;
        font-size: 12px !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #1e293b;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(BASE_DIR, "source")
DB_PATH = os.path.join(BASE_DIR, "data.db")
NC_FILE = os.path.join(BASE_DIR, "estado_nc.json")
FILE_ORDENES = os.path.join(SOURCE_DIR, "ordenes.xlsx")
FILE_FACTURAS = os.path.join(SOURCE_DIR, "facturas.xlsx")

SKU_ENVIO = "5966673"
PAGE_SIZE = 10 
DIAS_VENTANA_ESTANDAR = 12 

# ================== FUNCIONES DB & LOGIC ==================
def clean_sku(sku):
    if pd.isna(sku): return ""
    return str(sku).strip().lstrip('0')

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
            df_o = pd.read_excel(FILE_ORDENES)
            df_f = pd.read_excel(FILE_FACTURAS)
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

def load_nc_state():
    return json.load(open(NC_FILE)) if os.path.exists(NC_FILE) else {}

# ================== UI PRINCIPAL ==================
init_db()
if "extra_days" not in st.session_state: st.session_state.extra_days = {}
if "disabled_skus" not in st.session_state: st.session_state.disabled_skus = {}

nc_state = load_nc_state()
hoy = datetime.now()

# Header
st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>🎯 Receipt Tracker</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 2rem;'>Gestión centralizada de facturación</p>", unsafe_allow_html=True)

# Búsqueda
search = st.text_input("", placeholder="🔍 Buscar ID de orden (Ej: 1359)...", label_visibility="collapsed")

# SIDEBAR
with st.sidebar:
    st.markdown("### 📊 Estadísticas")
    conn = sqlite3.connect(DB_PATH)
    o_count = conn.execute("SELECT COUNT(*) FROM ordenes").fetchone()[0]
    f_count = conn.execute("SELECT COUNT(DISTINCT receipt_number) FROM facturas").fetchone()[0]
    conn.close()
    
    st.markdown(f"""
        <div style='background:#334155; padding:15px; border-radius:12px; margin-bottom:20px;'>
            <p style='margin:0; font-size:12px; opacity:0.8;'>Órdenes</p>
            <h2 style='margin:0;'>{o_count}</h2>
            <hr style='margin:10px 0; opacity:0.2;'>
            <p style='margin:0; font-size:12px; opacity:0.8;'>Facturas</p>
            <h2 style='margin:0;'>{f_count}</h2>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 Sincronizar Excel", use_container_width=True, type="primary"):
        sync_data(); st.cache_data.clear(); st.rerun()
    
    st.divider()
    filtro = st.radio("Filtro de vista:", ["Todas", "Solo Notas de Crédito"])

full_df = load_base_df()
df_to_show = full_df.copy()
if search:
    df_to_show = df_to_show[df_to_show["order_id"].str.contains(search.strip(), case=False)]

# PAGINACIÓN
if "current_page" not in st.session_state: st.session_state.current_page = 1
pages = max(1, (len(df_to_show) + PAGE_SIZE - 1) // PAGE_SIZE)
df_page = df_to_show.iloc[(st.session_state.current_page-1)*PAGE_SIZE : st.session_state.current_page*PAGE_SIZE]

# RENDER DE CARDS
for _, r in df_page.iterrows():
    order, f_creacion, skus_raw = r["order_id"], r["fecha_creacion"], r["skus"]
    es_nc = nc_state.get(order, False)
    if filtro == "Solo Notas de Crédito" and not es_nc: continue

    all_skus = [s.strip() for s in skus_raw.split(',') if s.strip() != ""]
    if order not in st.session_state.disabled_skus: st.session_state.disabled_skus[order] = []
    active_skus = [s for s in all_skus if s not in st.session_state.disabled_skus[order] and s != SKU_ENVIO]
    
    bonus = st.session_state.extra_days.get(order, 0)
    
    if es_nc:
        factura, badge_class, badge_text = None, "badge-nc", "Nota de Crédito"
    else:
        factura = find_matching_factura(active_skus, f_creacion, bonus)
        alerta = not factura and f_creacion
        badge_class, badge_text = ("badge-alert", "Fuera de Rango") if alerta else ("badge-pending", "Pendiente")
    
    qr_img = get_qr_base64(str(factura or ("NC" if es_nc else "PENDIENTE")))
    tags_html = "".join([f'<span class="sku-tag {"sku-tag-disabled" if s in st.session_state.disabled_skus[order] else ""}">{s}</span>' for s in all_skus])

    st.markdown(f"""
        <div class="order-card">
            <div style="display:flex; justify-content:space-between; align-items:start;">
                <div style="flex:1;">
                    <span class="badge {badge_class}">{badge_text}</span>
                    <h3 style="margin:8px 0 0 0; color:#1e293b;">Orden #{order}</h3>
                    <p style="margin:2px 0; font-size:13px; color:#64748b;">📅 {f_creacion or "—"} · ⏱️ Ventana: {DIAS_VENTANA_ESTANDAR + bonus}d</p>
                    <div class="receipt-id">🧾 {factura if factura else ("CANCELADO (NC)" if es_nc else "BUSCANDO...")}</div>
                    <div class="sku-container">{tags_html}</div>
                </div>
                <div style="margin-left:20px; text-align:center;">
                    <img src="data:image/png;base64,{qr_img}" width="85" style="border-radius:10px; border:1px solid #e2e8f0; background:white; padding:4px;">
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ACCIONES: Stock a la izquierda, NC eliminada
    c1, c2, c3 = st.columns([1, 1, 1.5])
    with c1:
        with st.popover("⚙️ Stock", use_container_width=True):
            st.caption("Excluir ítems sin stock:")
            for s in [sku for sku in all_skus if sku != SKU_ENVIO]:
                is_disabled = s in st.session_state.disabled_skus[order]
                if st.checkbox(f"SKU {s}", value=not is_disabled, key=f"stock_{order}_{s}") == is_disabled:
                    if is_disabled: st.session_state.disabled_skus[order].remove(s)
                    else: st.session_state.disabled_skus[order].append(s)
                    st.rerun()
    with c2:
        if not factura and not es_nc:
            if st.button(f"🔍 +5 Días", key=f"btn_{order}", use_container_width=True):
                st.session_state.extra_days[order] = bonus + 5; st.rerun()
    with c3:
        if not factura and not es_nc:
            with st.expander("🛠️ Diagnóstico"):
                conn = sqlite3.connect(DB_PATH)
                if active_skus:
                    placeholders = ",".join(['?'] * len(active_skus))
                    query_diag = f"SELECT receipt_number, fecha, sku FROM facturas WHERE sku IN ({placeholders}) ORDER BY fecha DESC LIMIT 3"
                    df_diag = pd.read_sql(query_diag, conn, params=active_skus)
                    st.dataframe(df_diag, hide_index=True)
                conn.close()

# Paginación
st.markdown("<br>", unsafe_allow_html=True)
p1, p2, p3 = st.columns([1,2,1])
with p1:
    if st.button("⬅️ Anterior", use_container_width=True) and st.session_state.current_page > 1:
        st.session_state.current_page -= 1; st.rerun()
with p2:
    st.markdown(f"<p style='text-align:center; color:#64748b; font-size:14px;'>Página {st.session_state.current_page} de {pages}</p>", unsafe_allow_html=True)
with p3:
    if st.button("Siguiente ➡️", use_container_width=True) and st.session_state.current_page < pages:

        st.session_state.current_page += 1; st.rerun()
