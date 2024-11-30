# .venv\Scripts\python.exe lunch_rating_tool.py

import curses
import csv
import subprocess
import sys
import urllib.parse
import numpy
import pickle
import os
import time
import tempfile
import webbrowser
from difflib import SequenceMatcher
from typing import Optional
from sjrako import load_lunch_menus

if __name__ != "__main__":
    sys.exit()

if not sys.stdout.isatty():
    print("Redirection is not supported. Opening in a new Command Prompt...")
    python_executable = sys.executable
    script_path = os.path.abspath(__file__)
    subprocess.Popen(f'start cmd /k ""{python_executable}" "{script_path}""', shell=True)
    sys.exit()


COLORS_COUNT = 8
BLACK, BLUE, GREEN, CYAN, RED, MAGENTA, YELLOW, WHITE = range(COLORS_COUNT)
class TerminalDisplay:
    def __init__(self, line_count: int):
        self.__stdscr = curses.initscr()
        self.height, self.width = self.__stdscr.getmaxyx()
        self.line_count = line_count
        self.chars = numpy.full((line_count, self.width), " ")
        self.__last_active_lunch = None
        self.__last_lunch_at_rank = numpy.full(11, None, dtype=object)
        self.__lunch_ends = numpy.full(11, None, dtype=object)
        self.__cursor_y = 0
        self.__last_cursor_y = None
        self.__lunch_x_start = 4+4*collected_properties_count

        curses.curs_set(0)  # Hide the cursor
        curses.noecho()  # Disable echoing of key presses
        curses.cbreak()  # React to keys instantly
        curses.start_color()  # Start color support (if needed)
        self.__stdscr.clear()  # Clear the screen initially

        # Initialize all color pairs
        for fg in range(COLORS_COUNT):
            for bg in range(COLORS_COUNT):
                curses.init_pair(self.get_color_pair(fg, bg), fg, bg)

    def write_str(self, y: int, x: int, s: str, fg: int = WHITE, bg: int = BLACK) -> None:
        if y < 0 or y >= self.line_count or x < 0 or x >= self.width:
            return
        end = x + len(s)
        if end > self.width:
            s = s[:self.width-x]
            end = self.width
        i = 0
        for c in s:
            self.chars[y][x+i] = c
            i += 1
        self.__stdscr.addstr(y, x, s, curses.color_pair(self.get_color_pair(fg, bg)))

    def change_color(self, y: int, from_x: int = 0, to_x: int = -1, fg: int = WHITE, bg: int = BLACK) -> None:
        if to_x == -1:
            to_x = self.width
        self.write_str(y, from_x, "".join(self.chars[y][from_x:to_x]), fg, bg)

    def change_color_at(self, y: int, x: int, fg: int = WHITE, bg: int = BLACK):
        self.change_color(y, x, x+1, fg, bg)

    def update_display(self) -> None:
        self.__stdscr.refresh()

    def __get_start_end_cursor_y(self, cursor_y: int) -> tuple:
        if cursor_y == 0:
            return 0, 17
        return self.__lunch_x_start, self.__lunch_ends[cursor_y]

    @staticmethod
    def __cursor_y_to_real_y(cursor_y: int) -> int:
        return 6 if cursor_y == 0 else 7 + cursor_y

    def update_cursor_y(self):
        if self.__last_cursor_y is not None:
            start, end = self.__get_start_end_cursor_y(self.__last_cursor_y)
            self.change_color(self.__cursor_y_to_real_y(self.__last_cursor_y), start, end)
        start, end = self.__get_start_end_cursor_y(self.__cursor_y)
        self.change_color(self.__cursor_y_to_real_y(self.__cursor_y), start, end, BLACK, WHITE)
        self.__last_cursor_y = self.__cursor_y

    def reset_cursor_y(self):
        self.__cursor_y = 0

    def move_up(self):
        self.__cursor_y -= 1
        if self.__cursor_y < 0:
            self.__cursor_y = 0
        self.update_cursor_y()

    def move_down(self):
        self.__cursor_y += 1
        if self.__cursor_y > 10:
            self.__cursor_y = 10
        self.update_cursor_y()

    def set_stands_for_line(self):
        curr_idx = 0
        for prop in property_names:
            if collect_property[prop]:
                text = f"{prop} = {property_names[prop]}   "
                self.write_str(1, curr_idx, text, property_colors[prop])
                curr_idx += len(text)

    def set_column_description_line(self):
        curr_idx = 4
        for prop in property_names:
            if collect_property[prop]:
                text = f"[{prop}] "
                self.write_str(7, curr_idx, text, property_colors[prop])
                curr_idx += len(text)

    def set_progress(self, progress: int) -> None:
        text = pad_with(progress, 5, " ")
        self.write_str(2, 10, text, CYAN)

    def set_out_of(self, out_of: int) -> None:
        text = pad_with(out_of, 5, " ", pad_after=True)
        self.write_str(2, 16, text, YELLOW)
        self.write_str(3, 16, text, YELLOW)

    def set_skipped(self, skipped: int) -> None:
        text = pad_with(skipped, 5, " ", pad_after=True)
        self.write_str(2, 35, text, MAGENTA)

    def set_remains(self, remains: int) -> None:
        text = pad_with(remains, 5, " ", pad_after=True)
        self.write_str(2, 54, text, RED)

    def set_finished(self, finished: int) -> None:
        text = pad_with(finished, 5, " ")
        self.write_str(3, 10, text, GREEN)

    def set_finished_percent(self, finished_ratio: float) -> None:
        col = GREEN
        if finished_ratio <= 1 / 3:
            col = RED
        elif finished_ratio <= 2 / 3:
            col = YELLOW
        text = pad_with(f"{round(finished_ratio * 10000) / 100}%", 6, " ", pad_after=True)
        self.write_str(3, 26, text, col)

    def set_eta(self, days: int, hours: int, minutes: int, seconds: int) -> None:
        add_days, add_hours, add_minutes, add_seconds = False, False, False, False
        if days > 0:
            add_days, add_hours, add_minutes, add_seconds = True, True, True, True
        elif hours > 0:
            add_hours, add_minutes, add_seconds = True, True, True
        elif minutes > 0:
            add_minutes, add_seconds = True, True
        elif seconds > 0:
            add_seconds = True
        time_parts = []
        if add_days:
            time_parts.append(f"{days}d")
        if add_hours:
            time_parts.append(f"{hours}h")
        if add_minutes:
            time_parts.append(f"{minutes}m")
        if add_seconds:
            time_parts.append(f"{seconds}s")
        text = " ".join(time_parts)
        self.write_str(3, 50, " " * 20)
        self.write_str(3, 50, text)

    def set_lunch_at_rank(self, lunch: tuple[str, tuple[int, ...]], rank: int) -> None:
        if rank < 1 or rank > 10:
            raise ValueError(f"Lunch rank must be between 1 and 10, not {rank}.")
        y, x = 7+rank, self.__lunch_x_start
        if self.__last_lunch_at_rank[rank]:
            self.write_str(y, x, " " * len(self.__last_lunch_at_rank[rank]))
        self.write_str(y, x, lunch[0])
        self.__last_lunch_at_rank[rank] = lunch[0]
        self.__lunch_ends[rank] = x + len(self.__last_lunch_at_rank[rank])

        i = 0
        x -= collected_properties_count * 4
        for prop in lunch[1]:
            color = property_colors[collected_properties[i]]
            prop_str = pad_with(prop, 3, " ")
            self.write_str(y, x, prop_str, color)
            x += 4
            i += 1

    def set_top_lunches(self, lunches: list[tuple[str, tuple[int, ...]]]) -> None:
        if len(lunches) > 10:
            raise ValueError(f"The len(lunches) must be <= 10, not {len(lunches)}.")
        rank = 1
        for lunch in lunches:
            self.set_lunch_at_rank(lunch, rank)
            rank += 1

    def set_active_lunch(self, lunch_name: str) -> None:
        text = f"'{lunch_name}'"
        if self.__last_active_lunch:
            self.write_str(19, 2, len(self.__last_active_lunch) * " ")
        self.write_str(19, 2, text)
        self.change_color(19, 3, 3+len(lunch_name), CYAN)
        self.__last_active_lunch = text

    def set_all(self, progress: int, out_of: int, skipped: int, remains: int, finished: int, eta_days: int,
                eta_hours: int, eta_minutes: int, eta_seconds: int, top_lunches: list[tuple[str, tuple[int, ...]]], active_lunch: str) -> None:
        self.set_progress(progress)
        self.set_out_of(out_of)
        self.set_skipped(skipped)
        self.set_remains(remains)
        self.set_finished(finished)
        self.set_finished_percent(finished/out_of)
        self.set_eta(eta_days, eta_hours, eta_minutes, eta_seconds)
        self.set_top_lunches(top_lunches)
        self.set_active_lunch(active_lunch)

    def set_rated_property(self, property_letter: str) -> None:
        property_name = property_names[property_letter]
        prefix, suffix = "Rate the ", " of this lunch from 0 to 100"
        text = f"{prefix}{property_name}{suffix}"
        self.write_str(20, 0, text + 10 * " ")
        self.change_color(20, len(prefix), len(prefix)+len(property_name), property_colors[property_letter])

    def set_user_input(self, user_input: str, rating_taste: bool = False):
        if len(user_input) > 3:
            raise ValueError(f"User input length must be 3 or lower, not {len(user_input)}.")
        text = pad_with(user_input, 3, " ", pad_after=True)
        self.write_str(21, 15, text, RED)
        offset = 15 + len(text)
        self.write_str(21, offset, " " * 20)
        if user_input and rating_taste:
            text = f"  =>  {tastes[int(min((len(tastes)-1, int(user_input)/len(tastes))))]}"
            self.write_str(21, offset, text)

    def get_selected_lunch(self) -> Optional[str]:
        if self.__cursor_y == 0:
            return "SKIP"
        return str(self.__last_lunch_at_rank[self.__cursor_y]) if self.__last_lunch_at_rank[self.__cursor_y] else None

    def wait_for_key(self) -> int:
        """Wait for a key press to continue."""
        return self.__stdscr.getch()

    @staticmethod
    def get_color_pair(fg: int, bg: int) -> int:
        return 1 + fg * COLORS_COUNT + bg

    @staticmethod
    def cleanup() -> None:
        curses.endwin()

    def __del__(self):
        """Ensure the terminal is restored to its normal state when the object is deleted."""
        self.cleanup()


