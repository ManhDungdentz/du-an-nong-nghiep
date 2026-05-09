import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta
import re

st.set_page_config(page_title="Dashboard AH4 Pro", layout="wide")
st.title("📊 Hệ Thống Dữ Liệu Pro (Hiệu ứng Kép)")

def clean_numeric(x):
    if pd.isna(x): return None
    x = str(x).strip()
    if x == "": return None
    try:
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
    else:
        return pd.DataFrame()
    
    skip_cols = ['Thời gian', '_id', 'STT', 'Tên khu', 'Trạng thái', 'Phương thức hoạt động', 'Người điều khiển', 'Bơm', 'Van', 'Ngưỡng tưới']
    for col in df.columns:
        if col not in skip_cols:
            df[col] = df[col].apply(clean_numeric)
            
    subset = ['Thời gian', 'STT'] if 'STT' in df.columns else ['Thời gian']
    df = df.drop_duplicates(subset=subset, keep='last')

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
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        
        st.sidebar.markdown("---")
        st.sidebar.header("🗓️ Tháng nào có dữ liệu?")
        
        df_temp = df.copy()
        df_temp['Tháng'] = df_temp['Thời gian'].dt.strftime('%m/%Y')
        thong_ke = df_temp['Tháng'].value_counts().reset_index()
        thong_ke.columns = ['Tháng', 'Số lượt đo']
        thong_ke['Sort'] = pd.to_datetime(thong_ke['Tháng'], format='%m/%Y')
        thong_ke = thong_ke.sort_values('Sort').drop('Sort', axis=1)
        st.sidebar.dataframe(thong_ke, hide_index=True, use_container_width=True)
        
        st.sidebar.markdown("---")
        st.sidebar.header("📅 Lọc thời gian")
        c1, c2 = st.sidebar.columns(2)
        start_date = c1.date_input("Từ ngày", min_dt.date(), key=f"start_{selected_file}")
        end_date = c2.date_input("Đến ngày", max_dt.date(), key=f"end_{selected_file}")
        
        st.sidebar.markdown("---")
        st.sidebar.header("⚙️ Chế độ hiển thị")
        use_sma = st.sidebar.checkbox("Bật Trung bình cộng (Làm mượt)", value=False)
        window_size = 1
        if use_sma:
            window_size = st.sidebar.slider("Độ mượt (Số mẫu):", 2, 100, 20)

        if start_date > end_date:
            st.sidebar.error("⚠️ Lỗi: 'Từ ngày' không thể lớn hơn 'Đến ngày'. Vui lòng chọn lại!")
        else:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date) + timedelta(days=1) - timedelta(seconds=1)
            df_filtered = df[(df['Thời gian'] >= start_dt) & (df['Thời gian'] <= end_dt)].copy()

            if not df_filtered.empty:
                if 'STT' in df_filtered.columns:
                    stt_options = df_filtered['STT'].dropna().astype(str).unique().tolist()
                    if len(stt_options) > 1:
                        st.sidebar.markdown("---")
                        st.sidebar.header("📍 Tách Trạm/Khu vực")
                        selected_stt = st.sidebar.selectbox("Chọn Trạm đo (STT):", ["Tất cả (Dễ bị nhiễu)"] + sorted(stt_options), key=f"stt_{selected_file}")
                        if "Tất cả" not in selected_stt:
                            df_filtered = df_filtered[df_filtered['STT'].astype(str) == selected_stt]

                if df_filtered.empty:
                    st.warning("⚠️ Trạm đo này không hoạt động trong các ngày đã chọn.")
                else:
                    num_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT', 'index']]
                    
                    st.subheader(f"📋 Dữ liệu tìm thấy ({len(df_filtered)} lượt đo)")
                    if num_cols:
                        m_cols = st.columns(4)
                        for i, col_name in enumerate(num_cols[:12]):
                            val = df_filtered[col_name].dropna()
                            if not val.empty:
                                m_cols[i % 4].metric(label=col_name, value=f"{val.iloc[-1]:.2f}")

                    st.markdown("---")
                    col_1, col_2 = st.columns([1, 2])
                    step = col_1.select_slider("Độ mảnh (Bước nhảy):", options=[1, 2, 5, 10, 50], value=1, key=f"step_{selected_file}")
                    selected_metrics = col_2.multiselect("Bấm vào đây để THÊM thông số vẽ:", num_cols, default=num_cols[:min(3, len(num_cols))], key=f"metrics_{selected_file}")
                    
                    if selected_metrics:
                        num_plots = len(selected_metrics)
                        fig = make_subplots(rows=num_plots, cols=1, shared_xaxes=True, vertical_spacing=0.04, subplot_titles=selected_metrics)
                        
                        display_df = df_filtered.iloc[::step]
                        
                        # --- BẢN CẬP NHẬT VẼ 2 ĐƯỜNG SO SÁNH ---
                        for i, m in enumerate(selected_metrics):
                            p_data = display_df[['Thời gian', m]].dropna()
                            if not p_data.empty:
                                if use_sma:
                                    # Vẽ đường dữ liệu gốc mờ mờ ở dưới nền
                                    fig.add_trace(go.Scatter(x=p_data['Thời gian'], y=p_data[m], mode='lines', name=f"{m} (Gốc)", line=dict(width=1, color='rgba(150, 150, 150, 0.4)'), showlegend=False), row=i+1, col=1)
                                    
                                    # Tính toán và vẽ đường mượt đậm lên trên
                                    y_values = p_data[m].rolling(window=window_size, min_periods=1).mean()
                                    trace = go.Scatter(x=p_data['Thời gian'], y=y_values, mode='lines', name=f"{m} (Mượt)", connectgaps=True, line=dict(width=2.5))
                                else:
                                    # Nếu không bật mượt thì chỉ vẽ đường gốc bình thường
                                    trace = go.Scatter(x=p_data['Thời gian'], y=p_data[m], mode='lines', name=m, connectgaps=True, line=dict(width=1.5))
                                
                                fig.add_trace(trace, row=i+1, col=1)
                            else:
                                st.warning(f"⚠️ Thông số '{m}' TRỐNG.")
                        
                        fig.update_layout(height=500 * num_plots, showlegend=False, hovermode="x unified", template="plotly_white", margin=dict(t=40, b=40))
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("🔍 Bảng dữ liệu gốc"):
                        st.dataframe(df_filtered, use_container_width=True)
            else:
                st.error("❌ Không tìm thấy dữ liệu nào trong các ngày này.")
    else:
        st.info("File này không có dữ liệu hợp lệ để hiển thị.")
else:
    st.info("Hãy tải file JSON lên sidebar.")
