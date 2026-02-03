# Gym Progress Dashboard

A personal strength training & body composition analytics dashboard built with **Streamlit**.   Designed for lifters who want data-driven insights, not just workout logs.

The app tracks training volume, intensity, exercise progress, fatigue, and body metrics — with a strong focus on long-term trends, recomposition quality, and proportions.

---

## Features

### Training & Progress
- Workout session overview (volume, intensity, duration)
- Exercise-level strength progress
- Per-body-part training distribution
- Estimated 1RM trends
- Consistency & exposure-based progress tracking

### Advanced Analytics
- Fatigue & recovery monitoring
- Progress vs exposure insights
- Plateau and regression detection
- Training balance across body parts

### Body Metrics
- Body composition tracking (weight, muscle mass, fat mass, water mass)
- Body measurements tracking (waist, chest, hips, thighs, arms, calves)
- Trend-based analysis instead of single measurements
- Proportion ratios (e.g. chest/waist, thigh/waist)
- Recomposition quality insights (lean mass vs total weight change)

### UX & Design
- Dark UI
- KPI-first layout (current / average / best)
- Dropdown-based metric selection to avoid chart overload
- Clean visual hierarchy

---

## Screenshots

- Main Dashboard
![Main Dashboard](screenshots\Dashboard_1.png)](https://github.com/BaseMar/ProgressAnalyzer/blob/945fbc9d157bed43a5318eaede45ebae96345f11/screenshots/Dashboard_1.png)
![History Session](screenshots\Dashboard_2.png)

- Analytics View
![Analytics Tab Part 1](screenshots\Analytics_1.png)
![Analytics Tab Part 2](screenshots\Analytics_2.png)
![Analytics Tab Part 3](screenshots\Analytics_3.png)

- Body Metrics View  
![Body Metrics Part 1](screenshots\Body_Metrics_1.png)
![Body Metrics Part 2](screenshots\Body_Metrics_2.png)
![Body Metrics Part 3](screenshots\Body_Metrics_3.png)

---

## Application Sections

### Main Dashboard
High-level training overview:
- Avg intensity
- Sessions per week
- Volume & duration trends
- Session history

### Exercises
- Strength progress per exercise
- Volume and exposure tracking
- Exercise-specific trends

### Body Parts
- Volume distribution per body part
- Avg estimated 1RM per body part
- Training balance overview

### Analytics
- Fatigue & recovery analysis
- Strength progress quality
- Plateaus vs improving lifts
- Basic insights

### Body Metrics
- Body composition trends
- Body measurements trends
- Proportion analysis
- Recomposition quality
- Manual measurement input

---

## Tech Stack

- **Python**
- **Streamlit** – UI & app framework
- **Pandas** – data processing
- **Plotly** – interactive charts
- **SQLAlchemy** – database access
- **SQL (MS SQL / SQLite)** – persistent storage

---

## Data Model

### Training
- `WorkoutSessions`
- `WorkoutExercises`
- `WorkoutSets`
- `Exercises`

### Body Tracking
- `BodyComposition`  
  *(weight, muscle mass, fat mass, water mass, body fat %)*
- `BodyMeasurements`  
  *(waist, chest, abdomen, hips, thighs, arms, calves)*

---

## How to Run

### Clone repository
```bash
git clone https://github.com/BaseMar/ProgressAnalyzer.git
cd gym-progress-dashboard