# Compares two strings similarity, returns float [0 - 1]
def similarity(s1: str, s2: str, prioritize_first_two_words: bool = False) -> float:
    sim = SequenceMatcher(None, s1, s2).ratio()
    if prioritize_first_two_words and s1.count(" ") >= 1 and s2.count(" ") >= 1:
        s1_first_two, s2_first_two = " ".join(s1.split(" ")[:2]), " ".join(s2.split(" ")[:2])
        sim2 = SequenceMatcher(None, s1_first_two, s2_first_two).ratio()
        return (sim + sim2 ** 3) / 2
    return sim

# Scans all filenames in the current folder and returns the most 'similar'
# 'similarity' prefers full filename > identical file extension > highest similarity()
def find_similar_file(file_name: str, min_similarity: float = 0.5) -> Optional[str]:
    """Find the most similar file name in the current directory."""
    best_match = None
    highest_similarity = -1

    file_name_base, file_name_ext = os.path.splitext(file_name)

    for current_file in os.listdir('..'):
        current_file_base, current_file_ext = os.path.splitext(current_file)

        # Check for an exact match (full name including extension)
        if current_file == file_name:
            return current_file

        # Check for identical file extension, then compare similarity of bases
        if current_file_ext == file_name_ext:
            sim = similarity(file_name_base, current_file_base)
            if sim > highest_similarity:
                highest_similarity = sim
                best_match = current_file

    return best_match if highest_similarity >= min_similarity else None

