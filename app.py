import streamlit as st
import pandas as pd
from google_play_scraper import Sort, reviews
import time
from io import BytesIO

# 页面配置
st.set_page_config(page_title="Google Play FULL Review Downloader", layout="wide")

st.title("🚀 Google Play 完整评论抓取平台 (绝不截断)")
st.markdown("输入 APP ID，自动抓取并分类 **完整** 的好评与差评，解决长评论被缩短的问题。")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 抓取配置")
    # 默认填入五个示例 APP
    default_apps = "com.whatsapp\ncom.instagram.android\nhttp://googleusercontent.com/spotify.com/3\ncom.facebook.orca\ncom.zhiliaoapp.musically"
    app_ids_input = st.text_area("APP ID 列表 (每行一个)", default_apps, height=150)

    # 默认设为 en 和 us
    lang = st.selectbox("语言 (Language)", ["en", "zh", "ja", "ko"], index=0)
    country = st.selectbox("国家/地区 (Country)", ["us", "cn", "jp", "kr"], index=0)

    st.divider()
    st.subheader("抓取策略 (关键！)")
    st.markdown("由于 Google 限制，要获取完整长评论，**不能**直接按星级筛选。我们将抓取一个大的评论池，然后在本地分类。")

    # 核心：定义大池子的数量
    pool_size = st.number_input("每个 APP 抓取的原始评论池大小 (100-5000)", value=500, min_value=100, step=100)

    st.divider()
    st.subheader("本地分类目标")
    st.caption("我们将从上面的池子里努力筛出以下数量：")
    neg_target = st.number_input("目标差评数 (1-2星)", value=50)
    pos_target = st.number_input("目标好评数 (4-5星)", value=30)

# 主界面逻辑
if st.button("开始执行深度抓取任务"):
    app_list = [id.strip() for id in app_ids_input.split('\n') if id.strip()]
    final_data = []

    if not app_list:
        st.error("请至少输入一个 APP ID")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, app_id in enumerate(app_list):
            status_text.text(f"正在处理深度抓取 ({idx + 1}/{len(app_list)}): {app_id}...")

            # --- 核心修改：抓取策略 ---
            # 1. 抓取一个大的、未经过滤的评论池
            # 2. sort 必须是 NEWEST 或 MOST_RELEVANT 之一，不能不写，但不要写 filter_score_with
            try:
                raw_pool, _ = reviews(
                    app_id,
                    lang=lang,
                    country=country,
                    sort=Sort.NEWEST,  # 或者 Sort.MOST_RELEVANT，都能拿到全文
                    count=pool_size,  # 抓取一个大的池子
                    # filter_score_with=None  # 核心：绝对不能有这个参数，或者设为None
                )
            except Exception as e:
                st.warning(f"无法从 {app_id} 抓取评论池: {e}")
                continue

            # 3. 本地进行全文级的星级分类和数量控制
            neg_count = 0
            pos_count = 0

            for r in raw_pool:
                score = r['score']
                # 检查评论内容是否为空（偶尔会有空评论）
                if not r['content']:
                    continue

                # 分类：1-2星为差评
                if score <= 2 and neg_count < neg_target:
                    final_data.append({
                        'App ID': app_id,
                        'Category': 'Negative',
                        'Rating': r['score'],
                        'Full Content': r['content'],  # 这里拿到的是全文！
                        'Date': r['at'].strftime('%Y-%m-%d %H:%M'),
                        'Thumbs Up': r['thumbsUpCount']
                    })
                    neg_count += 1

                # 分类：4-5星为好评
                elif score >= 4 and pos_count < pos_target:
                    final_data.append({
                        'App ID': app_id,
                        'Category': 'Positive',
                        'Rating': r['score'],
                        'Full Content': r['content'],  # 这里拿到的是全文！
                        'Date': r['at'].strftime('%Y-%m-%d %H:%M'),
                        'Thumbs Up': r['thumbsUpCount']
                    })
                    pos_count += 1

                # 如果两边都凑够了，就停止处理这个 APP 的池子
                if neg_count >= neg_target and pos_count >= pos_target:
                    break

            # 稍微等待，安全间隔
            time.sleep(1.0)
            progress_bar.progress((idx + 1) / len(app_list))

        if final_data:
            df = pd.DataFrame(final_data)
            status_text.success(f"✅ 深度抓取完成！共获得 {len(df)} 条 **完整** 评论数据。")

            # 1. 预览数据（重点预览内容列）
            st.subheader("📊 完整评论预览 (前50条)")
            st.dataframe(df[['App ID', 'Category', 'Rating', 'Full Content', 'Date']].head(50),
                         use_container_width=True)

            # 2. 导出 Excel 的核心逻辑
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 设置单元格自动换行，方便在Excel里阅读长评论
                df.to_excel(writer, index=False, sheet_name='FullReviews')
            processed_data = output.getvalue()

            st.download_button(
                label="📥 点击下载完整评论 Excel 文件",
                data=processed_data,
                file_name="google_play_FULL_reviews.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("抓取失败，评论池中未筛出符合数量的好评/差评。请尝试调大“评论池大小”或“目标数量”。")