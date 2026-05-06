import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. Cấu hình trang chuyên nghiệp
st.set_page_config(page_title="Dashboard AH4 Pro", layout="wide")
st.title("📊 Hệ Thống Phân Tích Dữ Liệu Nông Nghiệp ")

def clean_numeric(x):
    """Hàm ép kiểu số cực mạnh, xử lý dấu phẩy và khoảng trắng"""
    try:
        if isinstance(x, str):
            x = x.replace(',', '.') # Chuyển dấu phẩy thành dấu chấm
        return pd.to_numeric(x, errors='coerce') # Chuyển về số, lỗi thì thành NaN
    except:
        return None

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        # Chuẩn hóa thời gian từ mọi định dạng
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        # Loại bỏ dữ liệu lỗi thời gian và sắp xếp
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    # Ép kiểu số cho tất cả cột, bất kể tên là gì
    for col in df.columns:
        if col != 'Thời gian':
            df[col] = df[col].apply(clean_numeric)
            
    # Gộp dữ liệu trùng giây để biểu đồ đường không bị "vón cục"
    df = df.groupby('Thời gian').mean(numeric_only=True).reset_index()

    # Tự động sửa đơn vị PH và Nhiệt độ (Chia 100 nếu là số nguyên lớn)
    for col in df.columns:
        u_col = col.upper()
        if 'PH' in u_col and df[col].max() > 20: df[col] = df[col] / 100
        if ('NHIỆT' in u_col or 'TEMP' in u_col) and df[col].max() > 100: df[col] = df[col] / 100
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON dữ liệu", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file dữ liệu:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # --- BỘ LỌC THỜI GIAN THÔNG MINH (SỬA LỖI LỌC SAI NĂM) ---
        min_dt = df['Thời gian'].min()
        max_dt = df['Thời gian'].max()
        
        st.sidebar.header("📅 Lọc thời gian")
        filter_type = st.sidebar.selectbox("Xem theo:", ["Tùy chỉnh", "Toàn bộ dữ liệu", "7 ngày qua (dữ liệu thật)", "Tháng cuối (dữ liệu thật)"])
        
        # Mặc định lấy toàn bộ dữ liệu trong file để chắc chắn có dữ liệu
        start_date, end_date = min_dt, max_dt

        if filter_type == "7 ngày qua (dữ liệu thật)":
            start_date = max_dt - timedelta(days=7)
        elif filter_type == "Tháng cuối (dữ liệu thật)":
            start_date = max_dt - timedelta(days=30)
        elif filter_type == "Tùy chỉnh":
            c1, c2 = st.sidebar.columns(2)
            start_date = pd.to_datetime(c1.date_input("Từ ngày", min_dt.date()))
            end_date = pd.to_datetime(c2.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)

        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)].copy()

        if not df_filtered.empty:
            # --- HIỂN THỊ THÔNG SỐ (SỬA LỖI THIẾU TÊN TBPH/TBEC) ---
            st.subheader(f"📋 Thông số hiện tại (Dữ liệu thật)")
            
            # Tự động tìm cột chứa từ khóa, không kén tên
            def find_col(keywords):
                for col in df_filtered.columns:
                    if any(k.upper() in col.upper() for k in keywords): return col
                return None

            # Danh sách các nhóm cần hiển thị Metric nhanh
            targets = {
                "🌡️ Nhiệt Độ": ["Nhiệt Độ", "Temp"],
                "💧 Độ ẩm": ["Độ ẩm", "Humi"],
                "☀️ Ánh sáng": ["AS", "Light"],
                "🧪 PH": ["TBPH", "PH"],
                "⚡ EC": ["TBEC", "EC"],
                "🌊 Lưu lượng": ["m2/h", "Lưu lượng"]
            }

            # Tạo các ô hiển thị số
            m_cols = st.columns(min(len(targets), 4))
            idx = 0
            for label, keys in targets.items():
                col_name = find_col(keys)
                if col_name:
                    valid_series = df_filtered[col_name].dropna()
                    if not valid_series.empty:
                        last_val = valid_series.iloc[-1]
                        m_cols[idx % 4].metric(label=f"{label} ({col_name})", value=f"{last_val:.2f}")
                        idx += 1

            # --- BIỂU ĐỒ DIỄN BIẾN (SỬA LỖI ĐƯỜNG CONG VÀ ĐỘ ĐẶC) ---
            st.markdown("---")
            st.subheader("📈 Biểu đồ diễn biến (Đường cong mảnh)")
            c1, c2 = st.columns([1, 2])
            chart_choice = c1.radio("Kiểu biểu đồ:", ["Đường mảnh (Line)", "Cột rời (Bar)"], horizontal=True)
            step = c1.select_slider("Độ mảnh (Bước nhảy):", options=[1, 2, 5, 10, 20, 50], value=1)
            
            # Lấy tất cả cột số (trừ STT) để cho người dùng chọn vẽ
            num_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT', 'index']]
            selected_metrics = c2.multiselect("Chọn thông số vẽ biểu đồ:", num_cols, default=num_cols[:1])
            
            if selected_metrics:
                fig = go.Figure()
                # Áp dụng bước nhảy dữ liệu để làm mảnh đường kẻ
                display_df = df_filtered.iloc[::step]
                
                for m in selected_metrics:
                    p_data = display_df[['Thời gian', m]].dropna()
                    if not p_data.empty:
                        if "Đường mảnh" in chart_choice:
                            # Ép buộc vẽ đường mảnh (width=1.5), nối liền mạch (connectgaps=True)
                            fig.add_trace(go.Scatter(x=p_data['Thời gian'], y=p_data[m], mode='lines', name=m, connectgaps=True, line=dict(width=1.5)))
                        else:
                            fig.add_trace(go.Bar(x=p_data['Thời gian'], y=p_data[m], name=m))
                
                fig.update_layout(hovermode="x unified", template="plotly_white", height=500, xaxis_title="Thời gian", yaxis_title="Giá trị")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Hãy chọn ít nhất 1 thông số ở ô bên trên để vẽ biểu đồ.")

            # --- BẢNG DỮ LIỆU ---
            st.subheader("🔍 Chi tiết bảng dữ liệu")
            st.dataframe(df_filtered, use_container_width=True)
        else:
            st.error("⚠️ Không có dữ liệu trong khoảng thời gian này. Hãy chọn 'Toàn bộ dữ liệu' ở cột trái.")
else:
    st.info("Kéo thả file JSON vào sidebar.")
