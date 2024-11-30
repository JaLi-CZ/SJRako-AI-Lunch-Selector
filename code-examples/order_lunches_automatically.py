print("Importing library sjrako.py...")
from sjrako import *

print("Preparing neural network for lunch evaluation...")
from lunch_evaluation import evaluate_lunch

# If you don't want to always choose the lunch with the highest "taste" score
# You can define your own select_best_lunch function
# Otherwise you can import it by typing:
# from lunch_evaluation import select_best_lunch

# The dataset favours sweet lunches by default (they have higher taste scores)
# I prefer meaty lunches, so I will add additional points to them

# Also if no lunch has at least a taste score of 50
# - Return None (I better not order lunch that day)
# - Write to the console that I should rather go to a restaurant that day
def select_best_lunch(lunch_menu: LunchMenu) -> Optional[Lunch]:
    best_lunch = None
    best_lunch_points = -1

    for lunch in lunch_menu:
        properties = evaluate_lunch(lunch.main_dish)
        taste = properties["taste"]
        meatiness = properties["meatiness"]
        # Meaty lunches can have up to a six point advantage
        points = taste + meatiness*0.06

        # Only set the best lunch if it has a taste score >= 50
        if points > best_lunch_points and taste >= 50:
            best_lunch_points = points
            best_lunch = lunch

    # If no lunch has at least taste score >= 50, it remains None
    return best_lunch


# Login with your credentials
user = Canteen.login("YOUR USERNAME", "YOUR PASSWORD")

credit = user.get_credit()

print(f"""Logged in as: {user.full_name}
Credit remaining: {credit} Kč
----------------------------------------------------""")

print("Ordering lunches...")

skipped_days: list[Date] = []  # List of Dates, when all lunches are too bad
order_failed_days: list[Date] = []

# For each LunchMenu on the Canteen website
for lunch_menu in Canteen.get_lunch_menus():
    # If the lunch can't be changed this day (it is too late)
    # Don't even try and continue to the next one
    if not lunch_menu.date.is_lunch_changeable():
        print(f"IGNORING lunch for {lunch_menu.date} - it's too late to change it")
        continue

    # Choose the best lunch by your definition
    best_lunch = select_best_lunch(lunch_menu)

    # If there's no tasty lunch (all taste scores are < 50)
    if best_lunch is None:
        # Just skip this day and remind me later
        # And cancel the lunch if it's not cancelled already
        print(f"SKIPPING lunch for {lunch_menu.date}!")
        skipped_days.append(lunch_menu.date)
        if user.cancel_lunch(lunch_menu.date):
            print(" - [LUNCH CANCELLED]")

    # Otherwise order the best_lunch, warn me if the order failed
    else:
        if user.set_lunch(best_lunch.date, best_lunch.number):
            print(f"ORDERED \"{best_lunch.main_dish}\" for {best_lunch.date}")
        else:
            print(f"FAILED to order lunch for {best_lunch.date}!")
            order_failed_days.append(best_lunch.date)

credit_now = user.get_credit()
credit_change = credit_now - credit

print("--------------------------------------------")
print(f"Lunch ordering is finished! | FAILS: {len(order_failed_days)} | SKIPPED: {len(skipped_days)}")
print(f"Credit remaining (now): {credit_now} Kč | Credit change: {"+" if credit_change > 0 else ""}{credit_change} Kč")
if len(skipped_days) > 0:
    print("\nHere are the days I didn't order you lunch.")
    print("Go to a restaurant on the following days:")
    for date in skipped_days:
        print(f" - {date}")
