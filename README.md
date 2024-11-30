# SJRako-AI-Lunch-Selector

It was developed by a student as a high school project. It uses a neural network for approximating how good a lunch is just based off its name. In addition to taste, it also analyzes the meatiness and the sweetness of the lunch.

It also comes with a library which uses selenium for interacting with the school canteen website. It can log in with your credentials, get lunch menus at a specified date, set lunches for specified date by their number, and retrieve your credit balance.

## Requirements
- **Windows 10** (or 11) - it probably won't work with other operating systems
- **Python 3.12.4** installed - <a href="https://www.python.org/downloads/release/python-3124/">Download</a>
  - Don't forget to tick "**Add python.exe to PATH**" when installing it
  - After installation open Command prompt and type "**python --version**" - it should print "**Python 3.12.4**"
- **Git** installed - <a href="https://git-scm.com/downloads/win">Download</a>
- **PyCharm** installed (recommended) - <a href="https://www.jetbrains.com/pycharm/download/#community-edition">Download</a>
- Everything else will be installed automatically - more in Quick Setup

## Quick Setup
Open Command prompt and enter those commands (copy & paste works fine):
```bat
cd /d %USERPROFILE%/Desktop
git clone https://github.com/JaLi-CZ/SJRako-AI-Lunch-Selector.git
cd SJRako-AI-Lunch-Selector
python -m venv venv
"venv/Scripts/activate"
pip install -r requirements.txt
echo Now open (%cd%) as a project in PyCharm (or in an editor of your choice)
```
<p>Note that this can take few minutes, it depends on the speed of your internet connection. Expect the venv folder to take up about <b>2 GB</b> of disk space, mainly because of heavy packages like tensorflow...</p>

# Documentation
## SJRako library
SJRako library (sjrako.py) is written in Selenium. It is intended for interacting with the school canteen website (<a href="sjrako.cz">sjrako.cz</a>), located in Czechia (all lunch names are in czech).<br>
Here is the structure of important classes: (not actual Python code, just simplification)

### Date class
```python
class Date(year, month, day):

    year: int        # Stores the year
    month: int       # Stores the month
    month_name: str  # Stores the name of the month (in czech)
    day: int         # Stores the day of the month

    @staticmethod
    def today() -> Date:     # Returns today's Date
    @staticmethod
    def tomorrow() -> Date:  # Returns tomorrow's Date 

    def is_lunch_changeable() -> bool:  # Returns True if the lunch at the specified date can be changed/cancelled, otherwise False
    def is_after(date: Date) -> bool:   # Also works with > operator
    def is_before(date: Date) -> bool:  # Also works with < operator
```

### Lunch class
```python
class Lunch(date, number, soup, main_dish, can_be_changed=False, is_ordered=False):

    date: Date           # Stores the date of the lunch
    number: int          # Stores the lunch number (1, 2 or 3)
    soup: str            # Stores the name of the soup - e.g. "frankfurtská polévka"
    main_dish: str       # Stores the name of the main dish - e.g. "hovězí gulaš těstoviny vařené"
    can_be_changed: bool # True if the lunch can still be changed/cancelled
    is_ordered: bool     # True if the lunch has been ordered (only available when loaded via the User class)
```

### LunchMenu class
```python
# You can iterate over LunchMenu -> it is basically a collection of Lunches
# for lunch in lunch_menu: ...
class LunchMenu(lunches: list[Lunch]):

    date: Date                      # The date for which the lunch menu is created
    ordered_lunch: Optional[Lunch]  # Stores the lunch that is ordered (if any; only available when loaded via the User class)
    can_be_changed: bool            # True if the lunches in the menu can still be changed/cancelled
    shared_dish: Optional[str]      # Stores the shared ending of main dishes (if any)
    shared_soup: Optional[str]      # Stores the soup (if it's same for all lunches)

    def get_lunch_by_number(lunch_number: int) -> Optional[Lunch]:
        # Returns the Lunch with the specified number, or None if it doesn’t exist
```

### User class
```python
# User class interacts with the canteen's website in a way, that you have to log in first.
class User(username: str, password: str):

    username: str      # Stores the username of the logged-in user
    password: str      # Stores the password of the logged-in user
    first_name: str    # Stores user's first name 
    last_name: str     # Stores user's last name
    full_name: str     # Stores first_name + " " + last_name

    def get_credit() -> float:  # Returns the account balance
    def get_credit_consumption() -> float:
        # Returns how much credit you spent on lunches this month
    def get_credit_status() -> str:
        # Returns a formatted string of available credit and credit consumption

    def get_lunch_menu(date: Date) -> Optional[LunchMenu]:
        # Returns the LunchMenu for the specified date, or None if unavailable
    def get_all_lunch_menus_between(from_date: Date, to_date: Date) -> list[LunchMenu]:
        # Returns a list of LunchMenus between the specified dates (inclusive)

    def set_lunch(date: Date, lunch_number: int) -> bool:
        # Orders a specified lunch by number on the given date; returns True if successful
    def cancel_lunch(date: Date) -> bool:
        # Cancels the lunch for the specified date if possible; returns True if successful
    def cancel_all_lunches() -> bool:
        # Attempts to cancel all lunches within changeable dates; returns True if successful

    def logout() -> bool: # Logs out the user; returns True if successful, otherwise False
        # Optional - you will be logged out automatically when the program terminates
        # Useful when handling multiple accounts
```

