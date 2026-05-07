import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta
import re

st.set_page_config(page_title="Dashboard AH4 Pro - Fix", layout="wide")
st.title("📊 Hệ Thống Dữ Liệu ")

def clean_numeric(x):
    if pd.isna(x): return None
    x = str(x).strip()
    if x == "": return None
    try:
        # Xử lý chuỗi log phức tạp dạng 14-01-01/32.35 -> lấy 32.35
        matches = re.findall(r'/([-+]?(?:\d+\.\d+|\d+))', x)
        if matches: return float(matches[-1])
        # Xử lý số thông thường
        match = re.search(r'[-+]?(?:\d+\.\d+|\d+)', x.replace(',', '.'))
        if match: return float(match.group(0))
    except: pass
    return None

def process_data(file):
    try:
        df = pd.read_json(file)
    except: return pd.DataFrame()

    if 'Thời gian' in df.columns:
        # --- BƯỚC FIX LỖI THỜI GIAN ---
        def fix_date_string(date_str):
            date_str = str(date_str).strip()
            # Nếu có dạng YYYY-MM-DD HH-mm-ss (dấu gạch ngang ở phần giờ)
            # Ta đổi 2 dấu gạch ngang cuối cùng thành dấu hai chấm
            if date_str.count('-') >= 4:
                parts = date_str.split(' ')
                if len(parts) == 2:
                    date_part = parts[0]
                    time_part = parts[1].replace('-', ':', 2)
                    return f"{date_part} {time_part}"
            return date_str

        df['Thời gian_Clean'] = df['Thời gian'].apply(fix_date_string)
        df['Thời gian'] = pd.to_datetime(df['Thời gian_Clean'], errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    else:
        return pd.DataFrame()
    
    skip_cols = ['Thời gian', 'Thời gian_Clean', '_id', 'STT', 'Tên khu', 'Trạng thái', 'Phương thức hoạt động', 'Người điều khiển', 'Bơm', 'Van', 'Ngưỡng tưới']
    for col in df.columns:
        if col not in skip_cols:
            df[col] = df[col].apply(clean_numeric)
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Tự động scale các giá trị bị nhân 10/100 (pH, Nhiệt độ, Độ ẩm)
    for col in df.columns:
        if col not in skip_cols and pd.api.types.is_numeric_dtype(df[col]):
            u_col = col.upper()
            max_val = df[col].max()
            if 'PH' in u_col and max_val > 14:
                df[col] = df[col] / (100 if max_val > 140 else 10)
            elif ('NHIỆT' in u_col or 'TEMP' in u_col) and max_val > 100:
                df[col] = df[col] / (100 if max_val >= 1000 else 10)
            elif ('ẨM' in u_col or 'HUMI' in u_col) and max_val > 100:
                df[col] = df[col] / (100 if max_val >= 1000 else 10)
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file đang xem:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # --- THỐNG KÊ THÁNG ĐỂ BẠN KIỂM TRA ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 Các tháng tìm thấy:")
        df['Tháng'] = df['Thời gian'].dt.strftime('%m/%Y')
        counts = df['Tháng'].value_counts().sort_index()
        st.sidebar.dataframe(counts)

        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        st.sidebar.header("📍 Lọc thời gian")
        c1, c2 = st.sidebar.columns(2)
        start_date = c1.date_input("Từ", min_dt.date(), key=f"s_{selected_file}")
        end_date = c2.date_input("Đến", max_dt.date(), key=f"e_{selected_file}")
        
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date) + timedelta(days=1)
        df_filtered = df[(df['Thời gian'] >= start_dt) & (df['Thời gian'] < end_dt)].copy()

        if not df_filtered.empty:
            # Chọn trạm (STT)
            stt_list = sorted(df_filtered['STT'].unique().tolist())
            sel_stt = st.sidebar.selectbox("Chọn Trạm (STT):", ["Tất cả"] + [str(s) for s in stt_list])
            if sel_stt != "Tất cả":
                df_filtered = df_filtered[df_filtered['STT'].astype(str) == sel_stt]

            # Hiển thị Metrics
            num_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT', 'index']]
            if num_cols:
                cols = st.columns(min(len(num_cols), 4))
                for i, c_name in enumerate(num_cols[:8]):
                    val = df_filtered[c_name].iloc[-1]
                    cols[i % 4].metric(c_name, f"{val:.2f}")

            # Vẽ biểu đồ
            sel_metrics = st.multiselect("Chọn thông số vẽ biểu đồ:", num_cols, default=num_cols[:2])
            if sel_metrics:
                fig = make_subplots(rows=len(sel_metrics), cols=1, shared_xaxes=True, vertical_spacing=0.05)
                for i, m in enumerate(sel_metrics):
                    fig.add_trace(go.Scatter(x=df_filtered['Thời gian'], y=df_filtered[m], name=m, mode='lines+markers'), row=i+1, col=1)
                fig.update_layout(height=250*len(sel_metrics), template="plotly_white", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("🔍 Dữ liệu chi tiết")
            st.dataframe(df_filtered)
    else:
        st.error("Không có dữ liệu hợp lệ trong file này.")
else:
    st.info("Vui lòng tải file JSON lên để bắt đầu.")
