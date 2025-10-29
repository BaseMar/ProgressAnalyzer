LAST_SESSIONS = """
SELECT TOP 10
    SessionID,
    SessionDate,
    COUNT(DISTINCT ExerciseID) AS Exercises,
    SUM(Repetitions * Weight) AS TotalVolume
FROM TrainingLogs
GROUP BY SessionID, SessionDate
ORDER BY SessionDate DESC
"""
