import json
import os.path
import time

from sjrako import Canteen, Date, Lunch, LunchMenu, save_lunch_menus, load_lunch_menus
import pickle
from difflib import SequenceMatcher


# pickle_path = ".ignore/lunch-menus.txt"
# if os.path.exists(pickle_path):
#     with open(pickle_path, "rb") as f:
#         lunch_menus = pickle.load(f)
# else:
#     username, password = open("login-credentials", "r").read().split("\n")
#     user = Canteen.login(username, password)
#
#     from_date, to_date = Date(2023, 1, 1), Canteen.get_last_lunch_changeable_date()
#     lunch_menus = user.get_all_lunch_menus_between(from_date, to_date)
#     with open(pickle_path, "wb") as f:
#         pickle.dump(lunch_menus, f)
#
#
# for lunch_menu_str in open(".ignore/foods-list-with-data.txt", "r", encoding="utf-8").read().split("\n\n"):
#     lunches = []
#     for lunch_str in lunch_menu_str.split("\n"):
#         dot = lunch_str.index(".")
#         lunch_number, lunch_info = int(lunch_str[:dot]), lunch_str[dot + 1:].strip()
#         soup, main_dish, date_str = lunch_info.split(" | ")
#         date = Date.from_tuple(tuple(reversed(tuple(map(lambda x: int(x), date_str.split(". "))))))
#         lunches.append(Lunch(date, lunch_number, soup, main_dish))
#     lunch_menus.append(LunchMenu(lunches))
#
# lunch_menus_map: dict[Date, LunchMenu] = {}
# for lunch_menu in lunch_menus:
#     if lunch_menu.date in lunch_menus_map:
#         assert lunch_menu == lunch_menus_map[lunch_menu.date]
#     lunch_menus_map[lunch_menu.date] = lunch_menu
#
# lunch_menus = list(lunch_menus_map.values())
# lunch_menus.sort(key=lambda menu: menu.date)

save_lunch_menus(Canteen.get_lunch_menus(), filepath="lunch-menus-public.json")
lunch_menus = load_lunch_menus(filepath="lunch-menus-public.json")

for lunch_menu in lunch_menus:
    print(lunch_menu.date)


# TODO: make a GUI (for anyone to use) for creating a custom dataset
# TODO: Neural Network output layer will predict:
#  - float: taste[0-1]
#  - float: meatiness[0-1]
#  - float: sweetness[0-1]
#  - float: healthiness[0-1]
