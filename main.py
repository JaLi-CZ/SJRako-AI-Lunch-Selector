from sjrako import Canteen

username, password = open("login-credentials", "r").read().split("\n")
print(f"Logging in as {username}")
