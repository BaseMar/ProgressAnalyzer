import pyodbc

class Database:
    def __init__(self, connection_string):
        self.conn = pyodbc.connect(connection_string)
        self.cursor = self.conn.cursor()

    def fetch_exercises(self):
        query = "SELECT Id, Nazwa FROM dbo.Cwiczenie"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def insert_training(self, data_treningu):
        query = "INSERT INTO dbo.Trening (Data) OUTPUT INSERTED.Id VALUES (?)"
        self.cursor.execute(query, data_treningu)
        trening_id = self.cursor.fetchone()[0]
        self.conn.commit()
        return trening_id

    def insert_training_exercise(self, trening_id, exercise_id):
        query = """
            INSERT INTO dbo.TreningCwiczenie (TreningId, CwiczenieId)
            OUTPUT INSERTED.Id
            VALUES (?, ?)
        """
        self.cursor.execute(query, trening_id, exercise_id)
        trening_cwiczenie_id = self.cursor.fetchone()[0]
        self.conn.commit()
        return trening_cwiczenie_id

    def insert_training_series(self, trening_cwiczenie_id, powtorzenia, ciezar):
        query = """
            INSERT INTO dbo.TreningSeria (TreningCwiczenieId, Powtorzenia, Ciezar)
            VALUES (?, ?, ?)
        """
        self.cursor.execute(query, trening_cwiczenie_id, powtorzenia, ciezar)
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()
