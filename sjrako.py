# Python library for interacting with https://jidelna.sjrako.cz/
# Uses selenium to scrape data and interact with the website
# GitHub "https://github.com/JaLi-CZ/SJRako-AI-Lunch-Selector"
from enum import Enum

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


# Creates, configures and returns new selenium driver
def create_driver():
    options = ChromeOptions()
    options.add_argument("--headless=new")

    driver = Chrome(options)
    return driver

# Wait until a page is fully loaded
def wait_for_page_load(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except Exception as e:
        print(f"An error occurred while waiting for the page to load: {e}")

# Reads the price string and returns float
# For example: ' 158,7 Kč ' -> 158.7
allowed_price_chars = "0123456789."
def read_price(s: str):
    price = ""
    was_dot = False
    for c in s.replace(",", "."):
        if c == ".":
            if was_dot:
                continue
            was_dot = True
        if c in allowed_price_chars:
            price += c
    return float(price)


class Date:
    __months = (None, "ledna", "února", "března", "dubna", "května", "června", "července", "srpna", "září", "října", "listopadu", "prosince")

    # Alternative constructor - creates Date using tuple
    @staticmethod
    def from_tuple(date: tuple):
        if len(date) != 3:
            raise ValueError(f"Tuple length must equal 3 when creating a Date object, not {len(date)}!")

        year, month, day = date
        return Date(year, month, day)

    def __init__(self, year: int, month: int, day: int):
        if day < 1 or day > 31:
            raise ValueError(f"Day parameter must be between 1 and 31!")

        if month < 1 or month > 12:
            raise ValueError(f"Month value must be between 1 and 12!")

        self.year = year
        self.month = month
        self.month_name = self.__months[month]
        self.day = day

    @staticmethod
    def __pad_with_zeros(desired_len: int, s) -> str:
        return f"{'0' * desired_len}{s}"[-desired_len:]

    def format(self):
        return f"{self.year}-{Date.__pad_with_zeros(2, self.month)}-{Date.__pad_with_zeros(2, self.day)}"

    def __str__(self):
        return f"{self.day}. {self.month_name} {self.year}"

    def __eq__(self, other):
        if isinstance(other, Date):
            return self.year == other.year and self.month == other.month and self.day == other.day
        return False

    def __hash__(self):
        return hash((self.year, self.month, self.day))


# Class representing the logged User
class User:
    def __init__(self, username: str, password: str):
        driver = create_driver()
        driver.get(Canteen.url)

        driver.find_element(By.ID, "j_username").send_keys(username)
        driver.find_element(By.ID, "j_password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "#login_menu input[type=submit]").submit()

        wait_for_page_load(driver)

        if "objednání" not in driver.title:  # Login failed
            driver.quit()
            raise Exception(f"Login wasn't successful, check the credentials: {username} {'*' * len(password)}")

        # Login successful
        self.username = username
        self.password = password
        self.driver = driver

        credit_info = driver.find_element(By.ID, "kreditInclude").find_elements(By.CSS_SELECTOR, ".topMenuItem")
        self.credit, self.credit_used = read_price(credit_info[0].text), read_price(credit_info[1].text)

    # Log out of your account
    # Returns True if the logout was successful, otherwise False
    def logout(self):
        self.driver.find_element(By.ID, "logout").submit()
        wait_for_page_load(self.driver)
        successful = "přihlášení" in self.driver.title
        self.driver.quit()
        return successful

    # Returns DailyLunchMenu for specified Date
    def get_lunches(self, date: Date):
        # Modify day param in the url
        target_url = self.__url_set_param(self.driver.current_url, "day", date.format())

        # Go to that url
        self.driver.get(target_url)
        wait_for_page_load(self.driver)

        # Scrape lunches, save them as DailyLunchMenu and return it
        lunches = []
        lunch_number = 1
        lunch_items = self.driver.find_elements(By.CSS_SELECTOR, ".jidelnicekItem")
        for lunch_item in lunch_items:
            lunch_info = lunch_item.find_element(By.CSS_SELECTOR, "[id^='menu-']").text
            lunch_order_button = lunch_item.find_element(By.CSS_SELECTOR, ".btn")
            soup, main_dish = Lunch.get_soup_and_main_dish(lunch_info)

            if f"Oběd {lunch_number}" not in lunch_order_button.text:
                raise Exception(f"Lunch numbers must be the same! '{
                    lunch_order_button.text.replace('\n', '')}' does not correspond with lunch number {lunch_number}!")

            anchor = lunch_item.find_element(By.TAG_NAME, "a")
            classes = anchor.get_attribute("class").split(" ")
            if "ordered" in classes:
                status = Lunch.Status.ORDERED
            elif "enabled" in classes:
                status = Lunch.Status.ENABLED
            else:
                status = Lunch.Status.DISABLED

            lunches.append(Lunch(date, lunch_number, soup, main_dish, status=status))
            lunch_number += 1

        return DailyLunchMenu(lunches)

    # Orders a Lunch with the specified number on the specific Date
    # lunch_number == 0 > Cancels order on the specified Date
    # Returns True if all went OK, otherwise False
    def set_lunch(self, date: Date, lunch_number: int) -> bool:
        # Modify day param in the url
        target_url = self.__url_set_param(self.driver.current_url, "day", date.format())

        # Go to that url if not there already
        if self.driver.current_url != target_url:
            self.driver.get(target_url)
            wait_for_page_load(self.driver)

        curr_lunch_number = 1
        lunch_items = self.driver.find_elements(By.CSS_SELECTOR, ".jidelnicekItem")
        for lunch_item in lunch_items:
            lunch_order_button = lunch_item.find_element(By.CSS_SELECTOR, ".btn")

            if f"Oběd {curr_lunch_number}" not in lunch_order_button.text:
                raise Exception(f"Lunch numbers must be the same! '{
                    lunch_order_button.text.replace('\n', '')}' does not correspond with lunch number {curr_lunch_number}!")

            if lunch_number == curr_lunch_number or lunch_number == 0:
                anchor = lunch_item.find_element(By.TAG_NAME, "a")
                classes = anchor.get_attribute("class").split(" ")
                if "ordered" in classes:
                    if lunch_number == 0:
                        anchor.click()
                    return True
                elif "enabled" in classes:
                    if lunch_number != 0:
                        anchor.click()
                        return True
                else:
                    return False
            curr_lunch_number += 1

        return True

    # Modifies an url to have the specified param with the specified value
    @staticmethod
    def __url_set_param(url: str, param: str, value):
        parsed_url = urlparse(url)
        params = parse_qs(parsed_url.query)
        params[param] = [str(value)]
        new_query = urlencode(params, doseq=True)
        target_url = urlunparse(parsed_url._replace(query=new_query))
        return str(target_url)


# Represents a Lunch object
class Lunch:
    class Status(Enum):
        DISABLED = 0
        ENABLED = 1
        ORDERED = 2

    def __init__(self, date: Date, number: int, soup: str, main_dish: str, status: Status = Status.DISABLED):
        def format_dish(dish: str):
            return dish.strip().replace("  ", " ").replace(" ,", ",").replace(";", "")

        self.date = date
        self.number = number
        self.soup = format_dish(soup)
        self.main_dish = format_dish(main_dish)
        self.status = status

    def __str__(self):
        return f"Oběd č. {self.number} dne {self.date} > Polévka: „{self.soup}“ \t Hlavní chod: „{self.main_dish}“"

    # Removes all brackets, and it's content
    @staticmethod
    def __remove_brackets_from_lunch(lunch):
        parentheses, square_brackets = False, False
        s = ""
        for c in lunch:
            if parentheses:
                if c == ')':
                    parentheses = False
            elif square_brackets:
                if c == ']':
                    square_brackets = False
            elif c == '(':
                parentheses = True
            elif c == '[':
                square_brackets = True
            else:
                s += c
        return s.strip()

    # Extracts soup and main_dish name from the lunch and returns it as tuple: (soup, main_dish)
    @staticmethod
    def get_soup_and_main_dish(lunch: str):
        lunch = Lunch.__remove_brackets_from_lunch(lunch)
        first_comma = lunch.index(",")
        soup, main_dish = lunch[:first_comma], lunch[first_comma+1:]
        return soup, main_dish


# Represents a list of Lunches (usually 3) for specific day
class DailyLunchMenu(list):
    def __init__(self, lunches: list):
        # Ensure all items in lunches are of type Lunch
        if not all(isinstance(lunch, Lunch) for lunch in lunches):
            raise TypeError("All items in lunches must be instances of the Lunch class.")

        # Ensure all lunches have the same date
        first_date = lunches[0].date
        if not all(lunch.date == first_date for lunch in lunches):
            raise ValueError("All lunches must have the same date.")

        ordered_lunch, ordered_count, enabled_count = None, 0, 0
        for lunch in lunches:
            if lunch.status == Lunch.Status.ENABLED:
                enabled_count += 1
            elif lunch.status == Lunch.Status.ORDERED:
                ordered_count += 1
                ordered_lunch = lunch

        if ordered_count > 1:
            raise Exception(f"There are {ordered_count} ordered lunches at the same day! There can be only 1!")

        super().__init__(lunches)
        self.date = first_date
        self.change_enabled = enabled_count > 0
        self.ordered_lunch = ordered_lunch

    # Returns lunch by its number, otherwise None
    def get_lunch_by_number(self, lunch_number: int):
        for lunch in self:
            if lunch.number == lunch_number:
                return lunch
        return None

    def __str__(self):
        lunches_str = map(lambda lunch: f"\n -> {lunch.number}. Polévka: „{lunch.soup}“ \t Hlavní chod: „{lunch.main_dish}“", self)
        return f"Lunch Menu for day: {self.date}:{"".join(lunches_str)}"


# Class representing the school canteen
# Only static methods
class Canteen:
    url = "https://jidelna.sjrako.cz/login"
    __driver = None

    # Returns a list of publicly available LunchMenus from "https://jidelna.sjrako.cz/login"
    # Each LunchMenu is a list of Lunches
    @staticmethod
    def get_lunch_menus() -> list:
        # Create a new driver if it doesn't exist
        if not Canteen.__driver:
            Canteen.__driver = create_driver()

        # Scrape all the Lunches and add them to the list
        lunch_menus = []
        Canteen.__driver.get(Canteen.url)

        lunch_days = Canteen.__driver.find_elements(By.CSS_SELECTOR, ".jidelnicekDen")
        for lunch_day in lunch_days:
            lunches = []
            date_el = lunch_day.find_element(By.CSS_SELECTOR, ".jidelnicekTop")
            date = tuple(map(lambda d: int(d), date_el.get_attribute("id").split("-")[1:]))
            date = Date.from_tuple(date)

            lunch_number = 1
            lunch_containers = lunch_day.find_elements(By.CSS_SELECTOR, ".container")
            for lunch_container in lunch_containers:
                elements = lunch_container.find_elements(By.CSS_SELECTOR, ".jidelnicekItem")
                lunch_number_str, lunch = elements[0].text, elements[1].text

                if int(lunch_number_str.split(" ")[-1]) != lunch_number:
                    raise Exception(f"Lunch numbers must be the same! '{lunch_number_str}' does not correspond with {lunch_number}!")

                soup, main_dish = Lunch.get_soup_and_main_dish(lunch)
                lunches.append(Lunch(date, lunch_number, soup, main_dish))
                lunch_number += 1
            lunch_menus.append(DailyLunchMenu(lunches))

        return lunch_menus

    # Logs in with specified username and password and returns User object
    @staticmethod
    def login(username: str, password: str) -> User:
        return User(username, password)
