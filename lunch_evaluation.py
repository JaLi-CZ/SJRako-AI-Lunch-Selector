import os

import unicodedata
from difflib import SequenceMatcher
import re

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1'

import tensorflow as tf
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
import numpy as np

from sjrako import Lunch, LunchMenu

def read_dataset(dataset_path: str = f"{ROOT_DIR}/data/lunch-dataset.csv") -> dict[str, dict[str, float]]:
    dataset_rows = open(dataset_path, "r", encoding="utf-8").read().split("\n")
    is_header_row = True
    dataset = {}

    for row in dataset_rows:
        values = row.split(",")

        if is_header_row:
            property_names = list(values)
            is_header_row = False
            continue

        lunch_name = ""
        lunch_properties = {}
        index = 0
        for value in values:
            property_name = property_names[index]
            if property_name == "lunch_name":
                lunch_name = value
            else:
                lunch_properties[property_name] = float(value)
            index += 1

        if lunch_name:
            dataset[lunch_name] = lunch_properties

    return dataset

dataset = read_dataset()
lunch_names = list(dataset.keys())
lunch_ratings = [list(properties.values()) for properties in dataset.values()]
property_names = list(list(dataset.values())[0].keys())


tokenizer = Tokenizer()
tokenizer.fit_on_texts(lunch_names)
sequences = tokenizer.texts_to_sequences(lunch_names)

max_sequence_length = max(len(seq) for seq in sequences)


model_path = f"{ROOT_DIR}/data/lunch-evaluation-model.keras"

# If a model already exists, just load it
if os.path.exists(model_path):
    model = tf.keras.models.load_model(model_path)

# Otherwise create the model and then save it
else:
    lunch_input_vectors = pad_sequences(sequences, maxlen=max_sequence_length, padding='post')
    desired_property_outputs = np.array(lunch_ratings)

    vocab_size = len(tokenizer.word_index) + 1  # Total number of unique words + 1 for padding

    model = tf.keras.Sequential([
        tf.keras.layers.Embedding(input_dim=vocab_size, output_dim=3),
        tf.keras.layers.GlobalAveragePooling1D(),
        tf.keras.layers.Dense(256, activation="relu"),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dense(len(property_names))  # Output layer
    ])

    model.compile(optimizer='adam', loss='mean_absolute_error')

    model.fit(lunch_input_vectors, desired_property_outputs, epochs=800, batch_size=50, validation_split=0.0)
    model.save(model_path)


# Compares the similarity of two words (or strings)
# Returns a similarity score ranging from 0 to 1 inclusive
def similarity(word_1: str, word_2: str) -> float:
    return SequenceMatcher(None, word_1, word_2).ratio()

# Replaces multiple spaces with a single one
def only_single_spaces(s: str):
    return re.sub(" +", " ", s)

# Removes diacritics from a word (or string) - "Böhnův řízek" > "Bohnuv rizek"
def remove_diacritics(s: str):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


# Matches a word to the nearest in the embedding matrix - "vepřvý" > "vepřový"
# Fixes misspellings and different word endings
# If no word matches, returns "" (empty string)
no_diacritics_word_map = {remove_diacritics(word): word for word in tokenizer.word_index.keys()}
def match_word(word: str):
    if word in tokenizer.word_index:
        return word
    if not word:
        return ""
    word_no_diacritics = remove_diacritics(word)
    if word_no_diacritics in no_diacritics_word_map:
        return no_diacritics_word_map[word_no_diacritics]

    similarities = [[similarity(word, w), w] for w in tokenizer.word_index.keys()]
    similarities.sort(key=lambda x: x[0], reverse=True)
    highest_similarity, most_similar_word = similarities[0]
    if highest_similarity >= 0.5:
        return most_similar_word
    else:
        return ""

# Matches all words in the lunch name with the embedding matrix
def match_words(lunch_name: str):
    words = lunch_name.split(" ")
    return only_single_spaces(" ".join([match_word(word) for word in words]))

# Removes all characters not present in the allowed_chars set
allowed_chars = set("abcdefghijklmnopqrstuvwxyzáäéëíóöúůýčďěňřšťž -.")
def keep_only_allowed_chars(lunch_name: str):
    return "".join(filter(lambda c: c in allowed_chars, lunch_name))

# Returns a dictionary of properties
# For example: evaluate_lunch("kuřecí řízek smažený, bramborová kaše")
#   - returns: {'taste': 89, 'meatiness': 86, 'sweetness': 0}
def evaluate_lunch(lunch_name: str) -> dict[str, int]:
    lunch_name = keep_only_allowed_chars(lunch_name.lower())
    matched_lunch_name = match_words(lunch_name)

    sequence = tokenizer.texts_to_sequences([matched_lunch_name])
    padded_sequence = pad_sequences(sequence, maxlen=max_sequence_length)
    prediction = model.predict(padded_sequence, verbose=0)

    properties = {}
    index = 0
    for property in property_names:
        properties[property] = int(round(max(0, min(100, prediction[0][index]))))
        index += 1
    return properties

# Select the best Lunch from the LunchMenu and return it
def select_best_lunch(lunch_menu: LunchMenu) -> Lunch:
    highest_rating = -1
    best_lunch = None
    for lunch in lunch_menu:
        properties = evaluate_lunch(lunch.main_dish)
        rating = properties["taste"]
        if rating > highest_rating:
            highest_rating = rating
            best_lunch = lunch
    return best_lunch


# Prints the embedding matrix used for sequence padding
# Example:
# ...
# 5.	"vařené": [-0.26017868518829346, 0.7126797437667847, 0.5584633946418762]
# 6.	"kaše": [-0.2378835678100586, 0.3444685637950897, 0.23802611231803894]
# 7.	"knedlíky": [-0.43733513355255127, 0.4218534827232361, 0.014351990073919296]
# 8.	"salát": [-0.3613504469394684, -0.03930748999118805, 0.21599996089935303]
# ...
def print_embedding_matrix():
    embedding_layer = model.layers[0]
    embedding_matrix = embedding_layer.get_weights()[0]
    word_index = tokenizer.word_index
    print("Embedding Matrix Shape:", embedding_matrix.shape)
    print("Word Embeddings:")
    for word, index in word_index.items():
        if index < embedding_matrix.shape[0]:  # Ensure the index is within bounds
            embedding_vector = embedding_matrix[index]
            print(f"{index}.\t\"{word}\": {embedding_vector.tolist()}")