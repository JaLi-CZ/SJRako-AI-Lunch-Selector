# Python library for interacting with https://jidelna.sjrako.cz/
# Uses selenium to scrape data and interact with the website
# GitHub "https://github.com/JaLi-CZ/SJRako-AI-Lunch-Selector"

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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


# Class representing the school canteen
# Only static methods
class Canteen:

    url = "https://jidelna.sjrako.cz/login"
    __driver = None

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

    # Returns a list of publicly available Lunches from "https://jidelna.sjrako.cz/login"
    @staticmethod
    def get_lunches():
        # Create a new driver if it doesn't exist
        if not Canteen.__driver:
            Canteen.__driver = create_driver()

        # Scrape all the Lunches and add them to the list
        lunches = []
        Canteen.__driver.get(Canteen.url)

        lunch_days = Canteen.__driver.find_elements(By.CSS_SELECTOR, ".jidelnicekDen")
        for lunch_day in lunch_days:
            date_el = lunch_day.find_element(By.CSS_SELECTOR, ".jidelnicekTop")
            date = tuple(map(lambda d: int(d), date_el.get_attribute("id").split("-")[1:]))
            date = Date.from_tuple(date)

            lunch_number = 1
            lunch_containers = lunch_day.find_elements(By.CSS_SELECTOR, ".container")
            for lunch_container in lunch_containers:
                elements = lunch_container.find_elements(By.CSS_SELECTOR, ".jidelnicekItem")
                lunch_number_str, lunch = elements[0].text, Canteen.__remove_brackets_from_lunch(elements[1].text)

                if int(lunch_number_str.split(" ")[-1]) != lunch_number:
                    raise Exception(f"Lunch numbers must be the same! '{lunch_number_str}' does not correspond with {lunch_number}!")

                first_comma = lunch.index(",")
                soup, main_dish = lunch[:first_comma], lunch[first_comma+1:]

                lunch = Lunch(date, lunch_number, soup, main_dish)
                lunches.append(lunch)

                lunch_number += 1

        return lunches

    # Logs in with specified username and password and returns User object
    @staticmethod
    def login(username: str, password: str):
        driver = create_driver()
        driver.get(Canteen.url)

        driver.find_element(By.ID, "j_username").send_keys(username)
        driver.find_element(By.ID, "j_password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "#login_menu input[type=submit]").submit()

        wait_for_page_load(driver)

        print(driver.title)


class User:
    def __init__(self):
        pass


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

    def __str__(self):
        return f"{self.day}. {self.month_name} {self.year}"


# Represents a Lunch object
class Lunch:
    def __init__(self, date: Date, number: int, soup: str, main_dish: str):

        def format_dish(dish: str):
            return dish.strip().replace(" ,", ",").replace("  ", " ")

        self.date = date
        self.number = number
        self.soup = format_dish(soup)
        self.main_dish = format_dish(main_dish)

    def __str__(self):
        return f"Oběd č. {self.number} dne {self.date} > Polévka: „{self.soup}“ \t Hlavní chod: „{self.main_dish}“"
