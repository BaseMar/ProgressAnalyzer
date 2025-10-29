import streamlit as st

def metric_card(label, value, delta):
    st.metric(label, value, delta)
