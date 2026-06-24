import streamlit as st
import sqlite3
import pandas as pd
import time
import datetime as dt
import plotly.express as px
import os
import shutil
import json

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
    run_query('''CREATE TABLE IF NOT EXISTS scheduler (id INTEGER PRIMARY KEY, type TEXT, category TEXT, task TEXT, time TEXT, date TEXT, is_done INTEGER DEFAULT 0, recurring TEXT DEFAULT "بدون تکرار", daily_goal INTEGER DEFAULT 0, weekly_goal INTEGER DEFAULT 0, linked_task_id INTEGER DEFAULT NULL, description TEXT DEFAULT "")''')
    run_query('CREATE TABLE IF NOT EXISTS pomodoro_sessions (id INTEGER PRIMARY KEY, date TEXT, duration INTEGER, category TEXT, task TEXT)')
    run_query('CREATE TABLE IF NOT EXISTS fin_accounts (id INTEGER PRIMARY KEY, name TEXT, initial_balance REAL DEFAULT 0)')
    run_query('CREATE TABLE IF NOT EXISTS fin_transactions (id INTEGER PRIMARY KEY, acc_id INTEGER, type TEXT, amount REAL, category TEXT, date TEXT, desc TEXT)')
    run_query('CREATE TABLE IF NOT EXISTS fin_budgets (id INTEGER PRIMARY KEY, category TEXT, limit_amount REAL)')
    run_query('''CREATE TABLE IF NOT EXISTS knowledge_base (id INTEGER PRIMARY KEY, title TEXT, knowledge_type TEXT, category TEXT, date TEXT, content TEXT, file_path TEXT, custom_fields TEXT DEFAULT "{}")''')
    run_query('''CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY, report_type TEXT, title TEXT, content TEXT, date TEXT, rating INTEGER DEFAULT 0, tags TEXT DEFAULT "")''')
    run_query('''CREATE TABLE IF NOT EXISTS user_settings (id INTEGER PRIMARY KEY, setting_key TEXT UNIQUE, setting_value TEXT)''')
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

def get_user_categories():
    custom_cats = run_query("SELECT setting_value FROM user_settings WHERE setting_key='custom_categories'", fetch=True)
    if custom_cats and custom_cats[0]:
        return eval(custom_cats[0])
    return ["آزمون ارشد تکنولوژی آموزشی", "کانال نوآیین", "مدیریت آنلاین‌شاپ", "کالکشن اسکناس و کبریت", "توسعه فردی", "روزمره", "سایر"]

def save_user_categories(categories):
    cats_str = str(categories)
    existing = run_query("SELECT id FROM user_settings WHERE setting_key='custom_categories'", fetch=True)
    if existing:
        run_query("UPDATE user_settings SET setting_value=? WHERE setting_key='custom_categories'", (cats_str,))
    else:
        run_query("INSERT INTO user_settings (setting_key, setting_value) VALUES ('custom_categories', ?)", (cats_str,))

def get_knowledge_types():
    return ["کتاب", "فیلم", "مقاله", "پادکست", "دوره آموزشی", "یادداشت", "ایده"]

def get_custom_fields_for_type(knowledge_type):
    fields_map = {
        "کتاب": ["نویسنده", "سال انتشار", "ناشر", "ISBN", "امتیاز", "وضعیت مطالعه"],
        "فیلم": ["کارگردان", "سال انتشار", "ژانر", "امتیاز", "لینک", "وضعیت تماشا"],
        "مقاله": ["نویسنده", "ژورنال", "سال انتشار", "DOI", "امتیاز", "چکیده"],
        "پادکست": ["گوینده", "مدت زمان", "لینک", "امتیاز", "برچسب‌ها"],
        "دوره آموزشی": ["مدرس", "پلتفرم", "مدت زمان", "هزینه", "امتیاز", "وضعیت"],
        "یادداشت": ["برچسب‌ها", "اولویت", "تاریخ انقضا"],
        "ایده": ["وضعیت", "اولویت", "برچسب‌ها", "بودجه تخمینی"]
    }
    return fields_map.get(knowledge_type, [])

