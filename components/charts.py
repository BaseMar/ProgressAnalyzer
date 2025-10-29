import streamlit as st
import matplotlib.pyplot as plt

def placeholder_chart():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [5, 3, 6])
    ax.set_title("Wykres przykładowy")
    st.pyplot(fig)
