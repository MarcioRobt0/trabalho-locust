"""
Trabalho 06 — Avaliação de Desempenho de Microsserviços com Locust
Spring PetClinic Microservices

Dois perfis de carga:
  - ReadProfile  (Perfil 1 — Leitura):  GET /owners 45%, GET /owners/{id} 35%, GET /vets 15%, POST /owners 5%
  - WriteProfile (Perfil 2 — Escrita):  GET /owners 20%, GET /owners/{id} 20%, GET /vets 20%, POST /owners 40%

Endpoints via API Gateway (http://localhost:8080):
  GET  /api/customer/owners
  GET  /api/customer/owners/{id}
  GET  /api/vet/vets
  POST /api/customer/owners
"""

import random
from locust import HttpUser, task, between


# ---------------------------------------------------------------------------
# Dados para POST /owners
# ---------------------------------------------------------------------------
FIRST_NAMES = ["Ana", "Bruno", "Carlos", "Diana", "Eduardo", "Fernanda", "Gabriel", "Helena"]
LAST_NAMES  = ["Silva", "Santos", "Oliveira", "Pereira", "Costa", "Alves", "Souza", "Lima"]
CITIES      = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Salvador"]
STREETS     = ["Av. Paulista", "Rua das Flores", "Rua XV de Novembro", "Av. Brasil", "Rua da Paz"]


def random_owner_payload():
    return {
        "firstName": random.choice(FIRST_NAMES),
        "lastName":  random.choice(LAST_NAMES),
        "address":   f"{random.randint(1, 999)} {random.choice(STREETS)}",
        "city":      random.choice(CITIES),
        "telephone": f"11{random.randint(900000000, 999999999)}",
    }


# ---------------------------------------------------------------------------
# Perfil 1 — Leitura
# GET /owners      → 45%
# GET /owners/{id} → 35%
# GET /vets        → 15%
# POST /owners     →  5%
# ---------------------------------------------------------------------------
class ReadProfile(HttpUser):
    """Perfil 1 — Leitura (pesos: 45 / 35 / 15 / 5)"""

    wait_time = between(1, 3)

    @task(45)
    def get_owners(self):
        with self.client.get(
            "/api/customer/owners",
            name="GET /api/customer/owners",
            catch_response=True
        ) as response:
            if response.status_code not in (200, 204):
                response.failure(f"Status inesperado: {response.status_code}")

    @task(35)
    def get_owner_by_id(self):
        owner_id = random.randint(1, 10)
        with self.client.get(
            f"/api/customer/owners/{owner_id}",
            name="GET /api/customer/owners/{id}",
            catch_response=True
        ) as response:
            # 404 é aceitável para IDs inexistentes
            if response.status_code not in (200, 204, 404):
                response.failure(f"Status inesperado: {response.status_code}")

    @task(15)
    def get_vets(self):
        with self.client.get(
            "/api/vet/vets",
            name="GET /api/vet/vets",
            catch_response=True
        ) as response:
            if response.status_code not in (200, 204):
                response.failure(f"Status inesperado: {response.status_code}")

    @task(5)
    def post_owner(self):
        with self.client.post(
            "/api/customer/owners",
            json=random_owner_payload(),
            name="POST /api/customer/owners",
            catch_response=True
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"Status inesperado: {response.status_code}")


# ---------------------------------------------------------------------------
# Perfil 2 — Escrita
# GET /owners      → 20%
# GET /owners/{id} → 20%
# GET /vets        → 20%
# POST /owners     → 40%
# ---------------------------------------------------------------------------
class WriteProfile(HttpUser):
    """Perfil 2 — Escrita (pesos: 20 / 20 / 20 / 40)"""

    wait_time = between(1, 3)

    @task(20)
    def get_owners(self):
        with self.client.get(
            "/api/customer/owners",
            name="GET /api/customer/owners",
            catch_response=True
        ) as response:
            if response.status_code not in (200, 204):
                response.failure(f"Status inesperado: {response.status_code}")

    @task(20)
    def get_owner_by_id(self):
        owner_id = random.randint(1, 10)
        with self.client.get(
            f"/api/customer/owners/{owner_id}",
            name="GET /api/customer/owners/{id}",
            catch_response=True
        ) as response:
            if response.status_code not in (200, 204, 404):
                response.failure(f"Status inesperado: {response.status_code}")

    @task(20)
    def get_vets(self):
        with self.client.get(
            "/api/vet/vets",
            name="GET /api/vet/vets",
            catch_response=True
        ) as response:
            if response.status_code not in (200, 204):
                response.failure(f"Status inesperado: {response.status_code}")

    @task(40)
    def post_owner(self):
        with self.client.post(
            "/api/customer/owners",
            json=random_owner_payload(),
            name="POST /api/customer/owners",
            catch_response=True
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"Status inesperado: {response.status_code}")
