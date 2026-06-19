import streamlit as st
import sqlite3
import pandas as pd
import time
import datetime as dt
import plotly.express as px
import os
import shutil

# =====================================================================
# ۱. مدیریت ایمن دیتابیس و فایل‌ها
# =====================================================================
for folder in ["uploads", "backups"]:
    if not os.path.exists(folder): os.makedirs(folder)

DB_NAME = "life_os_mastermind.db"

def run_query(query, params=(), fetch=False, fetchall=False):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetch: return cursor.fetchone()
            if fetchall: return cursor.fetchall()
            conn.commit()
            return True
    except sqlite3.Error as e:
        st.error(f"خطای دیتابیس: {e}")
        return None

def init_db():
    run_query('CREATE TABLE IF NOT EXISTS scheduler (id INTEGER PRIMARY KEY, type TEXT, category TEXT, task TEXT, time TEXT, is_done INTEGER DEFAULT 0, recurring TEXT DEFAULT "بدون تکرار")')
    run_query('CREATE TABLE IF NOT EXISTS pomodoro_sessions (id INTEGER PRIMARY KEY, date TEXT, duration INTEGER, category TEXT, task TEXT)')
    run_query('CREATE TABLE IF NOT EXISTS fin_accounts (id INTEGER PRIMARY KEY, name TEXT, initial_balance REAL DEFAULT 0)')
    run_query('CREATE TABLE IF NOT EXISTS fin_transactions (id INTEGER PRIMARY KEY, acc_id INTEGER, type TEXT, amount REAL, category TEXT, date TEXT, desc TEXT)')
    run_query('CREATE TABLE IF NOT EXISTS fin_budgets (id INTEGER PRIMARY KEY, category TEXT, limit_amount REAL)')
    run_query('CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, title TEXT, category TEXT, date TEXT, content TEXT, file_path TEXT)')
    
    # اطمینان از وجود حداقل یک حساب بانکی پیش‌فرض
    if not run_query("SELECT id FROM fin_accounts LIMIT 1", fetch=True):
        run_query("INSERT INTO fin_accounts (name, initial_balance) VALUES ('کیف پول اصلی', 0)")

init_db()

def auto_backup():
    timestamp = dt.datetime.now().strftime("%Y%m%d")
    backup_path = f"backups/auto_backup_{timestamp}.db"
    if not os.path.exists(backup_path): shutil.copy(DB_NAME, backup_path)

auto_backup()

def get_csv_data(table_name):
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    return df.to_csv(index=False).encode('utf-8-sig')

