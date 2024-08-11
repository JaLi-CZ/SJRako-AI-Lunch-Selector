from sjrako import Canteen, Date

username, password = open("login-credentials", "r").read().split("\n")
user = Canteen.login(username, password)
for i in range(14, 30):
    print(user.set_lunch(Date(2024, 8, i), 0))