st.set_page_config(page_title="LifeOS | Mastermind", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #f0f2f6; }
    div.stButton > button { background-color: #deff9a; color: #121212; font-weight: 900; border-radius: 10px; border: none; padding: 0.5rem 1rem; transition: all 0.3s ease;}
    div.stButton > button:hover { background-color: #c2e673; transform: scale(1.02); }
    .stTextInput>div>div>input, .stTextArea>div>textarea, .stSelectbox>div>div>div { background-color: #1e2630 !important; color: #ffffff !important; border-radius: 8px !important; direction: rtl; }
    div[data-testid="stMetricValue"] { color: #deff9a; font-size: 2.5rem; font-weight: bold;}
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { border-radius: 5px 5px 0 0; background-color: #1e2630; padding: 10px 20px;}
    .stTabs [aria-selected="true"] { background-color: #deff9a !important; color: #121212 !important; font-weight: bold;}
    .stProgress .st-bo { background-color: #deff9a; }
</style>
""", unsafe_allow_html=True)

menu = st.sidebar.radio("🗂 منوی ناوبری", [
    "📊 داشبورد پیشرفت", "📅 برنامه‌ریزی جامع", "🍅 تایمر پومودورو", 
    "📝 پایگاه دانش و ایده‌ها", "📚 گزارش‌ها و بررسی‌ها", "💰 حسابداری پیشرفته", "⚙️ تنظیمات"
])

st.sidebar.divider()
st.sidebar.markdown("### 📥 خروجی اطلاعات (CSV)")
st.sidebar.download_button("دانلود کارهای ثبت‌شده", get_csv_data('scheduler'), "tasks.csv", "text/csv", use_container_width=True)
st.sidebar.download_button("دانلود گزارش مالی", get_csv_data('fin_transactions'), "finance.csv", "text/csv", use_container_width=True)
st.sidebar.download_button("دانلود پایگاه دانش", get_csv_data('knowledge_base'), "knowledge.csv", "text/csv", use_container_width=True)

MAIN_CATEGORIES = get_user_categories()
today = dt.date.today()

if menu == "📊 داشبورد پیشرفت":
    st.markdown("<h2 style='text-align: center; color: #deff9a;'>📊 داشبورد تحلیل عملکرد</h2>", unsafe_allow_html=True)
    st.write("---")
    t_tasks = run_query("SELECT COUNT(*) FROM scheduler WHERE type IN ('daily', 'float')", fetch=True)[0]
    d_tasks = run_query("SELECT COUNT(*) FROM scheduler WHERE is_done=1 AND type IN ('daily', 'float')", fetch=True)[0]
    total_focus = run_query("SELECT SUM(duration) FROM pomodoro_sessions", fetch=True)[0] or 0
    inc = run_query("SELECT SUM(amount) FROM fin_transactions WHERE type='درآمد'", fetch=True)[0] or 0
    exp = run_query("SELECT SUM(amount) FROM fin_transactions WHERE type='هزینه'", fetch=True)[0] or 0
    daily_tasks = run_query("SELECT COUNT(*) FROM scheduler WHERE type='daily'", fetch=True)[0]
    daily_done = run_query("SELECT COUNT(*) FROM scheduler WHERE type='daily' AND is_done=1", fetch=True)[0]
    float_tasks = run_query("SELECT COUNT(*) FROM scheduler WHERE type='float'", fetch=True)[0]
    float_done = run_query("SELECT COUNT(*) FROM scheduler WHERE type='float' AND is_done=1", fetch=True)[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✅ کارنامه تسک‌ها", f"{(d_tasks/t_tasks*100) if t_tasks>0 else 0:.0f}%", f"{d_tasks} از {t_tasks} انجام شده")
    c2.metric("🧠 تمرکز عمیق", f"{total_focus} دقیقه", "متصل به پومودورو")
    c3.metric("💰 تراز مالی", f"{(inc-exp):,.0f} تومان", f"هزینه‌ها: {exp:,.0f}-")
    c4.metric("📊 کارهای روزانه", f"{(daily_done/daily_tasks*100) if daily_tasks>0 else 0:.0f}%", f"{daily_done}/{daily_tasks}")
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
    st.markdown("### 📅 پیشرفت زمانی")
    seven_days_ago = (dt.date.today() - dt.timedelta(days=7)).strftime("%Y-%m-%d")
    daily_progress = run_query("SELECT date, COUNT(*) as total, SUM(is_done) as done FROM scheduler WHERE type IN ('daily', 'float') AND date >= ? GROUP BY date ORDER BY date", (seven_days_ago,), fetchall=True)
    if daily_progress:
        df_progress = pd.DataFrame(daily_progress, columns=['تاریخ', 'کل', 'انجام شده'])
        df_progress['درصد'] = (df_progress['انجام شده'] / df_progress['کل'] * 100).fillna(0)
        fig3 = px.line(df_progress, x='تاریخ', y='درصد', title="📈 پیشرفت روزانه (7 روز گذشته)", markers=True, color_discrete_sequence=['#deff9a'])
        fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
        st.plotly_chart(fig3, use_container_width=True)
    st.markdown("### 🎯 اهداف هفتگی")
    weekly_goals = run_query("SELECT category, weekly_goal, COUNT(CASE WHEN is_done=1 THEN 1 END) as done_count, COUNT(*) as total_count FROM scheduler WHERE type='float' AND weekly_goal > 0 GROUP BY category", fetchall=True)
    if weekly_goals:
        for cat, goal, done, total in weekly_goals:
            progress = (done / goal * 100) if goal > 0 else 0
            st.markdown(f"**{cat}**: {done}/{goal} ({progress:.0f}%)")
            st.progress(min(progress / 100, 1.0))
    else:
        st.info("هیچ هدف هفتگی تعریف نشده است.")

elif menu == "📅 برنامه‌ریزی جامع":
    st.markdown("<h2 style='color: #deff9a;'>📅 مدیریت برنامه‌ها و پروژه‌ها</h2>", unsafe_allow_html=True)
    t_daily, t_float, t_projects, t_weekly, t_monthly = st.tabs(["⏰ کارهای روزانه", "📌 کارهای شناور", "📁 نمای پروژه‌ای", "📅 برنامه هفتگی", "🗓 برنامه ماهانه"])
    
    with t_daily:
        st.markdown("### 📝 ثبت کار روزانه")
        with st.form("daily_task_form", clear_on_submit=True):
            cols = st.columns([2, 2, 1, 1, 1, 1])
            with cols[0]: cat = st.selectbox("پروژه/دسته:", MAIN_CATEGORIES, key="daily_cat")
            with cols[1]: task = st.text_input("عنوان اقدام:", key="daily_task")
            with cols[2]: time_str = st.text_input("ساعت:", key="daily_time")
            with cols[3]: date_str = st.text_input("تاریخ (YYYY-MM-DD):", value=dt.date.today().strftime("%Y-%m-%d"), key="daily_date")
            with cols[4]: recur = st.selectbox("تکرار:", ["بدون تکرار", "روزانه", "هفتگی"], key="daily_recur")
            with cols[5]: link_to_float = st.selectbox("اتصال به شناور:", ["خیر", "بله"], key="link_to_float")
            description = st.text_input("توضیحات (اختیاری):", key="daily_desc")
            if st.form_submit_button("➕ ثبت کار روزانه") and task:
                result = run_query("INSERT INTO scheduler (type, category, task, time, date, recurring, description) VALUES (?,?,?,?,?,?,?)", ('daily', cat, task, time_str, date_str, recur, description))
                if result and link_to_float == "بله":
                    task_id = run_query("SELECT last_insert_rowid()", fetch=True)[0]
                    run_query("INSERT INTO scheduler (type, category, task, date, linked_task_id, description) VALUES (?,?,?,?,?,?)", ('float', cat, f"[اتصال به روزانه] {task}", date_str, task_id, description))
                st.success("کار روزانه با موفقیت ثبت شد!")
                st.rerun()
        st.write("---")
        filter_date = st.text_input("🔍 فیلتر بر اساس تاریخ (YYYY-MM-DD):", value=dt.date.today().strftime("%Y-%m-%d"), key="filter_daily_date")
        st.markdown("### 📋 لیست کارهای روزانه")
        daily_tasks = run_query("SELECT id, category, task, time, date, is_done, recurring, linked_task_id, description FROM scheduler WHERE type='daily' AND date=? ORDER BY is_done ASC, id DESC", (filter_date,), fetchall=True)
        if not daily_tasks: st.info("هیچ کار روزانه‌ای برای این تاریخ ثبت نشده است.")
        for r_id, t_cat, t_task, t_time, t_date, is_done, t_rec, linked_id, desc in daily_tasks:
            c_task, c_del = st.columns([9, 1])
            with c_task:
                linked_icon = "🔗" if linked_id else ""
                recur_icon = "🔄" if t_rec != "بدون تکرار" else ""
                desc_text = f" - {desc}" if desc else ""
                chk = st.checkbox(f"[{t_cat}] {t_task} {f'(⏳ {t_time})' if t_time else ''} {f'📅 {t_date}' if t_date else ''} {recur_icon} {linked_icon}{desc_text}", value=bool(is_done), key=f"td_{r_id}")
                if chk != bool(is_done):
                    run_query("UPDATE scheduler SET is_done=? WHERE id=?", (1 if chk else 0, r_id))
                    if chk and t_rec == "روزانه":
                        next_date = dt.datetime.strptime(t_date, "%Y-%m-%d") + dt.timedelta(days=1)
                        run_query("INSERT INTO scheduler (type, category, task, time, date, recurring, description) VALUES (?,?,?,?,?,?,?)", ('daily', t_cat, t_task, t_time, next_date.strftime("%Y-%m-%d"), t_rec, desc))
                    st.rerun()
            with c_del:
                if st.button("❌", key=f"del_td_{r_id}"): run_query("DELETE FROM scheduler WHERE id=?", (r_id,)); st.rerun()
    
    with t_float:
        st.markdown("### 📝 ثبت کار شناور")
        with st.form("float_task_form", clear_on_submit=True):
            cols = st.columns([2, 2, 1, 1, 1])
            with cols[0]: f_cat = st.selectbox("پروژه:", MAIN_CATEGORIES, key="float_cat")
            with cols[1]: f_task = st.text_input("عنوان کار:", key="float_task")
            with cols[2]: f_date = st.text_input("تاریخ (اختیاری):", key="float_date")
            with cols[3]: f_time = st.text_input("ساعت (اختیاری):", key="float_time")
            with cols[4]: link_to_daily = st.selectbox("اتصال به روزانه:", ["خیر", "بله"], key="link_to_daily")
            cols2 = st.columns([1, 1, 2])
            with cols2[0]: daily_goal = st.number_input("هدف روزانه:", min_value=0, value=0, key="float_daily_goal")
            with cols2[1]: weekly_goal = st.number_input("هدف هفتگی:", min_value=0, value=0, key="float_weekly_goal")
            with cols2[2]: f_desc = st.text_input("توضیحات:", key="float_desc")
            if st.form_submit_button("➕ ثبت کار شناور") and f_task:
                result = run_query("INSERT INTO scheduler (type, category, task, time, date, recurring, daily_goal, weekly_goal, description) VALUES (?,?,?,?,?,?,?,?,?)", ('float', f_cat, f_task, f_time if f_time else '', f_date if f_date else '', 'بدون تکرار', daily_goal, weekly_goal, f_desc))
                if result and link_to_daily == "بله":
                    task_id = run_query("SELECT last_insert_rowid()", fetch=True)[0]
                    run_query("INSERT INTO scheduler (type, category, task, time, date, linked_task_id, description) VALUES (?,?,?,?,?,?,?)", ('daily', f_cat, f"[اتصال به شناور] {f_task}", '', f_date if f_date else dt.date.today().strftime("%Y-%m-%d"), task_id, f_desc))
                st.success("کار شناور با موفقیت ثبت شد!")
                st.rerun()
        st.write("---")
        filter_float_date = st.text_input("🔍 فیلتر بر اساس تاریخ (YYYY-MM-DD) - خالی برای همه:", key="filter_float_date")
        st.markdown("### 📋 لیست کارهای شناور")
        if filter_float_date:
            float_tasks = run_query("SELECT id, category, task, time, date, is_done, daily_goal, weekly_goal, linked_task_id, description FROM scheduler WHERE type='float' AND date=? ORDER BY is_done ASC, id DESC", (filter_float_date,), fetchall=True)
        else:
            float_tasks = run_query("SELECT id, category, task, time, date, is_done, daily_goal, weekly_goal, linked_task_id, description FROM scheduler WHERE type='float' ORDER BY is_done ASC, id DESC", fetchall=True)
        if not float_tasks: st.info("هیچ کار شناوری ثبت نشده است.")
        for r_id, t_cat, t_task, t_time, t_date, is_done, d_goal, w_goal, linked_id, desc in float_tasks:
            c_task, c_del = st.columns([9, 1])
            with c_task:
                linked_icon = "🔗" if linked_id else ""
                time_text = f" (⏳ {t_time})" if t_time else ""
                date_text = f" 📅 {t_date}" if t_date else ""
                desc_text = f" - {desc}" if desc else ""
                goal_text = ""
                if d_goal > 0: goal_text += f" | هدف روزانه: {d_goal}"
                if w_goal > 0: goal_text += f" | هدف هفتگی: {w_goal}"
                chk = st.checkbox(f"📌 [{t_cat}] {t_task}{time_text}{date_text}{linked_icon}{desc_text}{goal_text}", value=bool(is_done), key=f"tf_{r_id}")
                if chk != bool(is_done): run_query("UPDATE scheduler SET is_done=? WHERE id=?", (1 if chk else 0, r_id)); st.rerun()
            with c_del:
                if st.button("❌", key=f"del_tf_{r_id}"): run_query("DELETE FROM scheduler WHERE id=?", (r_id,)); st.rerun()
    
    with t_projects:
        st.info("در این بخش کارهای شما به تفکیک پروژه‌ها نمایش داده می‌شوند.")
        project_filter = st.radio("نمایش:", ["همه", "انجام نشده", "انجام شده"], horizontal=True, key="project_filter")
        categories_in_db = run_query("SELECT DISTINCT category FROM scheduler", fetchall=True)
        for (category,) in categories_in_db:
            if project_filter == "انجام نشده":
                tasks_in_cat = run_query("SELECT id, task, type, date, time, is_done, daily_goal, weekly_goal FROM scheduler WHERE category=? AND is_done=0", (category,), fetchall=True)
            elif project_filter == "انجام شده":
                tasks_in_cat = run_query("SELECT id, task, type, date, time, is_done, daily_goal, weekly_goal FROM scheduler WHERE category=? AND is_done=1", (category,), fetchall=True)
            else:
                tasks_in_cat = run_query("SELECT id, task, type, date, time, is_done, daily_goal, weekly_goal FROM scheduler WHERE category=?", (category,), fetchall=True)
            if tasks_in_cat:
                with st.expander(f"📁 پروژه: {category} ({len(tasks_in_cat)} کار)", expanded=True):
                    for t_id, task_text, t_type, t_date, t_time, is_done, d_goal, w_goal in tasks_in_cat:
                        status_icon = "✅" if is_done else "❌"
                        type_text = 'روزانه' if t_type=='daily' else 'شناور'
                        date_time = f" - {t_date} {t_time}" if t_date or t_time else ""
                        goal_text = ""
                        if d_goal > 0: goal_text += f" | هدف روزانه: {d_goal}"
                        if w_goal > 0: goal_text += f" | هدف هفتگی: {w_goal}"
                        st.markdown(f"{status_icon} **{task_text}** `({type_text}{date_time}{goal_text})`")
    
    with t_weekly:
        st.markdown("### 📅 برنامه هفتگی")
        start_of_week = today - dt.timedelta(days=today.weekday())
        end_of_week = start_of_week + dt.timedelta(days=6)
        st.markdown(f"**هفته جاری:** {start_of_week.strftime('%Y/%m/%d')} تا {end_of_week.strftime('%Y/%m/%d')}")
        for day_offset in range(7):
            current_day = start_of_week + dt.timedelta(days=day_offset)
            day_name = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"][day_offset]
            with st.expander(f"📅 {day_name} - {current_day.strftime('%Y/%m/%d')}", expanded=day_offset == today.weekday()):
                day_tasks = run_query("SELECT id, type, category, task, time, is_done FROM scheduler WHERE date=? ORDER BY type DESC, is_done ASC", (current_day.strftime("%Y-%m-%d"),), fetchall=True)
                if not day_tasks: st.info("هیچ کاری برای این روز ثبت نشده است.")
                for t_id, t_type, t_cat, t_task, t_time, is_done in day_tasks:
                    status_icon = "✅" if is_done else "❌"
                    type_icon = "⏰" if t_type == 'daily' else "📌"
                    time_text = f" ({t_time})" if t_time else ""
                    st.markdown(f"{status_icon} {type_icon} [{t_cat}] {t_task}{time_text}")
    
    with t_monthly:
        st.markdown("### 🗓 برنامه ماهانه")
        col1, col2 = st.columns(2)
        with col1: year = st.number_input("سال:", min_value=2020, max_value=2030, value=today.year, key="monthly_year")
        with col2: month = st.number_input("ماه:", min_value=1, max_value=12, value=today.month, key="monthly_month")
        if month == 12: next_month, next_year = 1, year + 1
        else: next_month, next_year = month + 1, year
        first_day = dt.date(year, month, 1)
        last_day = dt.date(next_year, next_month, 1) - dt.timedelta(days=1)
        st.markdown(f"**ماه:** {first_day.strftime('%Y/%m/%d')} تا {last_day.strftime('%Y/%m/%d')}")
        monthly_stats = run_query("SELECT category, COUNT(*) as total, SUM(is_done) as done FROM scheduler WHERE date >= ? AND date <= ? GROUP BY category", (first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")), fetchall=True)
        if monthly_stats:
            df_monthly = pd.DataFrame(monthly_stats, columns=['دسته', 'کل', 'انجام شده'])
            df_monthly['درصد'] = (df_monthly['انجام شده'] / df_monthly['کل'] * 100).fillna(0)
            fig_monthly = px.bar(df_monthly, x='دسته', y='درصد', title="📊 پیشرفت دسته‌ها در ماه جاری", color='درصد', color_continuous_scale='Tealgrn')
            fig_monthly.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_monthly, use_container_width=True)
        st.markdown("### 📋 لیست کارهای ماهانه")
        monthly_tasks = run_query("SELECT id, type, category, task, date, time, is_done FROM scheduler WHERE date >= ? AND date <= ? ORDER BY date, is_done ASC", (first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")), fetchall=True)
        if not monthly_tasks: st.info("هیچ کاری برای این ماه ثبت نشده است.")
        else:
            tasks_by_date = {}
            for t_id, t_type, t_cat, t_task, t_date, t_time, is_done in monthly_tasks:
                if t_date not in tasks_by_date: tasks_by_date[t_date] = []
                tasks_by_date[t_date].append((t_id, t_type, t_cat, t_task, t_time, is_done))
            for date_str, tasks in sorted(tasks_by_date.items(), reverse=True):
                with st.expander(f"📅 {date_str} - {len(tasks)} کار", expanded=False):
                    for t_id, t_type, t_cat, t_task, t_time, is_done in tasks:
                        status_icon = "✅" if is_done else "❌"
                        type_icon = "⏰" if t_type == 'daily' else "📌"
                        time_text = f" ({t_time})" if t_time else ""
                        st.markdown(f"{status_icon} {type_icon} [{t_cat}] {t_task}{time_text}")

elif menu == "🍅 تایمر پومودورو":
    st.markdown("<h2 style='color: #deff9a;'>🍅 تایمر تمرکز عمیق</h2>", unsafe_allow_html=True)
    pending_tasks = run_query("SELECT id, category, task, type FROM scheduler WHERE is_done=0", fetchall=True)
    task_options = {t[0]: f"[{t[1]}] {t[2]} ({'روزانه' if t[3]=='daily' else 'شناور'})" for t in pending_tasks} if pending_tasks else {0: "[سایر] کار آزاد"}
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
                    mins, secs = divmod(i, 60)
                    timer_text.markdown(f"<h1 style='text-align:center; font-size: 120px; color: #deff9a;'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
                    time.sleep(1)
                run_query("INSERT INTO pomodoro_sessions (date, duration, category, task) VALUES (?,?,?,?)", (str(dt.date.today()), work_time, cat, task_name))
                if cycle < cycles:
                    status_text.markdown(f"<h3 style='text-align:center; color: #4DA8DA;'>☕ زمان استراحت</h3>", unsafe_allow_html=True)
                    for i in range(rest_time * 60, -1, -1):
                        mins, secs = divmod(i, 60)
                        timer_text.markdown(f"<h1 style='text-align:center; font-size: 120px; color: #4DA8DA;'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
                        time.sleep(1)
            status_text.markdown("<h3 style='text-align:center; color: #deff9a;'>🎉 چرخه‌ها به پایان رسید!</h3>", unsafe_allow_html=True)
            st.balloons()

elif menu == "📝 پایگاه دانش و ایده‌ها":
    st.markdown("<h2 style='color: #deff9a;'>📝 مدیریت دانش، فایل‌ها و ایده‌ها</h2>", unsafe_allow_html=True)
    tb_know, tb_idea, tb_journal, tb_custom = st.tabs(["📚 مستندات و خلاصه‌ها", "💡 بارش فکری و ایده‌ها", "📔 دفترچه روزانه", "🔧 دانش سفارشی"])
    
    with tb_know:
        with st.form("know_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            with c1: title = st.text_input("عنوان یادداشت:")
            with c2: cat = st.selectbox("دسته‌بندی:", MAIN_CATEGORIES)
            content = st.text_area("متن/نکات کلیدی:")
            uploaded_file = st.file_uploader("آپلود ضمیمه (اختیاری):")
            if st.form_submit_button("ذخیره مستندات") and title:
                file_path = ""
                if uploaded_file:
                    file_path = os.path.join("uploads", uploaded_file.name)
                    with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
                run_query("INSERT INTO knowledge_base (title, knowledge_type, category, date, content, file_path) VALUES (?,?,?,?,?,?)", (title, 'یادداشت', cat, str(dt.date.today()), content, file_path))
                st.success("مستند با موفقیت ذخیره شد!")
                st.rerun()
        st.write("---")
        documents = run_query("SELECT id, title, category, date, content, file_path FROM knowledge_base WHERE knowledge_type='یادداشت' ORDER BY id DESC", fetchall=True)
        if not documents: st.info("هیچ مستندی ثبت نشده است.")
        for r_id, title, cat, date, content, f_path in documents:
            with st.expander(f"📌 {title} | 📁 {cat} | 📅 {date}"):
                st.write(content)
                if f_path and os.path.exists(f_path): st.info(f"📎 فایل ضمیمه: {os.path.basename(f_path)}")
                if st.button("🗑 حذف", key=f"jk_del_{r_id}"): run_query("DELETE FROM knowledge_base WHERE id=?", (r_id,)); st.rerun()
    
    with tb_idea:
        with st.form("idea_form", clear_on_submit=True):
            title = st.text_input("عنوان ایده خام:")
            content = st.text_area("شرح ایده / نیازمندی‌ها:")
            if st.form_submit_button("ثبت ایده") and title:
                run_query("INSERT INTO knowledge_base (title, knowledge_type, category, date, content) VALUES (?, 'ایده', 'ایده‌ها', ?, ?)", (title, str(dt.date.today()), content))
                st.success("ایده با موفقیت ثبت شد!")
                st.rerun()
        st.write("---")
        ideas = run_query("SELECT id, title, date, content FROM knowledge_base WHERE knowledge_type='ایده' ORDER BY id DESC", fetchall=True)
        if not ideas: st.info("هیچ ایده‌ای ثبت نشده است.")
        for r_id, title, date, content in ideas:
            with st.expander(f"💡 {title} | {date}"):
                st.write(content)
                if st.button("حذف ایده", key=f"ji_del_{r_id}"): run_query("DELETE FROM knowledge_base WHERE id=?", (r_id,)); st.rerun()
    
    with tb_journal:
        with st.form("journal_form", clear_on_submit=True):
            content = st.text_area("اتفاقات امروز چطور بود؟ چه احساسی داشتی؟", height=200)
            if st.form_submit_button("ثبت روزنوشت") and content:
                run_query("INSERT INTO knowledge_base (title, knowledge_type, category, date, content) VALUES ('خاطرات روزانه', 'روزنوشت', 'روزنوشت', ?, ?)", (str(dt.datetime.now().strftime("%Y-%m-%d %H:%M")), content))
                st.success("روزنوشت با موفقیت ثبت شد!")
                st.rerun()
        st.write("---")
        journals = run_query("SELECT id, date, content FROM knowledge_base WHERE knowledge_type='روزنوشت' ORDER BY id DESC", fetchall=True)
        if not journals: st.info("هیچ روزنوشتی ثبت نشده است.")
        for r_id, date, content in journals:
            st.markdown(f"**📅 {date}**")
            st.info(content)
            if st.button("حذف خاطره", key=f"jj_del_{r_id}"): run_query("DELETE FROM knowledge_base WHERE id=?", (r_id,)); st.rerun()
    
    with tb_custom:
        st.markdown("### 🔧 دانش سفارشی (کتاب، فیلم، مقاله و ...)")
        knowledge_types = get_knowledge_types()
        with st.form("custom_knowledge_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 2])
            with c1: title = st.text_input("عنوان:", key="custom_title")
            with c2: knowledge_type = st.selectbox("نوع دانش:", knowledge_types, key="custom_type")
            category = st.selectbox("دسته‌بندی:", MAIN_CATEGORIES, key="custom_cat")
            content = st.text_area("توضیحات/چکیده:", key="custom_content")
            uploaded_file = st.file_uploader("آپلود فایل (اختیاری):", key="custom_file")
            st.markdown("**فیلدهای سفارشی:**")
            custom_fields = get_custom_fields_for_type(knowledge_type)
            custom_values = {}
            cols = st.columns(2)
            for i, field in enumerate(custom_fields):
                with cols[i % 2]: custom_values[field] = st.text_input(field, key=f"custom_{field}_{i}")
            if st.form_submit_button("ثبت دانش سفارشی") and title:
                file_path = ""
                if uploaded_file:
                    file_path = os.path.join("uploads", uploaded_file.name)
                    with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
                custom_fields_json = json.dumps(custom_values, ensure_ascii=False)
                run_query("INSERT INTO knowledge_base (title, knowledge_type, category, date, content, file_path, custom_fields) VALUES (?,?,?,?,?,?,?)", (title, knowledge_type, category, str(dt.date.today()), content, file_path, custom_fields_json))
                st.success(f"{knowledge_type} با موفقیت ثبت شد!")
                st.rerun()
        st.write("---")
        st.markdown("### 📚 لیست دانش سفارشی")
        knowledge_filter = st.selectbox("فیلتر بر اساس نوع:", ["همه"] + knowledge_types, key="knowledge_filter")
        if knowledge_filter == "همه":
            custom_knowledge = run_query("SELECT id, title, knowledge_type, category, date, content, file_path, custom_fields FROM knowledge_base WHERE knowledge_type NOT IN ('یادداشت', 'ایده', 'روزنوشت') ORDER BY id DESC", fetchall=True)
        else:
            custom_knowledge = run_query("SELECT id, title, knowledge_type, category, date, content, file_path, custom_fields FROM knowledge_base WHERE knowledge_type=? ORDER BY id DESC", (knowledge_filter,), fetchall=True)
        if not custom_knowledge: st.info("هیچ موردی یافت نشد.")
        for r_id, title, k_type, cat, date, content, f_path, custom_fields_str in custom_knowledge:
            with st.expander(f"{k_type} 📖 {title} | 📁 {cat} | 📅 {date}", expanded=False):
                st.markdown(f"**چکیده:** {content}")
                if custom_fields_str:
                    try:
                        custom_fields = json.loads(custom_fields_str)
                        if custom_fields:
                            st.markdown("**فیلدهای سفارشی:**")
                            for field, value in custom_fields.items():
                                if value: st.markdown(f"- **{field}:** {value}")
                    except: pass
                if f_path and os.path.exists(f_path): st.info(f"📎 فایل ضمیمه: {os.path.basename(f_path)}")
                if st.button("🗑 حذف", key=f"kc_del_{r_id}"): run_query("DELETE FROM knowledge_base WHERE id=?", (r_id,)); st.rerun()

elif menu == "📚 گزارش‌ها و بررسی‌ها":
    st.markdown("<h2 style='color: #deff9a;'>📚 گزارش‌ها و بررسی‌ها</h2>", unsafe_allow_html=True)
    tb_daily_report, tb_book_report, tb_movie_report, tb_article_report, tb_stats = st.tabs(["📅 گزارش روزانه", "📖 گزارش کتاب", "🎬 گزارش فیلم", "📰 گزارش مقاله", "📊 آمار و تحلیل"])
    
    with tb_daily_report:
        st.markdown("### 📅 ثبت گزارش روزانه")
        with st.form("daily_report_form", clear_on_submit=True):
            report_date = st.text_input("تاریخ:", value=dt.date.today().strftime("%Y-%m-%d"), key="report_date")
            report_title = st.text_input("عنوان گزارش:", key="report_title")
            report_content = st.text_area("محتوا:", key="report_content")
            report_rating = st.slider("امتیاز (1-10):", 1, 10, 5, key="report_rating")
            report_tags = st.text_input("برچسب‌ها (با کاما جدا کنید):", key="report_tags")
            if st.form_submit_button("ثبت گزارش روزانه") and report_title:
                run_query("INSERT INTO reports (report_type, title, content, date, rating, tags) VALUES (?,?,?,?,?,?)", ('روزانه', report_title, report_content, report_date, report_rating, report_tags))
                st.success("گزارش روزانه با موفقیت ثبت شد!")
                st.rerun()
        st.write("---")
        daily_reports = run_query("SELECT id, title, content, date, rating, tags FROM reports WHERE report_type='روزانه' ORDER BY date DESC", fetchall=True)
        if not daily_reports: st.info("هیچ گزارش روزانه‌ای ثبت نشده است.")
        for r_id, title, content, date, rating, tags in daily_reports:
            with st.expander(f"📅 {date} - {title} | ⭐ {rating}/10"):
                st.write(content)
                if tags: st.markdown(f"**برچسب‌ها:** {tags}")
                if st.button("🗑 حذف", key=f"dr_del_{r_id}"): run_query("DELETE FROM reports WHERE id=?", (r_id,)); st.rerun()
    
    with tb_book_report:
        st.markdown("### 📖 ثبت گزارش کتاب")
        with st.form("book_report_form", clear_on_submit=True):
            cols = st.columns(2)
            with cols[0]:
                book_title = st.text_input("عنوان کتاب:", key="book_title")
                book_author = st.text_input("نویسنده:", key="book_author")
                book_year = st.text_input("سال انتشار:", key="book_year")
            with cols[1]:
                book_publisher = st.text_input("ناشر:", key="book_publisher")
                book_pages = st.number_input("تعداد صفحات:", min_value=0, value=0, key="book_pages")
                book_rating = st.slider("امتیاز (1-10):", 1, 10, 5, key="book_rating")
            book_summary = st.text_area("چکیده/بررسی:", key="book_summary")
            book_tags = st.text_input("برچسب‌ها:", key="book_tags")
            book_date = st.text_input("تاریخ خواندن:", value=dt.date.today().strftime("%Y-%m-%d"), key="book_date")
            if st.form_submit_button("ثبت گزارش کتاب") and book_title:
                run_query("INSERT INTO reports (report_type, title, content, date, rating, tags) VALUES (?,?,?,?,?,?)", ('کتاب', book_title, f"نویسنده: {book_author}\nسال: {book_year}\nناشر: {book_publisher}\nصفحات: {book_pages}\n\n{book_summary}", book_date, book_rating, book_tags))
                st.success("گزارش کتاب با موفقیت ثبت شد!")
                st.rerun()
        st.write("---")
        book_reports = run_query("SELECT id, title, content, date, rating, tags FROM reports WHERE report_type='کتاب' ORDER BY date DESC", fetchall=True)
        if not book_reports: st.info("هیچ گزارش کتابی ثبت نشده است.")
        for r_id, title, content, date, rating, tags in book_reports:
            with st.expander(f"📖 {title} | ⭐ {rating}/10 | {date}"):
                st.write(content)
                if tags: st.markdown(f"**برچسب‌ها:** {tags}")
                if st.button("🗑 حذف", key=f"br_del_{r_id}"): run_query("DELETE FROM reports WHERE id=?", (r_id,)); st.rerun()
    
    with tb_movie_report:
        st.markdown("### 🎬 ثبت گزارش فیلم")
        with st.form("movie_report_form", clear_on_submit=True):
            cols = st.columns(2)
            with cols[0]:
                movie_title = st.text_input("عنوان فیلم:", key="movie_title")
                movie_director = st.text_input("کارگردان:", key="movie_director")
                movie_year = st.text_input("سال انتشار:", key="movie_year")
            with cols[1]:
                movie_genre = st.text_input("ژانر:", key="movie_genre")
                movie_duration = st.text_input("مدت زمان:", key="movie_duration")
                movie_rating = st.slider("امتیاز (1-10):", 1, 10, 5, key="movie_rating")
            movie_summary = st.text_area("چکیده/بررسی:", key="movie_summary")
            movie_tags = st.text_input("برچسب‌ها:", key="movie_tags")
            movie_date = st.text_input("تاریخ تماشا:", value=dt.date.today().strftime("%Y-%m-%d"), key="movie_date")
            if st.form_submit_button("ثبت گزارش فیلم") and movie_title:
                run_query("INSERT INTO reports (report_type, title, content, date, rating, tags) VALUES (?,?,?,?,?,?)", ('فیلم', movie_title, f"کارگردان: {movie_director}\nسال: {movie_year}\nژانر: {movie_genre}\nمدت: {movie_duration}\n\n{movie_summary}", movie_date, movie_rating, movie_tags))
                st.success("گزارش فیلم با موفقیت ثبت شد!")
                st.rerun()
        st.write("---")
        movie_reports = run_query("SELECT id, title, content, date, rating, tags FROM reports WHERE report_type='فیلم' ORDER BY date DESC", fetchall=True)
        if not movie_reports: st.info("هیچ گزارش فیلمی ثبت نشده است.")
        for r_id, title, content, date, rating, tags in movie_reports:
            with st.expander(f"🎬 {title} | ⭐ {rating}/10 | {date}"):
                st.write(content)
                if tags: st.markdown(f"**برچسب‌ها:** {tags}")
                if st.button("🗑 حذف", key=f"mr_del_{r_id}"): run_query("DELETE FROM reports WHERE id=?", (r_id,)); st.rerun()
    
    with tb_article_report:
        st.markdown("### 📰 ثبت گزارش مقاله")
        with st.form("article_report_form", clear_on_submit=True):
            cols = st.columns(2)
            with cols[0]:
                article_title = st.text_input("عنوان مقاله:", key="article_title")
                article_author = st.text_input("نویسنده:", key="article_author")
                article_journal = st.text_input("ژورنال/مجله:", key="article_journal")
            with cols[1]:
                article_year = st.text_input("سال انتشار:", key="article_year")
                article_doi = st.text_input("DOI:", key="article_doi")
                article_rating = st.slider("امتیاز (1-10):", 1, 10, 5, key="article_rating")
            article_summary = st.text_area("چکیده/بررسی:", key="article_summary")
            article_tags = st.text_input("برچسب‌ها:", key="article_tags")
            article_date = st.text_input("تاریخ مطالعه:", value=dt.date.today().strftime("%Y-%m-%d"), key="article_date")
            if st.form_submit_button("ثبت گزارش مقاله") and article_title:
                run_query("INSERT INTO reports (report_type, title, content, date, rating, tags) VALUES (?,?,?,?,?,?)", ('مقاله', article_title, f"نویسنده: {article_author}\nژورنال: {article_journal}\nسال: {article_year}\nDOI: {article_doi}\n\n{article_summary}", article_date, article_rating, article_tags))
                st.success("گزارش مقاله با موفقیت ثبت شد!")
                st.rerun()
        st.write("---")
        article_reports = run_query("SELECT id, title, content, date, rating, tags FROM reports WHERE report_type='مقاله' ORDER BY date DESC", fetchall=True)
        if not article_reports: st.info("هیچ گزارش مقاله‌ای ثبت نشده است.")
        for r_id, title, content, date, rating, tags in article_reports:
            with st.expander(f"📰 {title} | ⭐ {rating}/10 | {date}"):
                st.write(content)
                if tags: st.markdown(f"**برچسب‌ها:** {tags}")
                if st.button("🗑 حذف", key=f"ar_del_{r_id}"): run_query("DELETE FROM reports WHERE id=?", (r_id,)); st.rerun()
    
    with tb_stats:
        st.markdown("### 📊 آمار و تحلیل گزارش‌ها")
        total_reports = run_query("SELECT COUNT(*) FROM reports", fetch=True)[0]
        avg_rating = run_query("SELECT AVG(rating) FROM reports", fetch=True)[0] or 0
        col1, col2, col3 = st.columns(3)
        col1.metric("کل گزارش‌ها", total_reports)
        col2.metric("امتیاز متوسط", f"{avg_rating:.1f}/10")
        report_types = run_query("SELECT report_type, COUNT(*) as count FROM reports GROUP BY report_type", fetchall=True)
        if report_types:
            df_types = pd.DataFrame(report_types, columns=['نوع', 'تعداد'])
            fig_types = px.pie(df_types, values='تعداد', names='نوع', title="توزیع انواع گزارش‌ها", color_discrete_sequence=px.colors.sequential.Tealgrn)
            fig_types.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_types, use_container_width=True)
        st.markdown("### 📅 گزارش‌ها بر اساس زمان")
        report_dates = run_query("SELECT date, COUNT(*) as count FROM reports GROUP BY date ORDER BY date", fetchall=True)
        if report_dates:
            df_dates = pd.DataFrame(report_dates, columns=['تاریخ', 'تعداد'])
            fig_dates = px.line(df_dates, x='تاریخ', y='تعداد', title="تعداد گزارش‌ها در طول زمان", markers=True, color_discrete_sequence=['#deff9a'])
            fig_dates.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_dates, use_container_width=True)

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
            desc = st.text_input("توضیحات:")
            trans_date = st.text_input("تاریخ:", value=dt.date.today().strftime("%Y-%m-%d"))
            if st.form_submit_button("ثبت تراکنش") and amt > 0:
                run_query("INSERT INTO fin_transactions (acc_id, type, amount, category, date, desc) VALUES (?,?,?,?,?,?)", (acc_sel, typ, amt, cat, trans_date, desc))
                st.rerun()
        st.write("---")
        trans_filter = st.selectbox("فیلتر بر اساس نوع:", ["همه", "درآمد", "هزینه"], key="trans_filter")
        if trans_filter == "همه":
            transactions = run_query("SELECT id, type, amount, category, date, desc FROM fin_transactions ORDER BY id DESC LIMIT 20", fetchall=True)
        else:
            transactions = run_query("SELECT id, type, amount, category, date, desc FROM fin_transactions WHERE type=? ORDER BY id DESC LIMIT 20", (trans_filter,), fetchall=True)
        for t_id, typ, amt, cat, date, desc in transactions:
            desc_text = f" | {desc}" if desc else ""
            st.markdown(f"{'🔴' if typ=='هزینه' else '🟢'} **{amt:,.0f} تومان** | {cat} | <small>{date}</small>{desc_text}", unsafe_allow_html=True)

    with tb_budget:
        with st.form("budget_form", clear_on_submit=True):
            st.markdown("### تعیین سقف هزینه ماهانه")
            c1, c2 = st.columns(2)
            b_cat = c1.selectbox("دسته‌بندی:", MAIN_CATEGORIES)
            b_limit = c2.number_input("حداکثر بودجه مجاز (تومان):", min_value=0.0, step=100000.0)
            if st.form_submit_button("تنظیم بودجه") and b_limit > 0:
                run_query("DELETE FROM fin_budgets WHERE category=?", (b_cat,))
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

elif menu == "⚙️ تنظیمات":
    st.markdown("<h2 style='color: #deff9a;'>⚙️ تنظیمات سیستم</h2>", unsafe_allow_html=True)
    tb_categories, tb_backup, tb_info = st.tabs(["📁 مدیریت دسته‌ها", "💾 پشتیبان‌گیری", "ℹ️ اطلاعات سیستم"])
    
    with tb_categories:
        st.markdown("### 📁 مدیریت دسته‌بندی‌های سفارشی")
        current_categories = get_user_categories()
        with st.form("categories_form", clear_on_submit=True):
            st.markdown("**دسته‌بندی‌های فعلی:**")
            for i, cat in enumerate(current_categories): st.markdown(f"{i+1}. {cat}")
            st.markdown("---")
            st.markdown("**افزودن دسته جدید:**")
            new_category = st.text_input("دسته جدید:", key="new_category")
            if st.form_submit_button("افزودن دسته") and new_category and new_category not in current_categories:
                current_categories.append(new_category)
                save_user_categories(current_categories)
                st.success(f"دسته '{new_category}' با موفقیت اضافه شد!")
                st.rerun()
            elif new_category and new_category in current_categories: st.warning("این دسته قبلا وجود دارد!")
        st.write("---")
        if current_categories:
            st.markdown("**حذف دسته:**")
            cat_to_remove = st.selectbox("دسته‌ای که می‌خواهید حذف کنید:", current_categories, key="remove_cat")
            if st.button("حذف دسته"):
                if cat_to_remove in current_categories:
                    current_categories.remove(cat_to_remove)
                    save_user_categories(current_categories)
                    st.success(f"دسته '{cat_to_remove}' حذف شد!")
                    st.rerun()
                else: st.error("دسته یافت نشد!")
    
    with tb_backup:
        st.markdown("### 💾 پشتیبان‌گیری و بازیابی")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 ایجاد پشتیبان جدید"):
                timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"backups/manual_backup_{timestamp}.db"
                shutil.copy(DB_NAME, backup_path)
                st.success(f"پشتیبان با موفقیت ایجاد شد: {backup_path}")
                st.rerun()
        with col2:
            backups = [f for f in os.listdir("backups") if f.endswith(".db")]
            if backups:
                selected_backup = st.selectbox("پشتیبان برای بازیابی:", backups, key="restore_backup")
                if st.button("🔄 بازیابی پشتیبان"):
                    st.warning("⚠️ با بازیابی پشتیبان، تمام داده‌های فعلی از بین می‌روند!")
                    if st.button("تایید بازیابی"):
                        shutil.copy(f"backups/{selected_backup}", DB_NAME)
                        st.success("پشتیبان با موفقیت بازیابی شد!")
                        st.rerun()
            else: st.info("هیچ پشتیبانی یافت نشد.")
        st.markdown("### 📋 لیست تمام پشتیبان‌ها")
        backups = sorted([f for f in os.listdir("backups") if f.endswith(".db")], reverse=True)
        for backup in backups: st.markdown(f"- {backup}")
    
    with tb_info:
        st.markdown("### ℹ️ اطلاعات سیستم")
        total_tasks = run_query("SELECT COUNT(*) FROM scheduler", fetch=True)[0]
        total_done = run_query("SELECT COUNT(*) FROM scheduler WHERE is_done=1", fetch=True)[0]
        total_pomodoro = run_query("SELECT COUNT(*) FROM pomodoro_sessions", fetch=True)[0]
        total_knowledge = run_query("SELECT COUNT(*) FROM knowledge_base", fetch=True)[0]
        total_reports = run_query("SELECT COUNT(*) FROM reports", fetch=True)[0]
        total_transactions = run_query("SELECT COUNT(*) FROM fin_transactions", fetch=True)[0]
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("کل کارها", total_tasks); st.metric("کارهای انجام شده", total_done)
        with col2: st.metric("جلسات پومودورو", total_pomodoro); st.metric("موارد دانش", total_knowledge)
        with col3: st.metric("گزارش‌ها", total_reports); st.metric("تراکنش‌ها", total_transactions)
        st.markdown("### 🗃 اطلاعات دیتابیس")
        db_size = os.path.getsize(DB_NAME) / 1024
        st.markdown(f"- اندازه دیتابیس: {db_size:.2f} کیلوبایت")
        st.markdown(f"- نام دیتابیس: {DB_NAME}")
        st.markdown("### 📊 نسخه و اطلاعات فنی")
        st.markdown("- نسخه اپلیکیشن: LifeOS Mastermind v2.0")
        st.markdown("- توسعه دهنده: هدی")
        st.markdown("- تاریخ آخرین به‌روزرسانی: 2026/06/24")
