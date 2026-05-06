import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Dashboard AH4 Pro", layout="wide")
st.title("📊 CÔNG CỤ PHÂN TÍCH")

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
        # Gộp dữ liệu trùng giây
        df = df.groupby('Thời gian').mean(numeric_only=True).reset_index()
    
    # Ép kiểu số cho tất cả cột trừ thời gian
    for col in df.columns:
        if col != 'Thời gian':
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # Tự động sửa đơn vị nếu số quá lớn (PH > 20 hoặc Nhiệt độ > 100)
    for col in df.columns:
        if 'PH' in col.upper() and df[col].max() > 20: df[col] = df[col] / 100
        if ('NHIỆT' in col.upper() or 'TEMP' in col.upper()) and df[col].max() > 100: df[col] = df[col] / 100
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # Lọc thời gian
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        st.sidebar.header("📅 Lọc thời gian")
        start_date = pd.to_datetime(st.sidebar.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(st.sidebar.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)
        
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)].copy()

        if not df_filtered.empty:
            # --- TỰ ĐỘNG TÌM THÔNG SỐ ĐỂ HIỂN THỊ METRIC ---
            st.subheader("📋 Thông số đo được (Mới nhất)")
            # Tìm các cột có tên chứa từ khóa tương ứng
            def find_col(keywords):
                for k in keywords:
                    for col in df_filtered.columns:
                        if k.upper() in col.upper(): return col
                return None

            m_cols = {
                "PH": find_col(["TBPH", "PH"]),
                "EC": find_col(["TBEC", "EC"]),
                "Lưu lượng": find_col(["Lưu lượng m2/h", "Lưu lượng tổng", "Lưu lượng"])
            }

            display_cols = st.columns(len([v for v in m_cols.values() if v]))
            idx = 0
            for label, col_name in m_cols.items():
                if col_name:
                    val = df_filtered[col_name].dropna()
                    if not val.empty:
                        display_cols[idx].metric(label=f"{label} ({col_name})", value=f"{val.iloc[-1]:.2f}")
                        idx += 1

            # --- BIỂU ĐỒ ---
            st.markdown("---")
            c1, c2 = st.columns([1, 2])
            chart_choice = c1.radio("Kiểu hiển thị:", ["Đường (Line)", "Cột (Bar)"], horizontal=True)
            step = c1.select_slider("Độ mảnh (Bước nhảy):", options=[1, 2, 5, 10, 50], value=1)
            
            numeric_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT']]
            selected_metrics = c2.multiselect("Chọn thông số vẽ biểu đồ:", numeric_cols, default=numeric_cols[:2] if len(numeric_cols)>1 else numeric_cols)
            
            if selected_metrics:
                fig = go.Figure()
                display_df = df_filtered.iloc[::step]
                for metric in selected_metrics:
                    plot_data = display_df[['Thời gian', metric]].dropna()
                    if not plot_data.empty:
                        if "Đường" in chart_choice:
                            fig.add_trace(go.Scatter(x=plot_data['Thời gian'], y=plot_data[metric], mode='lines', name=metric, line=dict(width=1.2)))
                        else:
                            fig.add_trace(go.Bar(x=plot_data['Thời gian'], y=plot_data[metric], name=metric))
                
                fig.update_layout(hovermode="x unified", template="plotly_white", height=500)
                st.plotly_chart(fig, use_container_width=True)

            # --- BẢNG DỮ LIỆU ---
            st.subheader("🔍 Chi tiết bảng dữ liệu")
            st.dataframe(df_filtered, use_container_width=True)
else:
    st.info("Kéo thả file vào sidebar.")
