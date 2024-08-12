# Python library for interacting with https://jidelna.sjrako.cz/
# Uses selenium to scrape data and interact with the website
# GitHub "https://github.com/JaLi-CZ/SJRako-AI-Lunch-Selector"

import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Tuple

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


# Creates, configures and returns new selenium driver
def create_driver() -> WebDriver:
    options = ChromeOptions()
    options.add_argument("--headless=new")

    driver = Chrome(options)
    return driver

# Wait until the page body is loaded
def wait_for_page_load(driver: WebDriver, wait_for_el: Tuple[str, str] = (By.TAG_NAME, "body"),
                       wait_for_multiple: bool = False, timeout: float = 10) -> None:
    if wait_for_multiple:
        ec = EC.presence_of_all_elements_located(wait_for_el)
    else:
        ec = EC.presence_of_element_located(wait_for_el)
    WebDriverWait(driver, timeout).until(ec)

# Reads the price string and returns float
# For example: ' 158,7 Kč ' -> 158.7
allowed_price_chars = "0123456789."
def read_price(s: str) -> float:
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
    __months: tuple[str] = ("?", "ledna", "února", "března", "dubna", "května", "června", "července", "srpna", "září", "října", "listopadu", "prosince")

    # Alternative constructor - creates Date using tuple
    @staticmethod
    def from_tuple(date: tuple) -> 'Date':
        if len(date) != 3:
            raise ValueError(f"Tuple length must equal 3 when creating a Date object, not {len(date)}!")

        year, month, day = date
        return Date(year, month, day)

    # Creates Date object using today's date
    @staticmethod
    def today() -> 'Date':
        today = datetime.today()
        return Date(today.year, today.month, today.day)

    # Creates Date object using tomorrow's date
    @staticmethod
    def tomorrow() -> 'Date':
        tomorrow = datetime.today() + timedelta(days=1)
        return Date(tomorrow.year, tomorrow.month, tomorrow.day)

    def __init__(self, year: int, month: int, day: int):
        if day < 1 or day > 31:
            raise ValueError(f"Day parameter must be between 1 and 31!")

        if month < 1 or month > 12:
            raise ValueError(f"Month value must be between 1 and 12!")

        self.year: int = year
        self.month: int = month
        self.month_name: str = self.__months[month]
        self.day: int = day

    # Check if Lunch can be changed on this date
    def is_lunch_changeable(self) -> bool:
        if self == self.today() or (self == self.tomorrow() and datetime.now().hour >= 16):  # 15:10 can still change next day
            return False
        for menu in Canteen.get_lunch_menus():
            if menu.date == self:
                return True
        return False

    @staticmethod
    def __pad_with_zeros(desired_len: int, s: object) -> str:
        return f"{'0' * desired_len}{s}"[-desired_len:]

    def format(self) -> str:
        return f"{self.year}-{Date.__pad_with_zeros(2, self.month)}-{Date.__pad_with_zeros(2, self.day)}"

    def __add__(self, other):
        if type(other) is int:
            days = other
            new_time = datetime(self.year, self.month, self.day) + timedelta(days=days)
            return Date(new_time.year, new_time.month, new_time.day)
        else:
            raise TypeError(f"You can only add int representing the number of days.")

    def __str__(self):
        return f"{self.day}. {self.month_name} {self.year}"

    def __eq__(self, other):
        if isinstance(other, Date):
            return self.year == other.year and self.month == other.month and self.day == other.day
        return False

    def __hash__(self):
        return hash((self.year, self.month, self.day))


