from sjrako import Canteen, Date
from difflib import SequenceMatcher

def similarity(s1: str, s2: str) -> float:
    return SequenceMatcher(None, s1, s2).ratio()

username, password = open("login-credentials", "r").read().split("\n")
user = Canteen.login(username, password)

curr_date = Date(2023, 1, 1)
while True:
    menu = user.get_lunch_menu(curr_date)
    print(menu)
    curr_date += 1

# TODO: make a GUI (for anyone to use) for creating a custom dataset
# TODO: Neural Network output layer: taste[0-1], meatiness[0-1], sweetness[0-1], healthiness[0-1]
