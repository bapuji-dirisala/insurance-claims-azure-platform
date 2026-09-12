"""Insured party generation (persons / vehicles / properties)."""

from __future__ import annotations

import random
from datetime import UTC, timedelta

from faker import Faker

from claims_azure.generator.config import GeneratorConfig

# Mix of insured types — matches a typical US multi-line P&C book.
_TYPE_WEIGHTS = {"person": 0.60, "vehicle": 0.25, "property": 0.15}


def generate_parties(cfg: GeneratorConfig) -> list[dict]:
    """Build the deterministic parties table."""
    rng = random.Random(cfg.seed)
    Faker.seed(cfg.seed)
    fake = Faker(cfg.locale)

    types = list(_TYPE_WEIGHTS.keys())
    weights = list(_TYPE_WEIGHTS.values())

    # Creation times spread over the 3y before the simulation window so
    # policies effective in the window can reference existing parties.
    creation_floor = cfg.start_date - timedelta(days=365 * 3)
    creation_span_s = int((cfg.start_date - creation_floor).total_seconds())

    parties: list[dict] = []
    for i in range(cfg.num_parties):
        ptype = rng.choices(types, weights=weights, k=1)[0]
        if ptype == "person":
            first = fake.first_name()
            last = fake.last_name()
            name = f"{first} {last}"
            email = f"{first.lower()}.{last.lower()}{i}@example.com"
            phone = fake.phone_number()
            birth_year = rng.randint(1945, 2005)
        elif ptype == "vehicle":
            # VIN-ish identifier.
            name = f"{rng.choice(('Toyota', 'Ford', 'Honda', 'Chevy', 'Tesla'))} {rng.choice(('Civic', 'F-150', 'Corolla', 'Model 3', 'Accord'))} {rng.randint(2015, 2026)}"
            email = None
            phone = None
            birth_year = None
        else:  # property
            name = f"Property at {fake.street_address()}"
            email = None
            phone = None
            birth_year = None

        offset_s = rng.randint(0, creation_span_s)
        created_at = creation_floor + timedelta(seconds=offset_s)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        state = fake.state_abbr() if rng.random() > 0.03 else None

        parties.append(
            {
                "party_id": f"PTY{i:07d}",
                "party_type": ptype,
                "name": name,
                "email": email,
                "phone": phone,
                "country": "US",
                "state_region": state,
                "city": fake.city(),
                "postal_code": fake.postcode(),
                "birth_year": birth_year,
                "created_at": created_at,
            }
        )
    return parties
