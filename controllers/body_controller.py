from storage.body_storage import insert_body_measurements, fetch_body_measurements, insert_body_composition, fetch_body_composition_history

class BodyController:
    def __init__(self):
        pass

    def save_measurements(self, measurement_data: tuple):
        insert_body_measurements(measurement_data)

    def get_measurements(self):
        return fetch_body_measurements()

    def save_composition(self, data_tuple):
        insert_body_composition(data_tuple)

    def get_composition_history(self):
        return fetch_body_composition_history()
