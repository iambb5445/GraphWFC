from random import Random

def uniform(values: list[float]|list[int]) -> list[float]:
    total = sum(values)
    return [value/total for value in values]

def get_random_str(rnd: Random):
    import string
    vowels = [v for v in "aeiou"]
    consonants = [s for s in string.ascii_lowercase if s not in vowels]
    vclusters = vowels + ["ae", "ou", "ea", "ai", "io", "ui"]
    cclusters = consonants + ["br", "cr", "dr", "gr", "pr", "fr", "st", "tr"]
    pattern: list[list[str]] = rnd.choice([
        [vowels, consonants, vowels],
        [vowels, consonants, vclusters, consonants],
        [cclusters, vclusters, consonants],
        [cclusters, vclusters, consonants, vowels],
        [cclusters, vclusters, consonants, vowels, consonants],
    ])

    return ''.join([rnd.choice(l) for l in pattern])