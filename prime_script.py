def is_prime(n):
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True

primes = [num for num in range(10, 501) if is_prime(num)]
print("Prime numbers from 10 to 500:")
print(primes)
print(f"Total: {len(primes)}")