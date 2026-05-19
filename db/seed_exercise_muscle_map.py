from __future__ import annotations

from sqlalchemy import text

from db.connection import get_engine


ROLE_FACTOR = {
    "primary": 1.0,
    "secondary": 0.5,
    "stabilizer": 0.25,
}


MAPPINGS: dict[str, list[tuple[str, str, str, float | None, str]]] = {
    "Incline Dumbell Press": [
        ("Chest", "Pectoralis major, clavicular and sternal fibers", "primary", None, "ExRx incline bench press"),
        ("Shoulders", "Anterior deltoid", "secondary", None, "ExRx incline bench press"),
        ("Triceps", "Triceps brachii", "secondary", None, "ExRx incline bench press"),
    ],
    "Low-to-High Cable Fly": [
        ("Chest", "Pectoralis major, clavicular fibers", "primary", None, "ExRx dumbbell fly / cable fly pattern"),
        ("Shoulders", "Anterior deltoid", "secondary", 0.4, "ExRx dumbbell fly"),
        ("Biceps", "Biceps brachii, short head", "stabilizer", None, "ExRx dumbbell fly"),
    ],
    "Dips": [
        ("Chest", "Pectoralis major, sternal fibers", "primary", None, "ExRx chest dip pattern"),
        ("Triceps", "Triceps brachii", "secondary", None, "ExRx chest dip pattern"),
        ("Shoulders", "Anterior deltoid", "secondary", 0.4, "ExRx chest dip pattern"),
    ],
    "Pull-Up (Overhand)": [
        ("Back", "Latissimus dorsi, teres major", "primary", None, "ExRx pull-up"),
        ("Biceps", "Biceps brachii", "secondary", None, "ExRx pull-up"),
        ("Forearms", "Brachialis, brachioradialis", "secondary", 0.4, "ExRx pull-up"),
        ("Shoulders", "Posterior deltoid", "stabilizer", None, "ExRx pull-up"),
    ],
    "One-Arm Dumbbell Row": [
        ("Back", "Latissimus dorsi, trapezius, rhomboids, teres major", "primary", None, "ExRx row pattern"),
        ("Biceps", "Biceps brachii, brachialis", "secondary", None, "ExRx row pattern"),
        ("Forearms", "Brachioradialis, wrist flexors", "secondary", 0.4, "ExRx row pattern"),
        ("Lower Back", "Erector spinae", "stabilizer", None, "ExRx row pattern"),
    ],
    "Face Pull": [
        ("Shoulders", "Posterior deltoid, external rotators", "primary", None, "ExRx external rotation / rear delt pattern"),
        ("Back", "Trapezius, rhomboids", "secondary", None, "ExRx face pull pattern"),
        ("Forearms", "Wrist flexors", "stabilizer", None, "Cable pulling grip"),
    ],
    "Lateral Raise (Dumbbell)": [
        ("Shoulders", "Lateral deltoid", "primary", None, "Lateral raise references"),
        ("Back", "Trapezius, serratus anterior", "stabilizer", None, "Lateral raise references"),
    ],
    "Cable Curl (Low Pulley)": [
        ("Biceps", "Biceps brachii", "primary", None, "ExRx barbell curl / cable curl pattern"),
        ("Forearms", "Brachialis, brachioradialis, wrist flexors", "secondary", None, "ExRx barbell curl"),
    ],
    "Cable Triceps Pushdown": [
        ("Triceps", "Triceps brachii", "primary", None, "ExRx cable pushdown"),
        ("Forearms", "Wrist flexors", "stabilizer", None, "ExRx cable pushdown"),
    ],
    "Leg Press": [
        ("Legs", "Quadriceps, hamstrings", "primary", None, "Mayo Clinic leg press"),
        ("Glutes", "Gluteus maximus", "secondary", None, "Mayo Clinic leg press"),
        ("Calves", "Gastrocnemius, soleus", "secondary", 0.4, "Mayo Clinic leg press"),
    ],
    "Romanian Deadlift": [
        ("Legs", "Hamstrings", "primary", None, "RDL EMG / ExRx hinge pattern"),
        ("Glutes", "Gluteus maximus", "primary", 0.8, "RDL EMG / ExRx hinge pattern"),
        ("Lower Back", "Erector spinae", "stabilizer", 0.5, "RDL EMG / ExRx hinge pattern"),
        ("Forearms", "Grip and wrist flexors", "stabilizer", None, "Free-weight hinge grip"),
    ],
    "Leg Extension": [
        ("Legs", "Quadriceps femoris", "primary", None, "Leg extension references"),
    ],
    "Bulgarian Split Squat": [
        ("Legs", "Quadriceps, hamstrings", "primary", None, "Bulgarian split squat references"),
        ("Glutes", "Gluteus maximus", "secondary", 0.75, "Bulgarian split squat references"),
        ("Calves", "Gastrocnemius, soleus", "secondary", 0.35, "Bulgarian split squat references"),
        ("Abs", "Rectus abdominis", "stabilizer", None, "Single-leg balance stabilization"),
        ("Obliques", "Internal and external obliques", "stabilizer", None, "Single-leg balance stabilization"),
    ],
    "Seated Calf Raise": [
        ("Calves", "Soleus, gastrocnemius", "primary", None, "Calf raise anatomy"),
    ],
    "Flat Barbell Bench Press": [
        ("Chest", "Pectoralis major, sternal fibers", "primary", None, "Bench press references"),
        ("Shoulders", "Anterior deltoid", "secondary", None, "Bench press references"),
        ("Triceps", "Triceps brachii", "secondary", None, "Bench press references"),
    ],
    "Chest Press - machine": [
        ("Chest", "Pectoralis major", "primary", None, "Bench/chest press pattern"),
        ("Shoulders", "Anterior deltoid", "secondary", None, "Bench/chest press pattern"),
        ("Triceps", "Triceps brachii", "secondary", None, "Bench/chest press pattern"),
    ],
    "Dumbell Pullover": [
        ("Back", "Latissimus dorsi, teres major", "primary", None, "Pullover pattern"),
        ("Chest", "Pectoralis major", "secondary", 0.5, "Pullover pattern"),
        ("Triceps", "Triceps brachii, long head", "stabilizer", None, "Pullover pattern"),
    ],
    "Seated Cable Row": [
        ("Back", "Latissimus dorsi, trapezius, rhomboids, teres major", "primary", None, "ExRx row pattern"),
        ("Shoulders", "Posterior deltoid", "secondary", 0.4, "ExRx row pattern"),
        ("Biceps", "Biceps brachii, brachialis", "secondary", None, "ExRx row pattern"),
        ("Forearms", "Brachioradialis, wrist flexors", "secondary", 0.4, "ExRx row pattern"),
    ],
    "Shrugs": [
        ("Back", "Trapezius, upper fibers", "primary", None, "Shrug pattern"),
        ("Forearms", "Grip and wrist flexors", "stabilizer", None, "Free-weight grip"),
    ],
    "Straight-Arm Pulldown": [
        ("Back", "Latissimus dorsi, teres major", "primary", None, "Pulldown / shoulder extension pattern"),
        ("Triceps", "Triceps brachii, long head", "secondary", 0.35, "Shoulder extension assistance"),
        ("Abs", "Rectus abdominis", "stabilizer", None, "Cable anti-extension stabilization"),
    ],
    "Barbell French Press": [
        ("Triceps", "Triceps brachii", "primary", None, "Triceps extension references"),
        ("Shoulders", "Shoulder stabilizers", "stabilizer", None, "Overhead/lying triceps extension setup"),
    ],
    "Barbell Biceps Curl": [
        ("Biceps", "Biceps brachii", "primary", None, "ExRx barbell curl"),
        ("Forearms", "Brachialis, brachioradialis, wrist flexors", "secondary", None, "ExRx barbell curl"),
        ("Shoulders", "Anterior deltoid", "stabilizer", None, "ExRx barbell curl"),
    ],
    "Incline Bench Press": [
        ("Chest", "Pectoralis major, clavicular and sternal fibers", "primary", None, "ExRx incline bench press"),
        ("Shoulders", "Anterior deltoid", "secondary", None, "ExRx incline bench press"),
        ("Triceps", "Triceps brachii", "secondary", None, "ExRx incline bench press"),
    ],
    "Incline Machine Press": [
        ("Chest", "Pectoralis major, clavicular and sternal fibers", "primary", None, "ExRx incline bench press"),
        ("Shoulders", "Anterior deltoid", "secondary", None, "ExRx incline bench press"),
        ("Triceps", "Triceps brachii", "secondary", None, "ExRx incline bench press"),
    ],
    "Cable Crossover (high-to-low)": [
        ("Chest", "Pectoralis major, sternal fibers", "primary", None, "ExRx fly pattern"),
        ("Shoulders", "Anterior deltoid", "secondary", 0.4, "ExRx fly pattern"),
        ("Biceps", "Biceps brachii, short head", "stabilizer", None, "ExRx fly pattern"),
    ],
    "Lat Pulldown": [
        ("Back", "Latissimus dorsi, teres major", "primary", None, "ExRx pulldown / pull-up pattern"),
        ("Biceps", "Biceps brachii, brachialis", "secondary", None, "ExRx pulldown / pull-up pattern"),
        ("Forearms", "Brachioradialis, wrist flexors", "secondary", 0.4, "ExRx pulldown / pull-up pattern"),
    ],
    "Barbell Row": [
        ("Back", "Latissimus dorsi, trapezius, rhomboids, teres major", "primary", None, "ExRx bent-over row"),
        ("Shoulders", "Posterior deltoid", "secondary", 0.4, "ExRx bent-over row"),
        ("Biceps", "Biceps brachii, brachialis", "secondary", None, "ExRx bent-over row"),
        ("Forearms", "Brachioradialis, wrist flexors", "secondary", 0.4, "ExRx bent-over row"),
        ("Lower Back", "Erector spinae", "stabilizer", 0.5, "ExRx bent-over row"),
    ],
    "Reverse Pec Deck": [
        ("Shoulders", "Posterior deltoid", "primary", None, "Rear delt fly pattern"),
        ("Back", "Trapezius, rhomboids, infraspinatus, teres minor", "secondary", None, "Rear delt fly pattern"),
    ],
    "Cable Lateral Raise": [
        ("Shoulders", "Lateral deltoid", "primary", None, "Cable lateral raise references"),
        ("Back", "Trapezius, serratus anterior", "stabilizer", None, "Cable lateral raise references"),
    ],
    "Hammer Curl": [
        ("Forearms", "Brachioradialis", "primary", None, "Curl grip EMG / hammer curl pattern"),
        ("Biceps", "Biceps brachii, brachialis", "secondary", 0.75, "Curl grip EMG / hammer curl pattern"),
    ],
    "Overhead Extension": [
        ("Triceps", "Triceps brachii, long head emphasis", "primary", None, "Overhead triceps extension references"),
        ("Shoulders", "Shoulder stabilizers", "stabilizer", None, "Overhead triceps extension references"),
    ],
    "Hack Machine": [
        ("Legs", "Quadriceps, hamstrings", "primary", None, "ExRx hack squat"),
        ("Glutes", "Gluteus maximus", "secondary", None, "ExRx hack squat"),
        ("Calves", "Soleus, gastrocnemius", "secondary", 0.4, "ExRx hack squat"),
    ],
    "Lying Leg Curl": [
        ("Legs", "Hamstrings", "primary", None, "Lying leg curl references"),
        ("Calves", "Gastrocnemius", "secondary", 0.4, "Lying leg curl references"),
    ],
    "Barbell Upright Row": [
        ("Shoulders", "Lateral deltoid", "primary", None, "Upright row pattern"),
        ("Back", "Trapezius, upper fibers", "secondary", None, "Upright row pattern"),
        ("Biceps", "Biceps brachii, brachialis", "secondary", 0.35, "Upright row pattern"),
        ("Forearms", "Brachioradialis, wrist flexors", "secondary", 0.35, "Upright row pattern"),
    ],
    "Deadlift": [
        ("Lower Back", "Erector spinae", "primary", None, "ExRx deadlift"),
        ("Glutes", "Gluteus maximus", "primary", None, "ExRx deadlift analysis"),
        ("Legs", "Quadriceps, hamstrings, adductor magnus", "secondary", 0.75, "ExRx deadlift analysis"),
        ("Back", "Trapezius, latissimus dorsi", "stabilizer", 0.4, "ExRx deadlift"),
        ("Forearms", "Grip and wrist flexors", "stabilizer", None, "Free-weight grip"),
    ],
    "Narrow Barbell Bench Press": [
        ("Triceps", "Triceps brachii", "primary", None, "ExRx close-grip bench press"),
        ("Chest", "Pectoralis major, sternal fibers", "secondary", None, "ExRx close-grip bench press"),
        ("Shoulders", "Anterior deltoid", "secondary", None, "ExRx close-grip bench press"),
    ],
    "Flat Dumbell Bench Press": [
        ("Chest", "Pectoralis major, sternal fibers", "primary", None, "Bench press references"),
        ("Shoulders", "Anterior deltoid", "secondary", None, "Bench press references"),
        ("Triceps", "Triceps brachii", "secondary", None, "Bench press references"),
    ],
    "Pec Dec": [
        ("Chest", "Pectoralis major, sternal fibers", "primary", None, "Machine fly references"),
        ("Shoulders", "Anterior deltoid", "secondary", 0.35, "Machine fly references"),
    ],
    "Chest-Supported Row": [
        ("Back", "Latissimus dorsi, trapezius, rhomboids, teres major", "primary", None, "ExRx row pattern"),
        ("Shoulders", "Posterior deltoid", "secondary", 0.4, "ExRx row pattern"),
        ("Biceps", "Biceps brachii, brachialis", "secondary", None, "ExRx row pattern"),
        ("Forearms", "Brachioradialis, wrist flexors", "secondary", 0.4, "ExRx row pattern"),
    ],
    "Preacher Curls": [
        ("Biceps", "Biceps brachii, brachialis", "primary", None, "Curl references"),
        ("Forearms", "Brachioradialis, wrist flexors", "secondary", 0.5, "Curl references"),
    ],
    "MIlitary Press": [
        ("Shoulders", "Anterior and lateral deltoid", "primary", None, "Overhead press pattern"),
        ("Triceps", "Triceps brachii", "secondary", None, "Overhead press pattern"),
        ("Chest", "Pectoralis major, clavicular fibers", "stabilizer", None, "Overhead press pattern"),
        ("Abs", "Rectus abdominis", "stabilizer", None, "Standing overhead stabilization"),
        ("Lower Back", "Erector spinae", "stabilizer", None, "Standing overhead stabilization"),
    ],
    "Low to High Cable Fly": [
        ("Chest", "Pectoralis major, clavicular fibers", "primary", None, "ExRx fly pattern"),
        ("Shoulders", "Anterior deltoid", "secondary", 0.4, "ExRx fly pattern"),
        ("Biceps", "Biceps brachii, short head", "stabilizer", None, "ExRx fly pattern"),
    ],
    "Dumbbell Walking Lunges": [
        ("Legs", "Quadriceps, hamstrings", "primary", None, "Lunge pattern"),
        ("Glutes", "Gluteus maximus", "primary", 0.8, "Lunge pattern"),
        ("Calves", "Gastrocnemius, soleus", "secondary", 0.4, "Lunge pattern"),
        ("Abs", "Rectus abdominis", "stabilizer", None, "Loaded carry/lunge stabilization"),
        ("Obliques", "Internal and external obliques", "stabilizer", None, "Loaded carry/lunge stabilization"),
        ("Forearms", "Grip and wrist flexors", "stabilizer", None, "Dumbbell grip"),
    ],
    "Standed Calf Raises": [
        ("Calves", "Gastrocnemius, soleus", "primary", None, "Standing calf raise pattern"),
    ],
    "Hip thrust": [
        ("Glutes", "Gluteus maximus", "primary", None, "ExRx hip thrust"),
        ("Legs", "Hamstrings, quadriceps", "secondary", None, "ExRx hip thrust"),
        ("Lower Back", "Erector spinae", "stabilizer", None, "ExRx hip thrust"),
        ("Abs", "Rectus abdominis", "stabilizer", None, "ExRx hip thrust"),
        ("Obliques", "Internal and external obliques", "stabilizer", None, "ExRx hip thrust"),
    ],
    "Barbell Squats": [
        ("Legs", "Quadriceps, hamstrings, adductor magnus", "primary", None, "Squat pattern"),
        ("Glutes", "Gluteus maximus", "primary", 0.8, "Squat pattern"),
        ("Lower Back", "Erector spinae", "stabilizer", 0.5, "Squat stabilization"),
        ("Abs", "Rectus abdominis", "stabilizer", None, "Squat stabilization"),
        ("Obliques", "Internal and external obliques", "stabilizer", None, "Squat stabilization"),
        ("Calves", "Gastrocnemius, soleus", "secondary", 0.35, "Squat pattern"),
    ],
    "Hammer Grip Dumbbell Press": [
        ("Chest", "Pectoralis major", "primary", None, "Dumbbell press pattern"),
        ("Triceps", "Triceps brachii", "secondary", None, "Dumbbell press pattern"),
        ("Shoulders", "Anterior deltoid", "secondary", None, "Dumbbell press pattern"),
        ("Forearms", "Grip and wrist flexors", "stabilizer", None, "Dumbbell grip"),
    ],
    "Dumbell Shoulder Press": [
        ("Shoulders", "Anterior and lateral deltoid", "primary", None, "Shoulder press pattern"),
        ("Triceps", "Triceps brachii", "secondary", None, "Shoulder press pattern"),
        ("Chest", "Pectoralis major, clavicular fibers", "stabilizer", None, "Shoulder press pattern"),
        ("Abs", "Rectus abdominis", "stabilizer", None, "Dumbbell overhead stabilization"),
        ("Lower Back", "Erector spinae", "stabilizer", None, "Dumbbell overhead stabilization"),
    ],
    "Rear Delt Row": [
        ("Shoulders", "Posterior deltoid", "primary", None, "Rear delt row pattern"),
        ("Back", "Trapezius, rhomboids", "secondary", None, "Rear delt row pattern"),
        ("Biceps", "Biceps brachii, brachialis", "secondary", 0.35, "Rear delt row pattern"),
        ("Forearms", "Brachioradialis, wrist flexors", "secondary", 0.35, "Rear delt row pattern"),
    ],
    "Incline Dumbell Curl": [
        ("Biceps", "Biceps brachii", "primary", None, "Curl references"),
        ("Forearms", "Brachialis, brachioradialis", "secondary", 0.5, "Curl references"),
    ],
    "Incline Barbell Press": [
        ("Chest", "Pectoralis major, clavicular and sternal fibers", "primary", None, "ExRx incline bench press"),
        ("Shoulders", "Anterior deltoid", "secondary", None, "ExRx incline bench press"),
        ("Triceps", "Triceps brachii", "secondary", None, "ExRx incline bench press"),
    ],
    "Cable Crunches": [
        ("Abs", "Rectus abdominis", "primary", None, "ExRx cable crunch"),
        ("Obliques", "Internal and external obliques", "secondary", None, "ExRx cable crunch"),
    ],
}


