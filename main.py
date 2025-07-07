import streamlit as st
import pandas as pd

# Konfiguracja aplikacji
st.set_page_config(page_title="Gym Progress Tracker", layout="wide")
st.title("💪 Gym Progress Tracker")

# stałe
KOLUMNY = ["Data", "Typ", "Ćwiczenie", "Serie", "Powtórzenia", "Ciężar"]

# inicjalizacja
if "workouts" not in st.session_state:
    st.session_state["workouts"] = pd.DataFrame(columns=KOLUMNY)

# funkcje
def dodaj_trening():
    st.subheader("Dodaj trening")

    with st.form("formularz_dodaj_trening"):
        data = st.date_input("Data")
        typ = st.text_input("Typ treningu (np Push A)")
        ćwiczenie = st.text_input("Nazwa ćwiczenia")
        serie = st.number_input("Liczba serii", min_value=1, max_value=10, value=3)
        powt = st.number_input("Powtórzenia", min_value=1, max_value=30, value=10)
        ciężar = st.number_input("Ciężar (kg)", min_value=0.0, step=0.5, value=50.0)

        submitted = st.form_submit_button("Dodaj trening")

        if submitted:
            nowy_wiersz = {
                "Data": data,
                "Typ": typ,
                "Ćwiczenie": ćwiczenie,
                "Serie": serie,
                "Powtórzenia": powt,
                "Ciężar": ciężar
            }
        
            st.session_state["workouts"] = pd.concat([st.session_state["workouts"], pd.DataFrame([nowy_wiersz])], ignore_index=True)
            st.success("✅ Dodano trening!")

def pokaz_trening():
    st.subheader("Twoje treningi")

    df = st.session_state["workouts"]

    if df.empty:
        st.info("Brak zapisanych treningów")
    else:
        st.dataframe(df, use_container_width=True)

def main():
    menu = st.sidebar.selectbox("Menu", ["Dodaj trening", "Zobacz trening"])

    match menu:
        case "Dodaj trening":
            dodaj_trening()
        
        case "Zobacz trening":
            pokaz_trening()


if __name__ == "__main__":
    main()