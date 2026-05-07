import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta
import re

st.set_page_config(page_title="Dashboard AH4 Pro", layout="wide")
st.title("📊 Hệ Thống Dữ Liệu ")

def clean_numeric(x):
    if pd.isna(x): return None
    x = str(x).strip()
    if x == "": return None
    
    # Bóc tách định dạng ngày giờ dính liền số (VD: 14-01-01/32.35)
    if '/' in x:
        try:
            val = x.split(' ')[0].split('/')[1]
            return float(val)
        except:
            pass
            
    # Ép kiểu xuyên chữ, lấy con số thực tế
    try:
        match = re.search(r'[-+]?(?:\d+\.\d+|\d+)', x.replace(',', '.'))
        if match:
            return float(match.group(0))
    except:
        pass
    return None

def process_data(file):
    try:
        df = pd.read_json(file)
    except: return pd.DataFrame()

    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    else:
        return pd.DataFrame()
    
    # Giữ lại cột STT để làm bộ lọc, không ép kiểu nó
    skip_cols = ['Thời gian', '_id', 'STT', 'Tên khu', 'Trạng thái', 'Phương thức hoạt động', 'Người điều khiển', 'Bơm', 'Van', 'Ngưỡng tưới']
    for col in df.columns:
        if col not in skip_cols:
            df[col] = df[col].apply(clean_numeric)
            
    # XÓA LỆNH GROUPBY CŨ ĐỂ KHÔNG BỊ MẤT CỘT STT
    subset = ['Thời gian', 'STT'] if 'STT' in df.columns else ['Thời gian']
    df = df.drop_duplicates(subset=subset, keep='last')

    # Tự động chia lại tỷ lệ chuẩn xác hơn (Chia 10 hoặc 100 tùy độ lớn)
    for col in df.columns:
        if col not in skip_cols and pd.api.types.is_numeric_dtype(df[col]):
            u_col = col.upper()
            max_val = df[col].max()
            
            if 'PH' in u_col and max_val > 14:
                df[col] = df[col] / (100 if max_val > 140 else 10)
            elif ('NHIỆT' in u_col or 'TEMP' in u_col) and max_val > 100:
                df[col] = df[col] / (100 if max_val >= 1000 else 10) # 370 chia 10 = 37.0°C
            elif ('ẨM' in u_col or 'HUMI' in u_col) and max_val > 100:
                df[col] = df[col] / (100 if max_val >= 1000 else 10) # 394 chia 10 = 39.4%
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file đang xem:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        st.sidebar.header("📅 Lọc thời gian")
        start_date = pd.to_datetime(st.sidebar.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(st.sidebar.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)
        
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)].copy()

        if not df_filtered.empty:
            # --- TÍNH NĂNG MỚI: LỌC THEO TRẠM/STT ĐỂ TRÁNH NHIỄU SÓNG ---
            if 'STT' in df_filtered.columns:
                stt_options = df_filtered['STT'].dropna().astype(str).unique().tolist()
                if len(stt_options) > 1:
                    st.sidebar.markdown("---")
                    st.sidebar.header("📍 Tách Trạm/Khu vực")
                    # Thêm Dropdown chọn STT
                    selected_stt = st.sidebar.selectbox(
                        "Chọn Trạm đo (STT):", 
                        ["Tất cả (Dễ bị nhiễu sóng)"] + sorted(stt_options)
                    )
                    if "Tất cả" not in selected_stt:
                        # Chỉ giữ lại dữ liệu của trạm đã chọn
                        df_filtered = df_filtered[df_filtered['STT'].astype(str) == selected_stt]

            num_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT', 'index']]
            
            st.subheader("📋 Thông số tìm thấy")
            if num_cols:
                m_cols = st.columns(4)
                for i, col_name in enumerate(num_cols[:12]):
                    val = df_filtered[col_name].dropna()
                    if not val.empty:
                        m_cols[i % 4].metric(label=col_name, value=f"{val.iloc[-1]:.2f}")

            st.markdown("---")
            c1, c2 = st.columns([1, 2])
            chart_type = c1.radio("Kiểu vẽ:", ["Đường (Line)", "Cột (Bar)"], horizontal=True)
            step = c1.select_slider("Độ mảnh (Bước nhảy):", options=[1, 2, 5, 10, 50], value=1)
            
            selected_metrics = c2.multiselect("Bấm vào đây để THÊM thông số vẽ:", num_cols, default=num_cols[:min(3, len(num_cols))])
            
            if selected_metrics:
                num_plots = len(selected_metrics)
                fig = make_subplots(rows=num_plots, cols=1, shared_xaxes=True, vertical_spacing=0.05, subplot_titles=selected_metrics)
                
                display_df = df_filtered.iloc[::step]
                
                for i, m in enumerate(selected_metrics):
                    p_data = display_df[['Thời gian', m]].dropna()
                    
                    if not p_data.empty:
                        if "Đường" in chart_type:
                            trace = go.Scatter(x=p_data['Thời gian'], y=p_data[m], mode='lines+markers', name=m, connectgaps=True, line=dict(width=1.5))
                            fig.add_trace(trace, row=i+1, col=1)
                        else:
                            trace = go.Bar(x=p_data['Thời gian'], y=p_data[m], name=m)
                            fig.add_trace(trace, row=i+1, col=1)
                    else:
                        st.warning(f"⚠️ Thông số '{m}' KHÔNG CÓ DỮ LIỆU trong khoảng thời gian hoặc Trạm đã chọn.")
                
                fig.update_layout(height=300 * num_plots, showlegend=False, hovermode="x unified", template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("🔍 Bảng dữ liệu gốc")
            st.dataframe(df_filtered, use_container_width=True)
        else:
            st.error("Khoảng thời gian này không có dữ liệu.")
else:
    st.info("Hãy tải file JSON lên sidebar.")
