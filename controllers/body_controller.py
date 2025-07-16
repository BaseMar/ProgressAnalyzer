from storage.body_storage import insert_body_measurements, fetch_body_measurements

class BodyController:
    def __init__(self):
        pass

    def save_measurements(self, measurement_data: tuple):
        insert_body_measurements(measurement_data)

    def get_measurements(self):
        return fetch_body_measurements()