### Canteen class
Canteen class is used to access public information on the canteen website, no logging in is required.
```python
class Canteen:

    url: str  # The URL of the canteen's login page

    @staticmethod
    def get_lunch_menus() -> list[LunchMenu]:
        # Returns a list of all available LunchMenus on the canteen's website.
        # If the menus are already updated for today, it returns cached data.

    @staticmethod
    def get_lunch_menu(date: Date) -> Optional[LunchMenu]:
        # Returns the LunchMenu for a specific date if available, otherwise returns None.

    @staticmethod
    def login(username: str, password: str) -> User:
        # Logs in to the canteen system with the provided credentials
        # Returns a User object representing the logged-in user.

    @staticmethod
    def get_lunch_changeable_dates() -> list[Date]:
        # Returns a list of Dates when lunches can still be changed.
```

### Other functions
```python
# Saves a list of LunchMenus as a JSON file at filepath (by default "data/lunch-menus.json")
# Always returns None (void function)
def save_lunch_menus(lunch_menus: list[LunchMenu], filepath: str):

# Loads LunchMenus from a JSON file at filepath (by default "data/lunch-menus.json")
# Returns a list of LunchMenus
def load_lunch_menus(filepath: str) -> list[LunchMenu]:

# JSON structure:
```
```jsonc
{
  "lunchMenus": [
    {
      "date": "2024-01-18",                  # ISO formatted date of the lunch menu
      "sharedSoup": "frankfurtská polévka",  # Present if all soups are the same
      "sharedDish": "mrkvový salát",         # Present if all lunches end with the same dish name
      "lunches": [
        {
          "lunchNumber": 1,                # There are usually 3 lunch numbers (sometimes only 2)
          "soup": "frankfurtská polévka",  # Present if there is no "sharedSoup"
          "mainDish": "vepřová panenka na sekané bazalce bramborové knedlíky"
        },
        {
          "lunchNumber": 2,
          "soup": ...,
          "mainDish": ...
        },
        ...
      ]
    },
    ...
  ]
}
```

### Graphical explanation of how SJRako library operates
<img src="https://i.ibb.co/Wt5jY0j/Canteen.png" width="600">
<img src="https://i.ibb.co/sgNy8gw/User.png" width="600">

## Lunch evaluation library
Lunch evaluation library (lunch_evaluation.py) provides a way to evaluate lunch properties (like taste, meatiness and sweetness) based just off its name.
It does that using a neural network powered by Tensorflow.<br><br>
Here is all you need to know:

```python
# Predicts properties of a lunch item based on its name
# Properties are rated on scale 0 - 100 (integers only)
# Example "kuřecí řízek, bramborová kaše" -> {'taste': 76, 'meatiness': 82, 'sweetness': 0}
def evaluate_lunch(lunch_name: str) -> dict[str, int]:

# Selects the best lunch from a menu (with the highest 'taste' score)
def select_best_lunch(lunch_menu: LunchMenu) -> Lunch:
```

Everything else will be done by using the combination of those two libraries - sjrako.py for communicating with canteen's website and lunch_evaluation.py for evaluating lunch properties and making decisions based on that.

# File structure