def is_valid_filepath(fp: str):
    try:
        with open(fp, 'w'):
            pass
        os.remove(fp)
        return True
    except (OSError, IOError):
        return False

# Asks user for filepath until exists, returns None if empty (use default)
def ask_user_for_file(text: str, non_existing_ok: bool = False) -> Optional[str]:
    first = True
    while True:
        fp = input(text if first else "Incorrect path, please try it again: ")
        if not fp:
            return None
        if os.path.isfile(fp) or (non_existing_ok and is_valid_filepath(fp)):
            return fp
        first = False

# Asks user for a boolean question
def ask(question: str, yes_char: str = "y", no_char: str = "n") -> bool:
    yes_char, no_char = yes_char.lower(), no_char.lower()
    first = True
    try_again = f"Please answer the question by {'YES (y)' if yes_char == "y" else yes_char} or {'NO (n)' if no_char == "n" else no_char}: "
    while True:
        resp = input(f"{question} [{yes_char}/{no_char}]: " if first else try_again).lower().strip()
        if resp.startswith(yes_char):
            return True
        elif resp.startswith(no_char):
            return False
        first = False


def save_progress(filepath: str, data: object) -> None:
    directory, filename = os.path.split(filepath)
    with tempfile.NamedTemporaryFile(dir=directory, delete=False) as temp_file:
        temp_file_name = temp_file.name
        try:
            with open(temp_file_name, "wb") as f:
                pickle.dump(data, f)
            temp_file.close()
            os.replace(temp_file_name, filepath)
        except Exception as e:
            os.remove(temp_file_name)
            raise e