# Represents a Lunch object
class Lunch:
    class Status(Enum):
        DISABLED = 0
        ENABLED = 1
        ORDERED = 2

    def __init__(self, date: Date, number: int, soup: str, main_dish: str, status: Status = Status.DISABLED):
        def format_dish(dish: str):
            dish = dish.lower()

            del_from = dish.find("oběd pro studenta")
            if del_from != -1:
                dish = dish[:del_from]

            dish = dish.strip().replace("  ", " ").replace("  ", " ").replace(" ,", ",").replace(";", "")
            if dish.endswith(","):
                dish = dish[:-1].strip()
            dish = dish.replace(", ", ",").replace(",", ", ")
            return dish.replace('"', "")

        self.date: Date = date
        self.number: int = number
        self.soup: str = format_dish(soup)
        self.main_dish: str = format_dish(main_dish)
        self.status: Lunch.Status = status

    def __str__(self):
        return f"Oběd č. {self.number} dne {self.date} > Polévka: „{self.soup}“ \t Hlavní chod: „{self.main_dish}“"

    # Removes all brackets, and it's content
    @staticmethod
    def __remove_brackets_from_lunch(lunch: str) -> str:
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
    def get_soup_and_main_dish(lunch: str) -> Optional[tuple[str, str]]:
        lunch = Lunch.__remove_brackets_from_lunch(lunch)
        sep = lunch.find(";")
        if sep == -1:
            return None
        soup, main_dish = lunch[:sep], lunch[sep+1:]
        if soup.strip() == "" or main_dish.strip() == "":
            return None
        return soup, main_dish


