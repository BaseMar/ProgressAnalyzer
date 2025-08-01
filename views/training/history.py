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
        st.subheader(f"Objętość treningowa - {title}")

        for muscle_group, series in volume_dict.items():
            series = series.sort_index()
            all_dates = pd.date_range(start=date_range[0], end=date_range[1], freq='D')
            series = series.reindex(all_dates, fill_value=0)
            series = series.infer_objects(copy=False)

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

        df = df.copy()
        df["Data"] = pd.to_datetime(df["Data"])
        df["Tydzien"] = df["Data"].dt.to_period("W").apply(lambda p: p.start_time)
        df["Tydzien"] = df["Tydzien"].dt.date
        df["Volume"] = df["Powtorzenia"] * df["Ciezar"]

        exercise_list = df["Cwiczenie"].unique()
        selected_exercise = st.selectbox("Wybierz ćwiczenie:", exercise_list, index=0)
        ex_df = df[df["Cwiczenie"] == selected_exercise]

        if ex_df.empty:
            st.warning(f"Brak danych dla {selected_exercise}")
            return

        weekly_avg = ex_df.groupby("Tydzien")["Ciezar"].mean().reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=weekly_avg["Tydzien"],
            y=weekly_avg["Ciezar"],
            mode='lines+markers',
            name="Średni ciężar"
        ))
        fig.update_layout(
            title=selected_exercise,
            xaxis=dict(title="Tydzień", tickformat="%d-%m", tickmode="auto"),
            yaxis_title="Średni ciężar (kg)",
            template="plotly_white",
            height=350
        )
        st.plotly_chart(fig, use_container_width=True)

    def display_weekly_series_report(self, df, exercise_groups):
        st.subheader("Raport tygodniowy – serie, ciężary, progresja")

        df = df.copy()
        df["Data"] = pd.to_datetime(df["Data"])
        df["Tydzień"] = df["Data"] - pd.to_timedelta(df["Data"].dt.weekday, unit="d")
        df["Tydzień"] = df["Tydzień"].dt.normalize()

        df["Volume"] = df["Ciezar"] * df["Powtorzenia"]

        exercise_stats = df.groupby(["Tydzień", "Cwiczenie"]).agg({
            "Ciezar": ["mean", "max"],
            "Powtorzenia": "sum",
            "Volume": "sum"
        }).reset_index()

        exercise_stats.columns = ["Tydzień", "Cwiczenie", "Średni ciężar", "Maks. ciężar", "Suma powtórzeń", "Objętość"]
        exercise_stats["Wskaźnik progresji"] = exercise_stats.groupby("Cwiczenie")["Średni ciężar"].pct_change().fillna(0) * 100
        serie_counts = df.groupby(["Tydzień", "Cwiczenie"]).size().reset_index(name="Liczba serii")
        full_df = pd.merge(exercise_stats, serie_counts, on=["Tydzień", "Cwiczenie"])
        tygodnie = full_df["Tydzień"].drop_duplicates().sort_values(ascending=False).dt.strftime("%Y-%m-%d")
        selected_week = st.selectbox("Wybierz tydzień:", tygodnie)
        selected_df = full_df[full_df["Tydzień"].dt.strftime("%Y-%m-%d") == selected_week]
        selected_df = selected_df.sort_values("Objętość", ascending=False)
        selected_df = selected_df.copy()
        selected_df["Tydzień"] = selected_df["Tydzień"].dt.strftime("%Y-%m-%d")

        st.markdown("### Ćwiczenia – metryki tygodniowe")
        st.dataframe(selected_df.style.format({
            "Średni ciężar": "{:.1f}",
            "Maks. ciężar": "{:.1f}",
            "Objętość": "{:.0f}",
            "Suma powtórzeń": "{:.0f}",
            "Liczba serii": "{:.0f}",
            "Wskaźnik progresji": "{:+.1f}%"
        }), use_container_width=True)

        df["PartieGlowne"] = df["Cwiczenie"].map(exercise_groups).fillna("")
        df["PartieGlowne"] = df["PartieGlowne"].str.split(r",\s*")
        df = df.explode("PartieGlowne")
        group_series = df.groupby(["Tydzień", "PartieGlowne"]).size().unstack(fill_value=0)
        group_series.index = group_series.index.strftime("%Y-%m-%d")
        
        st.markdown("### Grupy mięśniowe – liczba serii")
        st.dataframe(group_series.loc[selected_week].sort_values(ascending=False), use_container_width=True)
