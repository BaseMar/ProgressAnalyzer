import streamlit as st
import pandas as pd
from analytics.training_analysis import filter_training_data
from analytics. volume_analysis import analyze_training_volume
from storage.training_storage import load_training_history
import plotly.graph_objects as go

class TrainingHistoryView:
    def display_training_history(self):
        st.title("Historia treningów")

        raw_data = load_training_history()
        if not raw_data:
            st.info("Brak zapisanych treningów")
            return
        
        df = pd.DataFrame([{
        'Data': row.Data,
        'Cwiczenie': row.Cwiczenie,
        'Powtorzenia': row.Powtorzenia,
        'Ciezar': row.Ciezar} for row in raw_data])
        
        df['Data'] = pd.to_datetime(df["Data"])
        min_date, max_date = df['Data'].min(), df['Data'].max()

        date_range = st.date_input("Zakres dat:", [min_date, max_date])
        if len(date_range) != 2:
            st.info("Wybierz pełny zakres dat.")
            return
        date_start, date_end = [pd.to_datetime(d) for d in date_range]

        exercises = sorted(df['Cwiczenie'].unique())
        selected_exercise = st.selectbox("Ćwiczenie (opcjonalnie):", ["Wszystkie"] + exercises)

        filtered_df = filter_training_data(df, date_start, date_end, selected_exercise)

        if filtered_df.empty:
            st.warning("Brak treningów dla wybranych filtrów.")
            return

        for date, group in filtered_df.groupby('Data'):
            st.subheader(date.strftime('%Y-%m-%d'))
            for exercise, ex_group in group.groupby('Cwiczenie'):
                series_str = " | ".join(
                    f"Seria: {row.Powtorzenia} powt., {row.Ciezar} kg"
                    for i, row in ex_group.iterrows()
                )
                st.markdown(f"**{exercise}** ➔ {series_str}")
            st.markdown("---")
    
    def display_volume_charts(self, volume_dict, title, date_range=None):
        st.subheader(f"Objętość treningowa – {title}")

        for muscle_group, series in volume_dict.items():
            series = series.sort_index()
            all_dates = pd.date_range(start=date_range[0], end=date_range[1], freq='D')
            series = series.reindex(all_dates, fill_value=0)

            weekly_series = series.resample("W-MON").sum()
            status = analyze_training_volume(weekly_series)

            color = {
                "Objętość stabilna": "green",
                "Możliwe niedotrenowanie – objętość spadła >20%": "orange",
                "Ryzyko przetrenowania – gwałtowny wzrost objętości >30%": "red",
                "Za mało danych do analizy": "gray",
                "Brak wcześniejszych danych do porównania": "gray"
            }.get(status, "black")

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=series.index,
                y=series.values,
                name=muscle_group,
            ))

            fig.update_layout(
                title=muscle_group,
                xaxis=dict(
                    title="Data",
                    tickformat="%d-%m",
                    tickmode="auto"
                ),
                yaxis_title="Objętość (powt. x ciężar)",
                bargap=0.3,
                height=400,
                margin=dict(l=40, r=40, t=40, b=40),
                template="plotly_white"
            )

            col1, col2 = st.columns([4, 1])
            with col1:
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.markdown(f"<h4>Status:</h4><p style='color:{color}; font-weight:bold;'>{status}</p>", unsafe_allow_html=True)

    def display_strength_progression(self, df):
        st.subheader("Progresja siłowa")

        df["Data"] = pd.to_datetime(df["Data"])
        df["Tydzien"] = df["Data"].dt.to_period("W").apply(lambda r: r.start_time)
        df["Volume"] = df["Powtorzenia"] * df["Ciezar"]

        exercises = sorted(df['Cwiczenie'].unique())
        selected = st.multiselect("Wybierz ćwiczenia:", exercises, default=exercises[:1])

        for ex in selected:
            df_ex = df[df["Cwiczenie"] == ex]

            if df_ex.empty:
                st.warning(f"Brak danych dla {ex}")
                continue

            grouped = df_ex.groupby("Tydzien").agg({
                "Ciezar": ["mean", "max"],
                "Volume": "sum",
                "Powtorzenia": "sum"
            }).reset_index()

            grouped.columns = ["Tydzien", "Sredni_ciezar", "Max_ciezar", "Objętość", "Powtórzenia"]

            grouped["% zmiana (średni ciężar)"] = grouped["Sredni_ciezar"].pct_change().fillna(0) * 100

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=grouped["Tydzien"],
                y=grouped["Sredni_ciezar"],
                name="Średni ciężar",
                mode="lines+markers",
                line=dict(color="royalblue")
            ))
            fig.add_trace(go.Scatter(
                x=grouped["Tydzien"],
                y=grouped["Max_ciezar"],
                name="Maksymalny ciężar",
                mode="lines+markers",
                line=dict(color="firebrick")
            ))

            fig.update_layout(
                title=f"{ex} – progres siłowy",
                xaxis=dict(
                    title="Tydzień",
                    tickformat="%d-%m",
                    tickmode="auto"
                ),
                yaxis_title="Ciężar (kg)",
                height=400,
                template="plotly_white"
            )

            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(grouped.style.format({
                "Sredni_ciezar": "{:.1f}",
                "Max_ciezar": "{:.1f}",
                "Objętość": "{:.0f}",
                "Powtórzenia": "{:.0f}",
                "% zmiana (średni ciężar)": "{:+.1f}%"
            }))
