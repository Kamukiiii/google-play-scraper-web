import streamlit as st
import pandas as pd
from google_play_scraper import Sort, reviews
import time
from io import BytesIO

# 页面配置
st.set_page_config(page_title="High-Value Review Scraper", layout="wide")

st.title("🎯 高价值竞品评论调研平台")
st.markdown("""
**核心逻辑说明：**
1. **自动过滤短评**：字数少于 80 字符（约 15 个单词）的“水评”会被自动剔除。
2. **最有帮助排序**：优先抓取被其他用户点赞最多的评论。
3. **全文抓取**：保证长评论不被省略号截断。
""")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置参数")
    default_apps = "com.whatsapp\ncom.instagram.android"
    app_ids_input = st.text_area("APP ID 列表 (每行一个)", default_apps, height=150)

    lang = st.selectbox("语言 (Language)", ["en", "zh"], index=0)
    country = st.selectbox("国家/地区 (Country)", ["us", "cn"], index=0)

    st.divider()
    st.subheader("筛选标准")
    min_length = st.slider("评论最少字符数 (建议 80 以上)", 20, 500, 100)

    st.divider()
    st.subheader("目标数量")
    neg_target = st.number_input("目标差评数 (1-2星)", value=50)
    pos_target = st.number_input("目标好评数 (4-5星)", value=30)

    # 增加原始池大小以供筛选
    pool_size = st.number_input("原始检索池大小 (建议 1000)", value=1000)

# 主逻辑
if st.button("开始深度抓取并过滤"):
    app_list = [id.strip() for id in app_ids_input.split('\n') if id.strip()]
    final_data = []

    if not app_list:
        st.error("请输入 APP ID")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, app_id in enumerate(app_list):
            status_text.text(f"正在深度挖掘应用: {app_id}...")

            try:
                # 使用 Sort.MOST_RELEVANT 寻找高质量评论
                raw_pool, _ = reviews(
                    app_id,
                    lang=lang,
                    country=country,
                    sort=Sort.MOST_RELEVANT,
                    count=pool_size
                )
            except Exception as e:
                st.warning(f"无法访问 {app_id}: {e}")
                continue

            n_count, p_count = 0, 0
            for r in raw_pool:
                content = r['content']
                score = r['score']

                # --- 核心过滤逻辑 ---
                # 1. 长度过滤：太短的不要
                if len(content) < min_length:
                    continue

                # 2. 本地分类与存入
                item = {
                    'App ID': app_id,
                    'Type': 'Positive' if score >= 4 else ('Negative' if score <= 2 else 'Neutral'),
                    'Rating': score,
                    'Content': content,
                    'Date': r['at'].strftime('%Y-%m-%d'),
                    'Helpful Count': r['thumbsUpCount']
                }

                if score <= 2 and n_count < neg_target:
                    final_data.append(item)
                    n_count += 1
                elif score >= 4 and p_count < pos_target:
                    final_data.append(item)
                    p_count += 1

                if n_count >= neg_target and p_count >= pos_target:
                    break

            time.sleep(1.0)
            progress_bar.progress((idx + 1) / len(app_list))

        if final_data:
            df = pd.DataFrame(final_data)
            st.success(f"✅ 抓取完成！已过滤掉无效短评。")

            # 展示
            st.dataframe(df, use_container_width=True)

            # 导出 Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Deep_Research')

            st.download_button(
                label="📥 下载高价值评论 Excel",
                data=output.getvalue(),
                file_name="high_value_reviews.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("在当前检索池中未找到符合长度要求的评论，请尝试调低‘最少字符数’或调大‘检索池大小’。")