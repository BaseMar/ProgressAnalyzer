import streamlit as st
import pandas as pd

def placeholder_table():
    data = {
        "Ćwiczenie": ["Incline Press", "Pull-Up", "Dipy"],
        "Serii": [4, 4, 3],
        "Objętość": [2200, 1000, 600],
    }
    st.table(pd.DataFrame(data))