# Represents a list of Lunches (usually 3) for specific day
class LunchMenu(list):
    def __init__(self, lunches: list[Lunch]):
        if lunches is None or len(lunches) == 0:
            raise ValueError("Lunches must not be None and must have len >= 1.")

        # Ensure all items in lunches are of type Lunch
        if not all(isinstance(lunch, Lunch) for lunch in lunches):
            raise TypeError("All items in lunches must be instances of the Lunch class.")

        # Ensure all lunches have the same date
        first_date = lunches[0].date
        if not all(lunch.date == first_date for lunch in lunches):
            raise ValueError("All lunches must have the same date.")

        # Count lunches by status
        ordered_lunch, ordered_count, enabled_count = None, 0, 0
        for lunch in lunches:
            if lunch.status == Lunch.Status.ENABLED:
                enabled_count += 1
            elif lunch.status == Lunch.Status.ORDERED:
                ordered_count += 1
                ordered_lunch = lunch

        # There can be only 1 lunch ordered each day
        if ordered_count > 1:
            raise Exception(f"There are {ordered_count} ordered lunches at the same day! There can be only 1!")

        super().__init__(lunches)
        self.date: Date = first_date
        self.change_enabled: bool = enabled_count > 0
        self.ordered_lunch: Lunch = ordered_lunch

        # Find and define shared variables
        # shared_dish: defined if all main_dishes ends with the same part
        # shared_soup: defined if all soups are the same (which they should)
        self.shared_dish: Optional[str] = None
        self.shared_soup: Optional[str] = None

        # Check if all soups are the same
        first_soup = None
        shared_soup = True
        for lunch in lunches:
            if first_soup is None:
                first_soup = lunch.soup
            if lunch.soup != first_soup:
                shared_soup = False
                break
        if shared_soup:
            # All soups are the same
            self.shared_soup = first_soup

        # Find shared endings of main_dish(es), delete them, and save them as shared_dish
        shared_words = []
        curr_index = -1
        while True:
            try:
                word = None
                word_is_shared = True
                for lunch in lunches:
                    w = lunch.main_dish.split(" ")[curr_index]
                    if word is None:
                        word = w
                    if w != word:
                        word_is_shared = False
                        break
                if word_is_shared:
                    shared_words.append(word)
                else:
                    break
                curr_index -= 1
            except IndexError:
                break
        shared_ending = " ".join(reversed(shared_words))
        if shared_ending:
            self.shared_dish = shared_ending
            for lunch in lunches:
                main_dish = lunch.main_dish[:-len(shared_ending)].strip()
                if main_dish.endswith(","):
                    main_dish = main_dish[:-1].strip()
                lunch.main_dish = main_dish

    # Returns lunch by its number, otherwise None
    def get_lunch_by_number(self, lunch_number: int) -> Optional[Lunch]:
        for lunch in self:
            if lunch.number == lunch_number:
                return lunch
        return None

    def __str__(self):
        lunches_str = map(lambda lunch: f"\n -> {lunch.number}. {'' if self.shared_soup else f'Polévka: „{lunch.soup}“ \t '}"
                                        f"Hlavní chod: „{lunch.main_dish}“", self)
        shared_dish_str, shared_soup_str = "", ""
        if self.shared_dish:
            shared_dish_str = f"\n --> Pokrm: „{self.shared_dish}“"
        if self.shared_soup:
            shared_soup_str = f"\n --> Polévka: „{self.shared_soup}“"
        return f"Lunch Menu for day: {self.date}:{shared_soup_str + "".join(lunches_str) + shared_dish_str}"


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
        self.username: str = username
        self.password: str = password
        self.driver: WebDriver = driver

        self.__credit_up_to_date = False
        self.__update_credit()

    # Updates the credit status
    def __update_credit(self) -> None:
        credit_content_selector = By.ID, "kreditInclude"  # Do not change By.ID without first modifying execute_script!
        credit_info_selector = By.CSS_SELECTOR, ".topMenuItem"

        self.driver.execute_script(f"$('#{credit_content_selector[1]}').empty();")
        self.driver.refresh()
        wait_for_page_load(self.driver, wait_for_el=credit_info_selector, wait_for_multiple=True)

        credit_info = self.driver.find_element(*credit_content_selector).find_elements(*credit_info_selector)
        self.__credit, self.__credit_used = read_price(credit_info[0].text), read_price(credit_info[1].text)
        self.__credit_up_to_date = True

    def get_credit(self) -> float:
        if not self.__credit_up_to_date:
            self.__update_credit()
        return self.__credit

    def get_credit_used(self) -> float:
        if not self.__credit_up_to_date:
            self.__update_credit()
        return self.__credit_used

    def get_credit_status(self) -> str:
        credit = str(self.get_credit()).replace(".", ",")
        credit_used = str(self.get_credit_used()).replace(".", ",")
        return f"Zůstatek kreditu na účtu: {credit} Kč  | Aktuální spotřeba kreditu: {credit_used} Kč"

    # Log out of your account
    # Returns True if the logout was successful, otherwise False
    def logout(self) -> bool:
        self.driver.find_element(By.ID, "logout").submit()
        wait_for_page_load(self.driver)
        successful = "přihlášení" in self.driver.title
        self.driver.quit()
        return successful

    # Returns LunchMenu for specified Date
    def get_lunch_menu(self, date: Date) -> Optional[LunchMenu]:
        # Modify day param in the url
        target_url = self.__url_set_param(self.driver.current_url, "day", date.format())

        # Go to that url
        self.driver.get(target_url)
        wait_for_page_load(self.driver)

        # Scrape lunches, save them as LunchMenu and return it
        lunches = []
        lunch_number = 1
        lunch_items = self.driver.find_elements(By.CSS_SELECTOR, ".jidelnicekItem")
        for lunch_item in lunch_items:
            lunch_info = lunch_item.find_element(By.CSS_SELECTOR, "[id^='menu-']").text
            lunch_order_button = lunch_item.find_element(By.CSS_SELECTOR, ".btn")
            soup_and_dish = Lunch.get_soup_and_main_dish(lunch_info)
            if soup_and_dish is None:
                continue
            soup, main_dish = soup_and_dish

            if f"Oběd {lunch_number}" not in lunch_order_button.text:
                return None
                # raise Exception(f"Lunch numbers must be the same! '{
                #     lunch_order_button.text.replace('\n', '')}' does not correspond with lunch number {lunch_number}!")

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

        return None if len(lunches) == 0 else LunchMenu(lunches)

    __max_recursion_depth = 3

    # Orders a Lunch with the specified number on the specific Date
    # lunch_number == 0 > Cancels order on the specified Date
    # Returns True if all went OK, otherwise False, works perfectly only in safe_mode
    # safe_mode = Check if it was successful, otherwise try once more, takes longer
    def set_lunch(self, date: Date, lunch_number: int, safe_mode: bool = True, recursion_depth: int = 1) -> bool:
        # Check if it's possible to change Lunch on this date
        if not date.is_lunch_changeable():
            return False

        # Modify day param in the url
        target_url = self.__url_set_param(self.driver.current_url, "day", date.format())

        # Go to that url
        self.driver.get(target_url)
        wait_for_page_load(self.driver)

        # Order specified lunch
        probably_success, interacted = None, False
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
                        self.__credit_up_to_date, interacted = False, True
                    probably_success = True
                    break
                elif "enabled" in classes:
                    if lunch_number != 0:
                        anchor.click()
                        self.__credit_up_to_date, interacted = False, True
                        probably_success = True
                        break
                elif "disabled" in classes:
                    probably_success = False
                    break
            curr_lunch_number += 1

        if probably_success is None:
            probably_success = lunch_number == 0

        if safe_mode and (interacted or not probably_success):
            menu = self.get_lunch_menu(date)
            if menu is None:
                return False
            if menu.ordered_lunch is None:
                if lunch_number == 0:
                    return True
            elif menu.ordered_lunch.number == lunch_number:
                return True

            # Unable to set lunch, let's try it again few more times
            recursion_depth += 1
            if recursion_depth <= self.__max_recursion_depth:
                return self.set_lunch(date, lunch_number, safe_mode, recursion_depth)
            else:
                return False
        else:
            return probably_success

    # Cancels the lunch at a specified day
    def cancel_lunch(self, date: Date, safe_mode: bool = True) -> bool:
        return self.set_lunch(date, 0, safe_mode=safe_mode)

    # Cancels all lunches if possible
    # Returns True if all lunches were cancelled successfully, otherwise False
    def cancel_all_lunches(self, safe_mode: bool = True) -> bool:
        successful = True
        for date in Canteen.get_lunch_changeable_dates():
            if not self.cancel_lunch(date, safe_mode=safe_mode):
                successful = False
        return successful

    # Modifies an url to have the specified param with the specified value
    @staticmethod
    def __url_set_param(url: str, param: str, value: object) -> str:
        parsed_url = urlparse(url)
        params = parse_qs(parsed_url.query)
        params[param] = [str(value)]
        new_query = urlencode(params, doseq=True)
        target_url = urlunparse(parsed_url._replace(query=new_query))
        return str(target_url)


