from storage.sklad_storage import insert_body_composition, fetch_body_composition_history

class BodyCompositionController:
    def save_composition(self, data_tuple):
        insert_body_composition(data_tuple)

    def get_composition_history(self):
        return fetch_body_composition_history()