def main() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS exercise_muscle_map (
                    id BIGSERIAL PRIMARY KEY,
                    exercise_id INTEGER NOT NULL REFERENCES exercises(exercise_id) ON DELETE CASCADE,
                    muscle_group TEXT NOT NULL,
                    muscle_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('primary', 'secondary', 'stabilizer')),
                    set_factor NUMERIC(4, 2) NOT NULL CHECK (set_factor > 0 AND set_factor <= 1),
                    source_note TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE (exercise_id, muscle_group)
                )
                """
            )
        )

        exercise_ids = dict(
            conn.execute(text("SELECT exercise_name, exercise_id FROM exercises")).fetchall()
        )
        missing = sorted(set(MAPPINGS).difference(exercise_ids))
        if missing:
            raise RuntimeError(f"Missing exercises in database: {missing}")

        mapped_ids = [exercise_ids[name] for name in MAPPINGS]
        conn.execute(
            text("DELETE FROM exercise_muscle_map WHERE exercise_id = ANY(:exercise_ids)"),
            {"exercise_ids": mapped_ids},
        )

        for exercise_name, targets in MAPPINGS.items():
            exercise_id = exercise_ids[exercise_name]
            for muscle_group, muscle_name, role, set_factor, source_note in targets:
                conn.execute(
                    text(
                        """
                        INSERT INTO exercise_muscle_map
                            (exercise_id, muscle_group, muscle_name, role, set_factor, source_note)
                        VALUES
                            (:exercise_id, :muscle_group, :muscle_name, :role, :set_factor, :source_note)
                        """
                    ),
                    {
                        "exercise_id": exercise_id,
                        "muscle_group": muscle_group,
                        "muscle_name": muscle_name,
                        "role": role,
                        "set_factor": set_factor if set_factor is not None else ROLE_FACTOR[role],
                        "source_note": source_note,
                    },
                )

    print(f"Seeded {sum(len(targets) for targets in MAPPINGS.values())} muscle mappings for {len(MAPPINGS)} exercises.")


if __name__ == "__main__":
    main()