# Class representing the school canteen
# Only static methods
class Canteen:
    url: str = "https://jidelna.sjrako.cz/login"
    __driver: WebDriver = None
    __last_lunch_menus_update, __lunch_menus = None, None

    # Returns a list of publicly available LunchMenus from "https://jidelna.sjrako.cz/login"
    # Each LunchMenu is a list of Lunches
    @staticmethod
    def get_lunch_menus() -> list[LunchMenu]:
        # If there's no need for an update, just return cached lunch menus
        today = Date.today()
        if Canteen.__last_lunch_menus_update is not None and Canteen.__last_lunch_menus_update == today:
            return Canteen.__lunch_menus.copy()

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
            date = Date.from_tuple(tuple(map(lambda d: int(d), date_el.get_attribute("id").split("-")[1:])))

            lunch_number = 1
            lunch_containers = lunch_day.find_elements(By.CSS_SELECTOR, ".container")
            for lunch_container in lunch_containers:
                elements = lunch_container.find_elements(By.CSS_SELECTOR, ".jidelnicekItem")
                lunch_number_str, lunch = elements[0].text, elements[1].text

                if int(lunch_number_str.split(" ")[-1]) != lunch_number:
                    raise Exception(f"Lunch numbers must be the same! '{lunch_number_str}' does not correspond with {lunch_number}!")

                soup_and_dish = Lunch.get_soup_and_main_dish(lunch)
                if soup_and_dish is None:
                    continue
                soup, main_dish = soup_and_dish
                lunches.append(Lunch(date, lunch_number, soup, main_dish))
                lunch_number += 1

            if len(lunches) != 0:
                lunch_menus.append(LunchMenu(lunches))

        Canteen.__last_lunch_menus_update = today
        Canteen.__lunch_menus = lunch_menus
        return lunch_menus.copy()

    # Returns a LunchMenu for a specific date
    @staticmethod
    def get_lunch_menu(date: Date) -> Optional[LunchMenu]:
        lunch_menus = Canteen.get_lunch_menus()
        for menu in lunch_menus:
            if menu.date == date:
                return menu
        return None

    # Logs in with specified username and password and returns User object
    @staticmethod
    def login(username: str, password: str) -> User:
        return User(username, password)

    # Returns a list of all Dates when the lunch can be changed
    @staticmethod
    def get_lunch_changeable_dates() -> list[Date]:
        dates = []
        for menu in Canteen.get_lunch_menus():
            if menu.date.is_lunch_changeable():
                dates.append(menu.date)
        return dates
