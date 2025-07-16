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

    def fetch_training_history(self):
        self.cursor.execute("""
        SELECT 
            t.Id AS TreningId,
            t.Data,
            c.Nazwa AS Cwiczenie,
            ts.Powtorzenia,
            ts.Ciezar
        FROM dbo.Trening t
        JOIN dbo.TreningCwiczenie tc ON t.Id = tc.TreningId
        JOIN dbo.Cwiczenie c ON tc.CwiczenieId = c.Id
        JOIN dbo.TreningSeria ts ON tc.Id = ts.TreningCwiczenieId
        ORDER BY t.Data DESC, t.Id DESC
    """)
        return self.cursor.fetchall()
    
    def insert_body_measurements(self, data, waga, klatka, talia, brzuch, biodra, udo, lydka, ramie,
                             masa_miesniowa, masa_tluszczowa, tkanka_tluszczowa, woda, notatka):
        self.cursor.execute("""
            INSERT INTO dbo.PomiaryCiala
            (DataPomiaru, Waga, KlatkaPiersiowa, Talia, Brzuch, Biodra, Udo, Lydka, Ramie,
            MasaMiesniowa, MasaTluszczowa, TkankaTluszczowa, WodaCiala, Notatka)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data, waga, klatka, talia, brzuch, biodra, udo, lydka, ramie,
            masa_miesniowa, masa_tluszczowa, tkanka_tluszczowa, woda, notatka)
        self.conn.commit()

    def fetch_body_measurements(self):
        query = "SELECT DataPomiaru, Waga, KlatkaPiersiowa, Talia, Biodra, Udo, Lydka, Ramie, MasaMiesniowa, MasaTluszczowa, TkankaTluszczowa, WodaCiala FROM PomiaryCiala ORDER BY DataPomiaru"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        columns = [column[0] for column in self.cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    def fetch_exercise_groups(self):
        query = "SELECT Id, Nazwa, PartieGlowne, PartieSzczeg FROM dbo.Cwiczenie"
        self.cursor.execute(query)
        return self.cursor.fetchall()