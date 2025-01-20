import random

def safeparse_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
    
def safeparse_float(value: str, default: float = float(0)) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
    
def add_noise_int(original: int, noise_range: int = 0) -> int:
    return int(original) + random.randint(int(noise_range) * -1, int(noise_range))

# 0 to 100
# 0: always false
# 100: always true
def random_by_probability(p: float | int) -> bool:
    if p < 0 or p > 100:
        print("[ERROR] Probability input is not in 0 to 100")
        raise ValueError
    random_number = random.random() * 100
    return p > random_number