def load_progress(filepath: str) -> object:
    try:
        with open(filepath, "rb") as f:
            return pickle.load(f)
    except:
        return None

def load_dataset_csv(filepath: str) -> dict[str, tuple[int, ...]]:
    dataset = {}
    with open(filepath, mode='r', newline='', encoding="utf-8") as file:
        reader = csv.reader(file)
        header = True
        for row in reader:
            if header:
                prop_count = 0
                first = True
                for prop_name in row:
                    if first:
                        first = False
                        continue
                    letter = property_name_to_letter[prop_name]
                    if collect_property[letter]:
                        prop_count += 1
                if prop_count != collected_properties_count:
                    raise Exception(f"Dataset {filepath} doesn't collect the same properties about lunches.\n"
                                    f"It collects {", ".join(row[1:])} and current progress file collects {", ".join(
                                        map(lambda prop: property_names[prop], filter(lambda prop: collect_property[prop], collect_property)))}.")
                header = False
            else:
                lunch_name: str = row[0]
                properties = tuple(map(lambda x: int(x), row[1:]))  # Convert the remaining columns to integers
                dataset[lunch_name] = properties
    return dataset

def create_dataset_csv_if_needed(filepath: str):
    if not os.path.exists(filepath):
        properties = []
        for prop in property_names:
            if collect_property[prop]:
                properties.append(property_names[prop])
        with open(filepath, mode='w', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            # Write the header: "lunch_name", followed by property names
            header = ["lunch_name"] + properties
            writer.writerow(header)

def append_line_dataset_csv(filepath: str, lunch_name: str, properties: list[int]):
    with open(filepath, mode='a', newline='', encoding="utf-8") as file:
        writer = csv.writer(file)
        # Combine the lunch_name and the properties into a single row
        row = [lunch_name] + properties
        writer.writerow(row)

def calculate_eta(it_took_seconds: float):
    seconds = it_took_seconds * remains
    days = int(seconds / (24 * 3600))
    seconds -= days * 24 * 3600
    hours = int(seconds / 3600)
    seconds -= hours * 3600
    minutes = int(seconds / 60)
    seconds -= minutes * 60
    return days, hours, minutes, round(seconds)

def pad_with(s: object, desired_len: int, pad_char: str = "0", pad_after: bool = False) -> str:
    if len(pad_char) != 1:
        raise ValueError(f"Pad char must be of len == 1! len('{pad_char}') == {len(pad_char)}")
    if pad_after:
        if len(str(s)) > desired_len:
            raise ValueError(f"When pad_after is enabled, len(s) must be <= desired_len, and len('{s}') is not <= {desired_len}.")
        return f"{s}{pad_char * (desired_len-len(str(s)))}"
    return f"{pad_char * desired_len}{s}"[-desired_len:]


# Dictionary containing type of data and whether it should be collected
collect_property: dict[str, bool] = {"T": True}
# What the type of data stand for
property_names: dict[str, str] = {"T": "taste", "M": "meatiness", "S": "sweetness", "H": "healthiness"}
property_name_to_letter: dict[str, str] = {v: k for k, v in property_names.items()}
property_colors: dict[str, int] = {"T": CYAN, "M": RED, "S": MAGENTA, "H": GREEN}
tastes = ("Shit", "Disgusting", "Awful", "Bad", "Meh", "Okay", "Decent", "Tasty", "Delicious", "Excellent!!!")

DEFAULT_PROGRESS_FILE = "lunch-rating.progress"
DEFAULT_SOURCE_JSON_FILE = "lunch-menus.json"
DEFAULT_TARGET_CSV_FILE_LUNCH = "lunch-dataset.csv"
DEFAULT_TARGET_CSV_FILE_SOUP = "soups-dataset.csv"

expected_progress_file = find_similar_file(DEFAULT_PROGRESS_FILE, 0)
expected_source_json_file = find_similar_file(DEFAULT_SOURCE_JSON_FILE, 0.5)

expected_progress_file = expected_progress_file if expected_progress_file else DEFAULT_PROGRESS_FILE
expected_source_json_file = expected_source_json_file if expected_source_json_file else DEFAULT_SOURCE_JSON_FILE
expected_target_csv_file_lunch = DEFAULT_TARGET_CSV_FILE_LUNCH
expected_target_csv_file_soup = DEFAULT_TARGET_CSV_FILE_SOUP

print("\n\n\n**WARNING** DO NOT RESIZE YOUR TERMINAL WINDOW WHEN USING Lunch-rating tool!")
print("Otherwise it will break! If it happens, just Quit by pressing Q.")
print("Don't worry, your progress is being saved continuously.")
print("\n------------- Quick Setup -------------")
print(f"\nPress ENTER to use '{expected_progress_file}'")
progress_file = ask_user_for_file("Specify your progress file: ", non_existing_ok=True)
if progress_file is None:
    progress_file = expected_progress_file

data = load_progress(progress_file)
if data:
    source_json_file, target_csv_file, collect_property, collect_lunch_data = data
else:
    print(f"\nPress ENTER to use '{expected_source_json_file}'")
    source_json_file = ask_user_for_file("Specify source JSON file (containing lunch menu data): ")
    if source_json_file is None:
        source_json_file = expected_source_json_file

    collect_lunch_data = ask(f"\nDo you want to collect SOUP data (S) or LUNCH data (L) this time?", yes_char="L", no_char="S")
    expected_target_csv_file = expected_target_csv_file_lunch if collect_lunch_data else expected_target_csv_file_soup

    while True:
        print(f"\nPress ENTER to use '{expected_target_csv_file}'")
        target_csv_file = ask_user_for_file("Specify a non-existing target CSV file for creating a dataset: ", non_existing_ok=True)
        if target_csv_file is None:
            target_csv_file = expected_target_csv_file
        if os.path.exists(target_csv_file):
            print(f"File {target_csv_file} already exists, you should NEVER USE AN ALREADY EXISTING CSV FILE!")
            print("Unless you've accidentally deleted your .progress file and you're now trying to relink it.")
            sure = ask(f"ARE YOU 100% SURE you want to proceed and use '{target_csv_file}'?!?")
            if sure:
                break
        else:
            break

    print("\n\nDo you want to collect some additional data about lunches besides taste [T]?\n")
    for data in property_names:
        if data == "T":
            continue
        collect_property[data] = ask(f"Do you want to collect lunch {property_names[data]} [{data}]?")

    data = source_json_file, target_csv_file, collect_property, collect_lunch_data
    save_progress(progress_file, data)

collected_properties = []
for prop in property_names:
    if collect_property[prop]:
        collected_properties.append(prop)
collected_properties_count = len(collected_properties)

lunch_menus = load_lunch_menus(source_json_file)
lunches_set = set()
for lunch_menu in lunch_menus:
    for lunch in lunch_menu:
        lunches_set.add(lunch.main_dish if collect_lunch_data else lunch.soup)

create_dataset_csv_if_needed(target_csv_file)
dataset_lunches = load_dataset_csv(target_csv_file)

for lunch_name in dataset_lunches.keys():
    lunches_set.discard(lunch_name)

lunches = list(lunches_set)
progress, skipped, remains, finished, out_of = len(dataset_lunches), 0, len(lunches), len(dataset_lunches), len(dataset_lunches) + len(lunches)

lines = [
    "- - - - Lunch-rating tool - - - Create your own dataset - - - -",
    "",
    "Progress: XXXXX/XXXXX  |  Skipped: XXXXX  |  Remains: XXXXX",
    "Finished: XXXXX/XXXXX  |  XXXXX%          |  ETA: ",
    "Keys: Q = quit | O = open image | W = up | S = down | ENTER = select highlighted / save my rating",
    "Best matches [TOP 10] > Press ENTER to skip or use the same rating as highlighted",
    ">>> SKIP this one",
    "",
    "1. ",
    "2. ",
    "3. ",
    "4. ",
    "5. ",
    "6. ",
    "7. ",
    "8. ",
    "9. ",
    "10.",
    "",
    "> ",
    "",
    "$ Your rating: "
]

display = TerminalDisplay(len(lines))
y = 0
for line in lines:
    display.write_str(y, 0, line)
    y += 1

display.set_stands_for_line()
display.set_column_description_line()

eta_days, eta_hours, eta_minutes, eta_seconds = 0, 0, 0, 0
while len(lunches) > 0:
    start_seconds = time.time()
    curr_lunch_name = lunches.pop()
    top_matches = sorted(dataset_lunches.items(), key=lambda pair: -similarity(curr_lunch_name, pair[0], True))[:10]

    display.set_all(progress, out_of, skipped, remains, finished, eta_days, eta_hours, eta_minutes, eta_seconds, top_matches, curr_lunch_name)
    display.reset_cursor_y()
    display.update_cursor_y()

    ratings: list[int] = []
    skip = False
    copy_props = None
    prop_idx = -1
    for prop in property_names:
        if collect_property[prop]:
            prop_idx += 1
            user_input, last_user_input = str(copy_props[prop_idx]) if copy_props else "", ""
            display.set_user_input(user_input)
            display.set_rated_property(prop)

            while True:
                key: int = display.wait_for_key()
                c = chr(key).lower()
                if "0" <= c <= "9":
                    user_input += c
                elif c == "\b":
                    if user_input:
                        user_input = user_input[:-1]
                elif c == "\n" or c == "\r":  # Enter
                    if user_input:
                        break
                    selected_lunch = display.get_selected_lunch()
                    if selected_lunch == "SKIP":
                        skip = True
                        break
                    elif selected_lunch:
                        copy_props = dataset_lunches[selected_lunch]
                        curr_prop_rating: int = copy_props[prop_idx]
                        user_input = str(curr_prop_rating)
                elif c == "w":
                    display.move_up()
                elif c == "s":
                    display.move_down()
                elif c == "o":
                    search_text = curr_lunch_name
                    search_url = f"https://www.google.com/search?q={urllib.parse.quote(search_text)}&udm=2"
                    webbrowser.open(search_url)
                elif c == "q":
                    display.cleanup()
                    exit()

                if user_input and (int(user_input) > 100 or len(user_input) > 3):  # Block
                    user_input = last_user_input

                if user_input != last_user_input:
                    display.set_user_input(user_input, prop == "T")
                last_user_input = user_input

            if skip:
                break
            else:
                ratings.append(int(user_input))

    if skip:
        skipped += 1
    else:
        it_took_seconds = time.time() - start_seconds
        eta_days, eta_hours, eta_minutes, eta_seconds = calculate_eta(it_took_seconds)

        dataset_lunches[curr_lunch_name] = tuple(ratings)
        append_line_dataset_csv(target_csv_file, curr_lunch_name, ratings)

        finished += 1
        remains -= 1

    progress += 1

display.cleanup()

print("\n\n\n\n--------------- You're at the end! ---------------")
print("Congrats on finishing the data collection!")
print("Thank you for using Lunch-rating tool!\n")
if skipped > 0:
    print(f"You skipped the rating of {skipped} lunch{"" if skipped == 1 else "es"}.")
    print(f"You can run this program again and complete it if you want to!\n")
print(f"You can now find all the collected data at '{target_csv_file}'.")
print("If you wish, you can manually modify any data there.\n")

if collect_lunch_data:
    print("I've also noticed, that you have been collecting main dish [lunch] data.")
    print("This is obviously more important, because soups are the same for every lunch number.")
    print("But if you'd like to collect soup data too (if you haven't already), just:")
    print(" -> Run this program again.")
    print(" -> Choose another .progress filename - like 'soup-rating.progress' for example.")
    print(" -> Do everything the same, except choose to collect soup instead of lunch data when being asked for it.")
    print(" -> It will create separate csv file for saving soup data.")
else:
    print("I've also noticed, that you have been collecting soup data.")
    print("If you'd like to collect main dish [lunch] data too (if you haven't already), just:")
    print(" -> Run this program again.")
    print(" -> Choose another .progress filename - like 'lunch-rating.progress' for example.")
    print(" -> Do everything the same, except choose to collect lunch instead of soup data when being asked for it.")
    print(" -> It will create separate csv file for saving main dish [lunch] data.")
print(" -> Whenever you quit and rerun it, just don't forget to specify the correct .progress file.\n")

print("And finally, if you're 100% SURE THAT YOU COLLECTED ALL THE DATA you needed,")
print(f" you can now DELETE the '{progress_file}' file.")
print(f"It stores all the info about:")
print(f" -> What properties you want to collect about lunches [Taste] [M] [S] [H].")
print(f" -> Whether you want to collect main dish [lunch] or soup data.")
print(f" -> Filepaths: source JSON lunch menus path, target csv file, .progress file\n")
