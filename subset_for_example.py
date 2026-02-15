import json
import random

random.seed(42)

with open("./data/Biology2e-WEB.json") as f:
    data = json.load(f)

samples = random.sample(data, 100)

with open("./data/Biology2e-WEB-sample.json", "w") as f:
    json.dump(samples, f, indent=2)

print(f"Wrote {len(samples)} samples from {len(data)} total entries")
