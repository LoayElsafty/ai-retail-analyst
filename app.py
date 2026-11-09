"""Streamlit front end: streamlit run app.py"""
import streamlit as st

from analyst import Analyst, chart
from analyst.llm import default_llm

st.set_page_config(page_title="Ask the retail data", page_icon="📊", layout="centered")
st.title("Ask the retail data")
st.caption(
    "TheLook e-commerce, 2023–2025 · 86,904 order items · every answer shows the SQL behind it. "
    "Metrics follow the retail performance pack's definitions."
)

EXAMPLES = [
    "What were net sales and gross margin by year?",
    "Which 5 categories made the most gross profit in 2025?",
    "Which traffic source brings the highest average order value?",
    "How did the return rate change month by month in 2025?",
]


@st.cache_resource
def analyst():
    return Analyst(default_llm())


q = st.text_input("Your question", placeholder=EXAMPLES[0])
st.write("Try: " + " · ".join(f"*{e}*" for e in EXAMPLES))

if q:
    with st.spinner("Writing and checking the query…"):
        res = analyst().ask(q)
    if not res.ok:
        st.error(f"Couldn't answer that: {res.error}")
    else:
        st.subheader(res.answer)
        if res.assumption:
            st.info(f"Assumption: {res.assumption}")
        fig = chart(res)
        if fig:
            st.pyplot(fig)
        st.dataframe(res.data, hide_index=True, width="stretch")
        with st.expander(f"SQL used (attempt {res.attempts})"):
            st.code(res.sql, language="sql")
