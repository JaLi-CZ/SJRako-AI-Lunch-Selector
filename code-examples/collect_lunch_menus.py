from sjrako import *

user = Canteen.login("YOUR USERNAME", "YOUR PASSWORD")

print(f"Logged in as {user.full_name}!")

# Lunches from 2022 and earlier are no longer publicly available
collect_from = Date(2023, 1, 1)
collect_to = Canteen.get_last_lunch_changeable_date()

print(f"Collecting lunches from {collect_from} to {collect_to}, this may take some time.")

lunch_menus = user.get_all_lunch_menus_between(collect_from, collect_to)

print(f"{len(lunch_menus)} LunchMenus were collected in total.")

json_filepath = "../data/lunch-menus-new.json"
save_lunch_menus(lunch_menus, json_filepath)
print(f"LunchMenus saved to \"{json_filepath}\"!")
