import streamlit as st
import pandas as pd
import plotly.express as px
import re
from sqlalchemy import create_engine, text, inspect
from langchain_community.chat_models import ChatOllama
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate

OLLAMA_MODEL = "llama3"

st.set_page_config(page_title="Pro SQL Multi-Agent System", layout="wide")
st.title("🏛 AI SQL Analytics System (Multi-Agent Pro)")

with st.sidebar:
    st.header("⚙️ Конфигурация")
    lang = st.selectbox("Язык ответа", ["Русский", "English"])
    db_dialect = st.selectbox("СУБД", ["SQLite", "PostgreSQL"])
    db_file = st.file_uploader("Загрузите базу .db", type=["db", "sqlite"])

if db_file:
    path = "current_db.db"
    with open(path, "wb") as f:
        f.write(db_file.getbuffer())
    st.session_state.db_path = path


@st.cache_resource
def load_llm():
    return ChatOllama(model=OLLAMA_MODEL, base_url="http://localhost:11434", temperature=0)


llm = load_llm()



def run_multi_agent_pipeline(user_query, db_path):
    db = SQLDatabase.from_uri(f"sqlite:///{db_path}")

    with st.status("🕵️ Архитектор изучает структуру таблиц...") as status:
        schema_info = db.get_table_info()
        status.update(label="Схема получена", state="complete")

    with st.status("💻 Программист генерирует SQL...") as status:
        sql_prompt = ChatPromptTemplate.from_template("""
        Ты — Агент-Программист SQL для {dialect}. 
        Твоя задача: написать SQL-запрос на основе схемы.

        ПРАВИЛА:
        1. Если вопрос НЕ КАСАЕТСЯ данных базы (рецепты, угрозы, общие вопросы) — ответь ТОЛЬКО: ERROR: OUT_OF_CONTEXT
        2. Если вопрос по теме — выдай ТОЛЬКО чистый SQL-код внутри тегов [SQL] и [/SQL].

        СХЕМА: {schema}
        ЗАПРОС: {query}
        """)

        chain = sql_prompt | llm
        response = chain.invoke({"schema": schema_info, "query": user_query, "dialect": db_dialect}).content

        if "OUT_OF_CONTEXT" in response.upper():
            status.update(label="Запрос отклонен", state="error")
            return {"error": "Извините, в базе данных нет информации для ответа на этот вопрос."}

        sql_match = re.search(r"\[SQL\](.*?)\[/SQL\]", response, re.DOTALL)
        executed_sql = sql_match.group(1).strip() if sql_match else response.strip()
        executed_sql = executed_sql.replace("```sql", "").replace("```", "").strip()

        status.update(label="SQL подготовлен", state="complete")

    try:
        engine = create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            df = pd.read_sql_query(text(executed_sql), conn)
    except Exception as e:
        return {"error": f"Ошибка выполнения SQL: {e}", "sql_debug": executed_sql}

    with st.status("📊 Аналитик готовит финальный отчет...") as status:
        analysis_prompt = ChatPromptTemplate.from_template("""
        Ты — Агент-Аналитик. Твоя задача: ответить пользователю на основе данных.
        ЯЗЫК: {lang}
        ДАННЫЕ: {data}
        ВОПРОС: {query}
        Сделай краткий и четкий вывод.
        """)

        analyst_chain = analysis_prompt | llm
        final_answer = analyst_chain.invoke({"data": df.to_string(), "query": user_query, "lang": lang}).content
        status.update(label="Анализ завершен", state="complete")

    return {"sql": executed_sql, "data": df, "answer": final_answer}


if "db_path" in st.session_state:
    with st.expander("📂 Структура базы данных (Превью)"):
        engine = create_engine(f"sqlite:///{st.session_state.db_path}")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if tables:
            st.write(f"Доступные таблицы: {', '.join(tables)}")
            selected_t = st.selectbox("Выберите таблицу для просмотра:", tables)
            st.dataframe(pd.read_sql_query(f"SELECT * FROM {selected_t} LIMIT 5", engine))

    user_input = st.text_input("Задайте вопрос к данным (или попробуйте спросить рецепт):")

    if st.button("Запустить анализ"):
        if user_input:
            result = run_multi_agent_pipeline(user_input, st.session_state.db_path)

            if "error" in result:
                st.warning(f"🤖 {result['error']}")
                if "sql_debug" in result:
                    st.code(result["sql_debug"], language="sql")
            else:
                st.success("Ответ агента:")
                st.write(result["answer"])

                with st.expander("🛠 Посмотреть SQL-запрос Программиста"):
                    st.code(result["sql"], language="sql")

                st.subheader("🔢 Извлеченные данные:")
                st.dataframe(result["data"], use_container_width=True)

                df = result["data"]
                num_cols = df.select_dtypes(include=['number']).columns
                if len(num_cols) > 0 and not df.empty:
                    st.subheader("📈 Визуализация:")
                    fig = px.bar(df, x=df.columns[0], y=num_cols[0], color_discrete_sequence=['#00CC96'])
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Пожалуйста, введите запрос.")
else:
    st.info("Загрузите файл базы данных в боковом меню, чтобы начать.")
