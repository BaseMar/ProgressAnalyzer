import streamlit as st
import pandas as pd
import plotly.express as px

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

def pokaz_wykres():
    st.subheader("Progress ciężaru")

    df = st.session_state["workouts"]
    if df.empty:
        st.info("Brak danych do wyświetlenia")
        return
    
    lista_ćwiczeń = df["Ćwiczenie"].unique().tolist()
    if not lista_ćwiczeń:
        st.info("Brak zapisanych ćwiczeń")
        return
    
    wybrane_ćwiczenie = st.selectbox("Wybierz ćwiczenie", lista_ćwiczeń)
    df_przefiltrowane = df[df["Ćwiczenie"] == wybrane_ćwiczenie].copy()
    df_przefiltrowane["Data"] = pd.to_datetime(df_przefiltrowane["Data"])
    df_zgrupowane = df_przefiltrowane.groupby("Data")["Ciężar"].max().reset_index()
    
    df_zgrupowane["Data"] = df_zgrupowane["Data"].dt.strftime('%Y-%m-%d')
    df_zgrupowane["Progres %"] = df_zgrupowane["Ciężar"].pct_change()*100
    df_zgrupowane["Progres %"] = df_zgrupowane["Progres %"].round(1).fillna(0.0)

    fig = px.line(df_zgrupowane, x="Data", y="Ciężar", markers = True, title=f"Maksymalny ciężar - {wybrane_ćwiczenie}", labels={"Data": "Data", "Ciężar": "Ciężar (kg)"}, text="Ciężar")
    fig.update_layout(xaxis_type='category')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Tempo rozwoju (% zmiany)")
    st.dataframe(df_zgrupowane[["Data", "Ciężar", "Progres %"]], use_container_width=True)

def main():
    menu = st.sidebar.selectbox("Menu", ["Dodaj trening", "Zobacz trening", "Wykres progresu"])

    match menu:
        case "Dodaj trening":
            dodaj_trening()
        
        case "Zobacz trening":
            pokaz_trening()
        
        case "Wykres progresu":
            pokaz_wykres()


if __name__ == "__main__":
    main()