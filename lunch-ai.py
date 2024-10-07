import os.path
from typing import Union
import numpy as np
from numpy.typing import NDArray
from collections import Counter
import pickle

from ai import NeuralNetwork, ReLU, MeanAbsoluteError
from sjrako import Canteen, Date, LunchMenu, Lunch


trained_model_path = "lunch.ai"
lunch_dataset_path = "lunch-data.csv"


# Read the dataset
# [{"lunch_name": str, "taste": int[0-100], ?"meatiness": int[0-100], ?"sweetness": int[0-100], ?"healthiness": int[0-100]}, {...}, ...]
dataset: list[dict[str, Union[str, int]]] = []

longest_lunch_len = -1
dataset_params: list[str] = []
first_line = True
for line in map(lambda line: line.strip(), filter(lambda line: line, open(lunch_dataset_path, "r", encoding="utf-8").read().split("\n"))):
    values = line.split(",")
    if first_line:
        dataset_params = values
        first_line = False
        continue

    params = {param: values[i] if i == 0 else int(values[i]) for i, param in enumerate(dataset_params)}
    if len(params["lunch_name"]) > longest_lunch_len:
        longest_lunch_len = len(params["lunch_name"])
    dataset.append(params)


# Create a character map of all used characters and their indexes like {'a': 1, 'b': 2, ...}
lunch_names_joined = "".join([lunch["lunch_name"] for lunch in dataset])
_letters = tuple(sorted(Counter(lunch_names_joined).keys()))
letters_count = len(_letters)
letters: dict[str, int] = {}
for i in range(letters_count):
    letters[_letters[i]] = i


def one_hot_encode(lunch_name: str) -> NDArray:
    inputs = np.zeros(longest_lunch_len * letters_count)
    i = 0
    for c in lunch_name:
        inputs[i * letters_count + letters[c]] = 1
        i += 1
    return inputs


# Create training data from the dataset using One-hot encoding
training_data: list[tuple[NDArray, NDArray]] = []  # [(input_activations, desired_output_activations), (...), ...]
for params in dataset:
    inputs = one_hot_encode(params["lunch_name"])
    desired_outputs = np.array(list(params.values())[1:])
    training_data.append((inputs, desired_outputs))


# Create a model or load it if it already exists at trained_model_path
model = NeuralNetwork.load(trained_model_path)
if model is None:
    model = NeuralNetwork([longest_lunch_len * letters_count, 24, 4], activation_func=ReLU(), loss_func=MeanAbsoluteError())

# model.train(training_data, 1000, 100, 0.01, True, 0.)
# model.save(trained_model_path)

print(f"Done training with Cost: {model.cost}")


def lunch_taste(lunch_name: str) -> int:
    prediction = model.predict(one_hot_encode(lunch_name))
    return max(0, min(100, int(round(prediction[0]))))

def best_lunch(menu: LunchMenu) -> Lunch:
    best_taste = -1
    best_lunch = None
    for lunch in menu:
        taste = lunch_taste(lunch.main_dish)
        if taste > best_taste:
            best_lunch = lunch
            best_taste = taste
    return best_lunch


# pickle_save_path = "obj.pickle"
# if os.path.exists(pickle_save_path):
#     with open(pickle_save_path, "rb") as f:
#         lunch_menus = pickle.load(f)
# else:
#     username, password = open("login-credentials", "r").read().split("\n")
#     user = Canteen.login(username, password)
#     lunch_menus = user.get_all_lunch_menus_between(Date(2023, 1, 1), Date.today())
#     with open(pickle_save_path, "wb") as f:
#         pickle.dump(lunch_menus, f)

# username, password = open("login-credentials", "r").read().split("\n")
# user = Canteen.login(username, password)

username, password = open("login-credentials", "r").read().split("\n")
user = Canteen.login(username, password)

for menu in Canteen.get_lunch_menus():
    user.set_lunch(menu.date, best_lunch(menu).number)
    print(f"Lunch for {menu.date} set to {best_lunch(menu).number}")
