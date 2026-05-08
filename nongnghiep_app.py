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
    try:
        # Lấy số mới nhất ở cuối chuỗi lịch sử (Ví dụ: "14-01-01/32.35 14-01-08/32.36" -> Lấy 32.36)
        matches = re.findall(r'\d+-\d+-\d+/([-+]?(?:\d+\.\d+|\d+))', x)
        if matches: return float(matches[-1])
    except: pass
    try:
        match = re.search(r'[-+]?(?:\d+\.\d+|\d+)', x.replace(',', '.'))
        if match: return float(match.group(0))
    except: pass
    return None

def process_data(file):
    try:
        df = pd.read_json(file)
    except: return pd.DataFrame()
    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    else: return pd.DataFrame()
    
    skip_cols = ['Thời gian', '_id', 'STT', 'Tên khu', 'Trạng thái', 'Phương thức hoạt động', 'Người điều khiển', 'Bơm', 'Van', 'Ngưỡng tưới']
    for col in df.columns:
        if col not in skip_cols:
            df[col] = df[col].apply(clean_numeric)
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    subset = ['Thời gian', 'STT'] if 'STT' in df.columns else ['Thời gian']
    df = df.drop_duplicates(subset=subset, keep='last')
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file đang xem:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        st.sidebar.header("📅 Lọc thời gian")
        c1, c2 = st.sidebar.columns(2)
        # Sử dụng key để reset lịch khi đổi file (fix lỗi kẹt năm 2025)
        start_date = c1.date_input("Từ ngày", min_dt.date(), key=f"start_{selected_file}")
        end_date = c2.date_input("Đến ngày", max_dt.date(), key=f"end_{selected_file}")
        
        st.sidebar.markdown("---")
        st.sidebar.header("⚙️ Chế độ hiển thị")
        use_sma = st.sidebar.checkbox("Bật Trung bình cộng (Làm mượt)", value=False)
        window_size = 1
        if use_sma:
            window_size = st.sidebar.slider("Độ mượt (Số mẫu):", 2, 100, 20)

        if start_date <= end_date:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date) + timedelta(days=1) - timedelta(seconds=1)
            df_filtered = df[(df['Thời gian'] >= start_dt) & (df['Thời gian'] <= end_dt)].copy()

            if not df_filtered.empty:
                if 'STT' in df_filtered.columns:
                    stt_options = df_filtered['STT'].dropna().astype(str).unique().tolist()
                    if len(stt_options) > 1:
                        selected_stt = st.sidebar.selectbox("📍 Chọn Trạm (STT):", ["Tất cả"] + sorted(stt_options), key=f"stt_{selected_file}")
                        if "Tất cả" not in selected_stt:
                            df_filtered = df_filtered[df_filtered['STT'].astype(str) == selected_stt]

                num_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT', 'index']]
                st.subheader(f"📋 Dữ liệu tìm thấy ({len(df_filtered)} lượt đo)")
                
                if num_cols:
                    m_cols = st.columns(4)
                    for i, col_name in enumerate(num_cols[:12]):
                        val = df_filtered[col_name].dropna()
                        if not val.empty:
                            m_cols[i % 4].metric(label=col_name, value=f"{val.iloc[-1]:.2f}")

                st.markdown("---")
                # Cho phép chọn nhiều thông số
                selected_metrics = st.multiselect("Bấm vào đây để THÊM thông số vẽ biểu đồ:", num_cols, default=num_cols[:min(2, len(num_cols))], key=f"met_{selected_file}")
                
                if selected_metrics:
                    num_plots = len(selected_metrics)
                    # Giảm vertical_spacing để tiết kiệm diện tích cho biểu đồ chính
                    fig = make_subplots(rows=num_plots, cols=1, shared_xaxes=True, vertical_spacing=0.03, subplot_titles=selected_metrics)
                    
                    for i, m in enumerate(selected_metrics):
                        p_data = df_filtered[['Thời gian', m]].dropna()
                        if not p_data.empty:
                            y_values = p_data[m]
                            label_name = m
                            if use_sma:
                                y_values = y_values.rolling(window=window_size, min_periods=1).mean()
                                label_name = f"{m} (Mượt)"
                            
                            # Chế độ 'lines' để bỏ chấm tròn rối mắt
                            fig.add_trace(go.Scatter(x=p_data['Thời gian'], y=y_values, mode='lines', name=label_name, line=dict(width=2)), row=i+1, col=1)
                    
                    # TĂNG CHIỀU CAO LÊN 500 MỖI BIỂU ĐỒ ĐỂ NHÌN RÕ HƠN
                    fig.update_layout(height=500 * num_plots, showlegend=True, hovermode="x unified", template="plotly_white", margin=dict(t=50, b=50))
                    st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("🔍 Xem bảng dữ liệu gốc"):
                    st.dataframe(df_filtered, use_container_width=True)
            else:
                st.warning("⚠️ Không tìm thấy dữ liệu trong khoảng thời gian này.")
    else:
        st.info("File rỗng hoặc không đúng định dạng.")
else:
    st.info("Vui lòng tải file JSON ở thanh công cụ bên trái.")