I want to make clear what is the purpose of each file and directory in this repository.
- **code-examples/** ... Folder containing all python code examples (more below)
- **data/** ... All files related to storing/collecting data used for machine learning
  - **chromedriver.exe** ... Google Chrome driver used by selenium for web scraping
  - **lunch-dataset.csv** ... CSV table of lunch names and their taste, meatiness and sweetness
    - The 1270 lunches were manually collected and rated by me
    - It is used as a dataset for training the neural network
  - **lunch-evaluation-model.keras** ... Stores the trained neural network (weights, biases, etc.)
    - It will be created automatically after the training of the neural network is done
  - **lunch-menus.json** ... JSON file containing historical data about LunchMenus
    - From 9th August 2021 to 30th August 2024
    - LunchMenus before 2023 are no longer publicly available
  - **lunch_rating_tool.py** ... I created this tool to speed up the process of manually rating all 1270 lunches
    - If you have a different taste than me, you can create your own dataset (not recommended, it took me over 10 hours)
    - Run this script, specify progress file, source JSON file and target CSV file where the rated lunches will be saved
- **lunch_evaluation.py** ... Library for evaluating lunch properties (taste, meatiness, sweetness) using a neural network - documentation above
- **README.md** ... The file you are reading right now
- **requirements.txt** ... Stores all the libraries (and their versions), that required to run this project.
- **sjrako.py** ... Library for communicating with the canteen's website - documentation above


# Code examples

If you have an account, and you want to try it out for yourself, don't forget to replace the "YOUR USERNAME" and "YOUR PASSWORD" strings with your real login credentials.

## How I collected "data/lunch-menus.json"
In order to access the history of older LunchMenus, you must be logged in and use the User class, because the lunches in the past are not publicly available on the canteen's website.

At the time I was collecting it, LunchMenus before 2023 were still available.
```python
from sjrako import *

user = Canteen.login("YOUR USERNAME", "YOUR PASSWORD")

print(f"Logged in as {user.full_name}!")

# Lunches from 2022 and earlier are no longer publicly available
collect_from = Date(2023, 1, 1)
collect_to = Canteen.get_last_lunch_changeable_date()

print(f"Collecting lunches from {collect_from} to {collect_to}, this may take some time.")

lunch_menus = user.get_all_lunch_menus_between(collect_from, collect_to)

print(f"{len(lunch_menus)} LunchMenus were collected in total.")

json_filepath = "../data/lunch-menus.json"
save_lunch_menus(lunch_menus, json_filepath)
print(f"LunchMenus saved to \"{json_filepath}\"!")
```
Program output:
```text
Logged in as **** ****!
Collecting lunches from 1. ledna 2023 to 29. listopadu 2024, this may take some time.
455 LunchMenus were collected in total.
LunchMenus saved to "../data/lunch-menus.json"!
```

## Evaluate lunch properties based on its name

```python
from lunch_evaluation import evaluate_lunch

while True:
    lunch_name = input("Enter a lunch name: ")
    properties = evaluate_lunch(lunch_name)

    for property_name, property_value in properties.items():
        print(f" > {property_name}: {property_value}/100")

    print()  # Print blank line
```
This is the output, when I entered some random lunch names that came to my mind:
```text
Enter a lunch name: smažený kuřecí řízek bramborová kaše
 > taste: 88/100
 > meatiness: 86/100
 > sweetness: 0/100

Enter a lunch name: tofu se špenátem, brokolice
 > taste: 2/100
 > meatiness: 0/100
 > sweetness: 8/100

Enter a lunch name: pečená kachna, rýže jasmínová, mrkvový salát
 > taste: 54/100
 > meatiness: 78/100
 > sweetness: 0/100

Enter a lunch name: sekaná pečeně, brambory vařené
 > taste: 67/100
 > meatiness: 78/100
 > sweetness: 0/100

Enter a lunch name: 
```
And you can evaluate how many lunches you'd like.

## Order lunches automatically
This is a script which automatically orders lunches for you (it is set to meet my personal preferences - mealy lunches are slightly prioritized).
```python
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
```
Program output:
```text
Importing library sjrako.py...
Preparing neural network for lunch evaluation...
Logged in as: **** ****
Credit remaining: 1171.0 Kč
----------------------------------------------------
Ordering lunches...
IGNORING lunch for 21. listopadu 2024 - it's too late to change it
IGNORING lunch for 22. listopadu 2024 - it's too late to change it
ORDERED "dukátové buchtičky s krémem jahodový koktejl" for 25. listopadu 2024
ORDERED "rybí prsty smažené bramborová kaše rajče" for 26. listopadu 2024
ORDERED "telecí maso stroganov rýže dušená" for 27. listopadu 2024
ORDERED "masové koule v rajčatové omáčce těstoviny vařené" for 28. listopadu 2024
ORDERED "spätzle s hruškama a tvarohem perníkový posyp mléko" for 29. listopadu 2024
ORDERED "rybí file na másle s citronem bramborová kaše rajče" for 2. prosince 2024
ORDERED "bavorské vdolečky kakao nesquik" for 3. prosince 2024
ORDERED "hovězí kostky na divoko houskové knedlíky domácí" for 4. prosince 2024
SKIPPING lunch for 5. prosince 2024!
 - [LUNCH CANCELLED]
ORDERED "vepřové kostky na kmíně rýže dušená" for 6. prosince 2024
ORDERED "bratislavské vepřové plecko houskové knedlíky domácí" for 9. prosince 2024
ORDERED "šišky z kynutého těsta horká čokoláda" for 10. prosince 2024
ORDERED "špagety s tuňákem" for 11. prosince 2024
ORDERED "zapečené palačinky s tvarohem mléčný nápoj" for 12. prosince 2024
ORDERED "kuřecí stehna na kysaném zelí bramborové knedlíky" for 13. prosince 2024
--------------------------------------------
Lunch ordering is finished! | FAILS: 0 | SKIPPED: 1
Credit remaining (now): 597.0 Kč | Credit change: -574.0 Kč

Here are the days I didn't order you lunch.
Go to a restaurant on the following days:
 - 5. prosince 2024
```


<hr>
These were some code examples to demonstrate what can be done by using these libraries. Feel free to experiment.