# sample_no_issues.py

integer = 30

def compute_square(numbers):
    return [number ** 2 for number in numbers]

if integer%2 == 0 and integer%3 == 0:
    print(f"{integer} is divisible by both 2 and 3")
else:
    print(f"{integer} is not divisible by both 2 and 3.")