# =====================================================================
# ۲. هویت بصری و رابط کاربری
# =====================================================================
st.set_page_config(page_title="LifeOS | Mastermind", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #f0f2f6; }
    div.stButton > button { 
        background-color: #deff9a; color: #121212; font-weight: 900; 
        border-radius: 10px; border: none; padding: 0.5rem 1rem; transition: all 0.3s ease;
    }
    div.stButton > button:hover { background-color: #c2e673; transform: scale(1.02); }
    .stTextInput>div>div>input, .stTextArea>div>textarea, .stSelectbox>div>div>div { 
        background-color: #1e2630 !important; color: #ffffff !important; border-radius: 8px !important; direction: rtl; 
    }
    div[data-testid="stMetricValue"] { color: #deff9a; font-size: 2.5rem; font-weight: bold;}
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { border-radius: 5px 5px 0 0; background-color: #1e2630; padding: 10px 20px;}
    .stTabs [aria-selected="true"] { background-color: #deff9a !important; color: #121212 !important; font-weight: bold;}
    .stProgress .st-bo { background-color: #deff9a; }
</style>
""", unsafe_allow_html=True)

menu = st.sidebar.radio("🗂 منوی ناوبری", ["📊 داشبورد پیشرفت", "📅 برنامه‌ریزی جامع", "🍅 تایمر پومودورو", "📝 پایگاه دانش و ایده‌ها", "💰 حسابداری پیشرفته"])

st.sidebar.divider()
st.sidebar.markdown("### 📥 خروجی اطلاعات (CSV)")
st.sidebar.download_button("دانلود کارهای ثبت‌شده", get_csv_data('scheduler'), "tasks.csv", "text/csv", use_container_width=True)
st.sidebar.download_button("دانلود گزارش مالی", get_csv_data('fin_transactions'), "finance.csv", "text/csv", use_container_width=True)

MAIN_CATEGORIES = ["آزمون ارشد تکنولوژی آموزشی", "کانال نوآیین", "مدیریت آنلاین‌شاپ", "کالکشن اسکناس و کبریت", "توسعه فردی", "روزمره", "سایر"]

# =====================================================================
# ۳. صفحات سیستم
# =====================================================================

# ---------------- داشبورد ----------------
if menu == "📊 داشبورد پیشرفت":
    st.markdown("<h2 style='text-align: center; color: #deff9a;'>📊 داشبورد تحلیل عملکرد</h2>", unsafe_allow_html=True)
    st.write("---")
    
    t_tasks = run_query("SELECT COUNT(*) FROM scheduler", fetch=True)[0]
    d_tasks = run_query("SELECT COUNT(*) FROM scheduler WHERE is_done=1", fetch=True)[0]
    total_focus = run_query("SELECT SUM(duration) FROM pomodoro_sessions", fetch=True)[0] or 0
    inc = run_query("SELECT SUM(amount) FROM fin_transactions WHERE type='درآمد'", fetch=True)[0] or 0
    exp = run_query("SELECT SUM(amount) FROM fin_transactions WHERE type='هزینه'", fetch=True)[0] or 0

    c1, c2, c3 = st.columns(3)
    c1.metric("✅ کارنامه تسک‌ها", f"{(d_tasks/t_tasks*100) if t_tasks>0 else 0:.0f}%", f"{d_tasks} از {t_tasks} انجام شده")
    c2.metric("🧠 تمرکز عمیق", f"{total_focus} دقیقه", "متصل به پومودورو")
    c3.metric("💰 تراز مالی", f"{(inc-exp):,.0f} تومان", f"هزینه‌ها: {exp:,.0f}-")

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        focus_data = run_query("SELECT category, SUM(duration) FROM pomodoro_sessions GROUP BY category", fetchall=True)
        if focus_data:
            df_f = pd.DataFrame(focus_data, columns=['پروژه', 'دقیقه'])
            fig1 = px.pie(df_f, values='دقیقه', names='پروژه', hole=0.4, title="🎯 سهم تمرکز پروژه‌ها", color_discrete_sequence=px.colors.sequential.Tealgrn)
            fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig1, use_container_width=True)
            
    with col_chart2:
        if t_tasks > 0:
            df_t = pd.DataFrame({'وضعیت': ['انجام شده', 'باقی‌مانده'], 'تعداد': [d_tasks, t_tasks - d_tasks]})
            fig2 = px.pie(df_t, values='تعداد', names='وضعیت', hole=0.4, title="📈 وضعیت برنامه‌ها", color_discrete_sequence=['#deff9a', '#2e3b4e'])
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig2, use_container_width=True)

# ---------------- برنامه‌ریزی ----------------
elif menu == "📅 برنامه‌ریزی جامع":
    st.markdown("<h2 style='color: #deff9a;'>📅 مدیریت برنامه‌ها و پروژه‌ها</h2>", unsafe_allow_html=True)
    t_daily, t_float, t_projects = st.tabs(["⏰ کارهای روزانه", "📌 کارهای شناور", "📁 نمای پروژه‌ای (چک‌لیست)"])
    
    with t_daily:
        with st.form("task_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 3, 1, 1])
            cat = c1.selectbox("پروژه/دسته:", MAIN_CATEGORIES)
            task = c2.text_input("عنوان اقدام:")
            time_str = c3.text_input("ساعت:")
            recur = c4.selectbox("تکرار:", ["بدون تکرار", "روزانه"])
            if st.form_submit_button("➕ ثبت کار") and task:
                run_query("INSERT INTO scheduler (type, category, task, time, recurring) VALUES ('daily',?,?,?,?)", (cat, task, time_str, recur))
                st.rerun()
                
        for r_id, t_cat, t_task, t_time, is_done, t_rec in run_query("SELECT id, category, task, time, is_done, recurring FROM scheduler WHERE type='daily' ORDER BY is_done ASC, id DESC", fetchall=True):
            c_task, c_edit, c_del = st.columns([8, 1, 1])
            with c_task:
                chk = st.checkbox(f"[{t_cat}] {t_task} {f'(⏳ {t_time})' if t_time else ''} {f'🔄' if t_rec=='روزانه' else ''}", value=bool(is_done), key=f"td_{r_id}")
                if chk != bool(is_done):
                    run_query("UPDATE scheduler SET is_done=? WHERE id=?", (1 if chk else 0, r_id))
                    if chk and t_rec == "روزانه":
                        run_query("INSERT INTO scheduler (type, category, task, time, recurring) VALUES ('daily',?,?,?,?)", (t_cat, t_task, t_time, "روزانه"))
                    st.rerun()
            with c_del:
                if st.button("❌", key=f"del_td_{r_id}"):
                    run_query("DELETE FROM scheduler WHERE id=?", (r_id,)); st.rerun()

    with t_float:
        with st.form("float_form", clear_on_submit=True):
            c1, c2 = st.columns([1, 2])
            f_cat = c1.selectbox("پروژه:", MAIN_CATEGORIES)
            f_task = c2.text_input("عنوان کار بدون زمان:")
            if st.form_submit_button("➕ ثبت کار شناور") and f_task:
                run_query("INSERT INTO scheduler (type, category, task, time, recurring) VALUES ('float',?,?, '', 'بدون تکرار')", (f_cat, f_task))
                st.rerun()
                
        for r_id, t_cat, t_task, is_done in run_query("SELECT id, category, task, is_done FROM scheduler WHERE type='float' ORDER BY is_done ASC", fetchall=True):
            c_task, c_del = st.columns([9, 1])
            with c_task:
                chk = st.checkbox(f"📌 [{t_cat}] {t_task}", value=bool(is_done), key=f"tf_{r_id}")
                if chk != bool(is_done):
                    run_query("UPDATE scheduler SET is_done=? WHERE id=?", (1 if chk else 0, r_id)); st.rerun()
            with c_del:
                if st.button("❌", key=f"del_tf_{r_id}"): run_query("DELETE FROM scheduler WHERE id=?", (r_id,)); st.rerun()

    with t_projects:
        st.info("در این بخش کارهای شما به تفکیک پروژه‌ها نمایش داده می‌شوند.")
        categories_in_db = run_query("SELECT DISTINCT category FROM scheduler WHERE is_done=0", fetchall=True)
        for (category,) in categories_in_db:
            with st.expander(f"📁 پروژه: {category}", expanded=True):
                tasks_in_cat = run_query("SELECT id, task, type FROM scheduler WHERE category=? AND is_done=0", (category,), fetchall=True)
                for t_id, task_text, t_type in tasks_in_cat:
                    st.markdown(f"- **{task_text}** `{'روزانه' if t_type=='daily' else 'شناور'}`")

# ---------------- پومودورو ----------------
elif menu == "🍅 تایمر پومودورو":
    st.markdown("<h2 style='color: #deff9a;'>🍅 تایمر تمرکز عمیق</h2>", unsafe_allow_html=True)
    pending_tasks = run_query("SELECT id, category, task FROM scheduler WHERE is_done=0", fetchall=True)
    task_options = {t[0]: f"[{t[1]}] {t[2]}" for t in pending_tasks} if pending_tasks else {0: "[سایر] کار آزاد"}
    
    c1, c2 = st.columns([1, 2])
    with c1:
        sel_task_id = st.selectbox("اتصال به وظیفه:", list(task_options.keys()), format_func=lambda x: task_options[x])
        work_time = st.number_input("زمان تمرکز (دقیقه):", 1, 120, 25)
        rest_time = st.number_input("زمان استراحت (دقیقه):", 1, 30, 5)
        cycles = st.number_input("تعداد چرخه‌ها:", 1, 10, 1)
        start_btn = st.button("🚀 شروع چرخه", use_container_width=True)
        
    with c2:
        status_text, timer_text = st.empty(), st.empty()
        timer_text.markdown("<h1 style='text-align:center; font-size: 100px; color: #1e2630;'>00:00</h1>", unsafe_allow_html=True)
        if start_btn:
            if sel_task_id == 0: cat, task_name = "سایر", "کار آزاد"
            else:
                cat = run_query("SELECT category FROM scheduler WHERE id=?", (sel_task_id,), fetch=True)[0]
                task_name = task_options[sel_task_id]

            for cycle in range(1, cycles + 1):
                status_text.markdown(f"<h3 style='text-align:center; color: #deff9a;'>🔥 چرخه {cycle}: در حال تمرکز</h3>", unsafe_allow_html=True)
                for i in range(work_time * 60, -1, -1):
                    timer_text.markdown(f"<h1 style='text-align:center; font-size: 120px; color: #deff9a;'>{i//60:02d}:{i%60:02d}</h1>", unsafe_allow_html=True)
                    time.sleep(1)
                
                run_query("INSERT INTO pomodoro_sessions (date, duration, category, task) VALUES (?,?,?,?)", (str(dt.date.today()), work_time, cat, task_name))
                
                if cycle < cycles:
                    status_text.markdown(f"<h3 style='text-align:center; color: #4DA8DA;'>☕ زمان استراحت</h3>", unsafe_allow_html=True)
                    for i in range(rest_time * 60, -1, -1):
                        timer_text.markdown(f"<h1 style='text-align:center; font-size: 120px; color: #4DA8DA;'>{i//60:02d}:{i%60:02d}</h1>", unsafe_allow_html=True)
                        time.sleep(1)
            status_text.markdown("<h3 style='text-align:center; color: #deff9a;'>🎉 چرخه‌ها به پایان رسید!</h3>", unsafe_allow_html=True)
            st.balloons()

# ---------------- پایگاه دانش و ایده‌ها ----------------
elif menu == "📝 پایگاه دانش و ایده‌ها":
    st.markdown("<h2 style='color: #deff9a;'>📝 مدیریت دانش، فایل‌ها و ایده‌ها</h2>", unsafe_allow_html=True)
    tb_know, tb_idea, tb_journal = st.tabs(["📚 مستندات و خلاصه‌ها", "💡 بارش فکری و ایده‌ها", "📔 دفترچه روزانه"])
    
    with tb_know:
        with st.form("know_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            title = c1.text_input("عنوان یادداشت:")
            cat = c2.selectbox("دسته‌بندی:", MAIN_CATEGORIES)
            content = st.text_area("متن/نکات کلیدی:")
            uploaded_file = st.file_uploader("آپلود ضمیمه (اختیاری):")
            
            if st.form_submit_button("ذخیره مستندات") and title:
                file_path = ""
                if uploaded_file:
                    file_path = os.path.join("uploads", uploaded_file.name)
                    with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
                run_query("INSERT INTO journal (title, category, date, content, file_path) VALUES (?,?,?,?,?)", (title, cat, str(dt.date.today()), content, file_path))
                st.rerun()
                
        for r_id, title, cat, date, content, f_path in run_query("SELECT id, title, category, date, content, file_path FROM journal WHERE category != 'ایده‌ها' AND category != 'روزنوشت' ORDER BY id DESC", fetchall=True):
            with st.expander(f"📌 {title} | 📁 {cat} | 📅 {date}"):
                st.write(content)
                if f_path and os.path.exists(f_path): st.info(f"📎 فایل ضمیمه: {os.path.basename(f_path)}")
                if st.button("🗑 حذف", key=f"jk_del_{r_id}"): run_query("DELETE FROM journal WHERE id=?", (r_id,)); st.rerun()

    with tb_idea:
        with st.form("idea_form", clear_on_submit=True):
            title = st.text_input("عنوان ایده خام:")
            content = st.text_area("شرح ایده / نیازمندی‌ها:")
            if st.form_submit_button("ثبت ایده") and title:
                run_query("INSERT INTO journal (title, category, date, content, file_path) VALUES (?, 'ایده‌ها', ?, ?, '')", (title, str(dt.date.today()), content))
                st.rerun()
        for r_id, title, date, content in run_query("SELECT id, title, date, content FROM journal WHERE category = 'ایده‌ها' ORDER BY id DESC", fetchall=True):
            with st.expander(f"💡 {title} | {date}"):
                st.write(content)
                if st.button("حذف ایده", key=f"ji_del_{r_id}"): run_query("DELETE FROM journal WHERE id=?", (r_id,)); st.rerun()

    with tb_journal:
        with st.form("journal_form", clear_on_submit=True):
            content = st.text_area("اتفاقات امروز چطور بود؟ چه احساسی داشتی؟", height=200)
            if st.form_submit_button("ثبت روزنوشت") and content:
                run_query("INSERT INTO journal (title, category, date, content, file_path) VALUES ('خاطرات روزانه', 'روزنوشت', ?, ?, '')", (str(dt.datetime.now().strftime("%Y-%m-%d %H:%M")), content))
                st.rerun()
        for r_id, date, content in run_query("SELECT id, date, content FROM journal WHERE category = 'روزنوشت' ORDER BY id DESC", fetchall=True):
            st.markdown(f"**📅 {date}**")
            st.info(content)
            if st.button("حذف خاطره", key=f"jj_del_{r_id}"): run_query("DELETE FROM journal WHERE id=?", (r_id,)); st.rerun()

# ---------------- حسابداری پیشرفته ----------------
elif menu == "💰 حسابداری پیشرفته":
    st.markdown("<h2 style='color: #deff9a;'>💰 سیستم مدیریت مالی</h2>", unsafe_allow_html=True)
    tb_trans, tb_acc, tb_budget = st.tabs(["💸 تراکنش‌ها", "🏦 حساب‌ها و کیف پول", "📊 بودجه‌بندی (محدودیت)"])
    
    with tb_acc:
        st.markdown("### ثبت حساب بانکی جدید")
        with st.form("acc_form", clear_on_submit=True):
            a_name = st.text_input("نام حساب/بانک:")
            a_bal = st.number_input("موجودی اولیه (تومان):", min_value=0.0, step=100000.0)
            if st.form_submit_button("ایجاد حساب") and a_name:
                run_query("INSERT INTO fin_accounts (name, initial_balance) VALUES (?,?)", (a_name, a_bal))
                st.rerun()
        
        st.write("---")
        for a_id, a_name, a_init in run_query("SELECT id, name, initial_balance FROM fin_accounts", fetchall=True):
            # محاسبه موجودی لحظه‌ای حساب
            inc = run_query("SELECT SUM(amount) FROM fin_transactions WHERE acc_id=? AND type='درآمد'", (a_id,), fetch=True)[0] or 0
            exp = run_query("SELECT SUM(amount) FROM fin_transactions WHERE acc_id=? AND type='هزینه'", (a_id,), fetch=True)[0] or 0
            current_bal = a_init + inc - exp
            st.markdown(f"💳 **{a_name}** | موجودی فعلی: `{current_bal:,.0f}` تومان")

    with tb_trans:
        accounts = run_query("SELECT id, name FROM fin_accounts", fetchall=True)
        acc_dict = {a[0]: a[1] for a in accounts}
        
        with st.form("fin_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            typ = c1.radio("نوع:", ["هزینه", "درآمد"], horizontal=True)
            acc_sel = c2.selectbox("از حساب:", list(acc_dict.keys()), format_func=lambda x: acc_dict[x])
            cat = c3.selectbox("دسته‌بندی:", MAIN_CATEGORIES)
            amt = c4.number_input("مبلغ (تومان):", min_value=0.0, step=50000.0)
            if st.form_submit_button("ثبت تراکنش") and amt > 0:
                run_query("INSERT INTO fin_transactions (acc_id, type, amount, category, date, desc) VALUES (?,?,?,?,?, '')", (acc_sel, typ, amt, cat, str(dt.date.today())))
                st.rerun()
                
        for t_id, typ, amt, cat, date in run_query("SELECT id, type, amount, category, date FROM fin_transactions ORDER BY id DESC LIMIT 15", fetchall=True):
            st.markdown(f"{'🔴' if typ=='هزینه' else '🟢'} **{amt:,.0f} تومان** | {cat} | <small>{date}</small>", unsafe_allow_html=True)

    with tb_budget:
        with st.form("budget_form", clear_on_submit=True):
            st.markdown("### تعیین سقف هزینه ماهانه")
            c1, c2 = st.columns(2)
            b_cat = c1.selectbox("دسته‌بندی:", MAIN_CATEGORIES)
            b_limit = c2.number_input("حداکثر بودجه مجاز (تومان):", min_value=0.0, step=100000.0)
            if st.form_submit_button("تنظیم بودجه") and b_limit > 0:
                run_query("DELETE FROM fin_budgets WHERE category=?", (b_cat,)) # پاک کردن بودجه قبلی
                run_query("INSERT INTO fin_budgets (category, limit_amount) VALUES (?,?)", (b_cat, b_limit))
                st.rerun()
        
        st.write("---")
        for b_id, cat, limit in run_query("SELECT id, category, limit_amount FROM fin_budgets", fetchall=True):
            spent = run_query("SELECT SUM(amount) FROM fin_transactions WHERE type='هزینه' AND category=?", (cat,), fetch=True)[0] or 0
            st.markdown(f"🎯 **{cat}** (سقف مجاز: {limit:,.0f} تومان)")
            if spent >= limit:
                st.error(f"⚠️ اخطار! شما {spent:,.0f} تومان خرج کرده‌اید که از سقف تعیین شده بیشتر است.")
            else:
                progress_val = spent / limit
                st.progress(progress_val)
                st.caption(f"مبلغ خرج شده: {spent:,.0f} تومان | باقیمانده: {(limit - spent):,.0f} تومان")