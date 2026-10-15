"""Explicit synthetic contracts, never used by live publishing."""
from autopilot.science import make_fact

ROW = {
    "pl_name": "SIMULATION b", "hostname": "SIMULATION", "pl_orbper": 0.5,
    "pl_orbpererr1": 0.001, "pl_orbpererr2": -0.001, "pl_orbperlim": 0,
    "pl_controv_flag": 0, "default_flag": 1,
    "pl_refname": '<a href="https://ui.adsabs.harvard.edu/abs/SIMULATION-NOT-A-PUBLICATION">Synthetic fixture, not a citation</a>',
}


class SimulatedArchive:
    def select(self, used):
        from autopilot.science import Unverified
        if ROW["pl_name"] in used:
            raise Unverified("Fixture già usata")
        fact = make_fact(dict(ROW), "SIMULATION ONLY — NO SCIENTIFIC EVIDENCE")
        fact["simulation"] = True
        fact["content"]["caption"] = "SIMULAZIONE TECNICA — dati sintetici, nessuna citazione scientifica. Non pubblicare."
        return fact


class SimulatedInstagram:
    user_id = "100"
    token = "not-a-real-token"

    def __init__(self):
        self.publishes = 0
        self.uploaded = False

    def identity(self):
        return {"user_id": self.user_id, "username": "simulation"}

    def create(self, caption):
        return "200", "https://rupload.facebook.com/ig-api-upload/v24.0/200"

    def upload(self, uri, path):
        assert path.stat().st_size > 0
        self.uploaded = True

    def wait_ready(self, container):
        return "FINISHED"

    def publish(self, container):
        self.publishes += 1
        return "300"
