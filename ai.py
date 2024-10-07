"""
Neural Network library written in Python
"""
import os.path
import random
from abc import abstractmethod, ABC
from typing import Optional, Iterable, Union
import numpy as np
from numpy.typing import NDArray


class ActivationFunction(ABC):
    @abstractmethod
    def __call__(self, x: NDArray[float]) -> NDArray[float]:
        pass

    @abstractmethod
    def derivative(self, x: NDArray[float]) -> NDArray[float]:
        pass

    @abstractmethod
    def init_weights(self, input_size: int, output_size: int) -> NDArray:
        pass

class Sigmoid(ActivationFunction):
    def __call__(self, x: NDArray[float]) -> NDArray[float]:
        # Clip values to prevent overflow
        x = np.clip(x, -709, 709)
        return 1.0 / (1.0 + np.exp(-x))

    def derivative(self, x: NDArray[float]) -> NDArray[float]:
        # Sigmoid derivative: f'(x) = f(x) * (1 - f(x))
        sigmoid_x = self.__call__(x)
        return sigmoid_x * (1.0 - sigmoid_x)

    def init_weights(self, input_size: int, output_size: int) -> NDArray:
        # Initialize weights with a small random value based on the input size
        stddev = 1.0 / np.sqrt(input_size)
        return np.random.normal(loc=0.0, scale=stddev, size=(input_size, output_size))

class ReLU(ActivationFunction):
    def __call__(self, x: NDArray) -> NDArray[float]:
        # Apply ReLU function element-wise to the array
        return np.maximum(0.0, x)

    def derivative(self, x: NDArray) -> NDArray[float]:
        # ReLU derivative: f'(x) = 1 if x > 0, else 0
        return np.where(x > 0.0, 1.0, 0.0)

    def init_weights(self, input_size: int, output_size: int) -> NDArray:
        # Initialize weights using He initialization for ReLU
        stddev = np.sqrt(2.0 / input_size)
        return np.abs(np.random.normal(loc=0.0, scale=stddev, size=(input_size, output_size)))

class LeakyReLU(ActivationFunction):
    leak = 0.1

    def __call__(self, x: NDArray) -> NDArray[float]:
        # Apply ReLU function element-wise to the array
        return np.where(x > 0.0, x, x * self.leak)

    def derivative(self, x: NDArray) -> NDArray[float]:
        # ReLU derivative: f'(x) = 1 if x > 0, else 0
        return np.where(x > 0.0, 1.0, self.leak)

    def init_weights(self, input_size: int, output_size: int) -> NDArray:
        # Initialize weights using He initialization for ReLU
        stddev = np.sqrt(2.0 / input_size)
        return np.random.normal(loc=0.0, scale=stddev, size=(input_size, output_size))

ActivationFunction.default = Sigmoid()


class LossFunction(ABC):
    @abstractmethod
    def __call__(self, predictions: NDArray[float], targets: NDArray[float]) -> NDArray[float]:
        pass

    @abstractmethod
    def derivative(self, predictions: NDArray[float], targets: NDArray[float]) -> NDArray[float]:
        pass

    @abstractmethod
    def cost(self, predictions: NDArray[float], targets: NDArray[float]) -> float:
        pass

class MeanSquareError(LossFunction):
    def __call__(self, predictions: NDArray[float], targets: NDArray[float]) -> NDArray[float]:
        return (predictions - targets) ** 2.0

    def derivative(self, predictions: NDArray[float], targets: NDArray[float]) -> NDArray[float]:
        return 2.0 * (predictions - targets)

    def cost(self, predictions: NDArray[float], targets: NDArray[float]) -> float:
        return np.mean(self.__call__(predictions, targets))

class MeanAbsoluteError(LossFunction):
    def __call__(self, predictions: NDArray[float], targets: NDArray[float]) -> NDArray[float]:
        return np.abs(predictions - targets)

    def derivative(self, predictions: NDArray[float], targets: NDArray[float]) -> NDArray[float]:
        return np.where(predictions > targets, 1, -1)

    def cost(self, predictions: NDArray[float], targets: NDArray[float]) -> float:
        return np.mean(self.__call__(predictions, targets))

class BinaryCrossEntropy(LossFunction):
    def __call__(self, predictions: NDArray[float], targets: NDArray[float]) -> NDArray[float]:
        # To avoid log(0) we clip predictions to a minimum value
        predictions = np.clip(predictions, 1e-15, 1 - 1e-15)
        return - (targets * np.log(predictions) + (1 - targets) * np.log(1 - predictions))

    def derivative(self, predictions: NDArray[float], targets: NDArray[float]) -> NDArray[float]:
        predictions = np.clip(predictions, 1e-15, 1 - 1e-15)
        return (predictions - targets) / (predictions * (1 - predictions))

    def cost(self, predictions: NDArray[float], targets: NDArray[float]) -> float:
        return np.mean(self.__call__(predictions, targets))

class CategoricalCrossEntropy(LossFunction):
    def __call__(self, predictions: NDArray[float], targets: NDArray[float]) -> NDArray[float]:
        # To avoid log(0) we clip predictions to a minimum value
        predictions = np.clip(predictions, 1e-15, 1 - 1e-15)
        return -np.sum(targets * np.log(predictions), axis=1)

    def derivative(self, predictions: NDArray[float], targets: NDArray[float]) -> NDArray[float]:
        predictions = np.clip(predictions, 1e-15, 1 - 1e-15)
        return -targets / predictions

    def cost(self, predictions: NDArray[float], targets: NDArray[float]) -> float:
        return np.mean(self.__call__(predictions, targets))

LossFunction.default = MeanSquareError()


class NeuralNetwork:
    defaultSavePath = "model.ai"

    def __init__(self, layer_neuron_counts: list[int], activation_func: Union[ActivationFunction, list[ActivationFunction]] = ActivationFunction.default,
                 loss_func: LossFunction = LossFunction.default):
        if len(layer_neuron_counts) < 2:
            raise ValueError("The number of layers is less than 2, there must be at least 1 input and 1 output layer.")

        if isinstance(activation_func, ActivationFunction):
            activation_func = [activation_func for _ in range(len(layer_neuron_counts)-1)]

        if len(activation_func) != len(layer_neuron_counts)-1:
            raise ValueError("The len(activation_func) must be equal to the number of layers - 1 (input layer doesn't have activation function).")

        layers = []
        previous_layer = None
        i = 0
        for neuron_count in layer_neuron_counts:
            layer = Layer(neuron_count, previous_layer, ActivationFunction.default if previous_layer is None else activation_func[i-1])
            previous_layer = layer
            layers.append(layer)
            i += 1

        self.loss_func = loss_func
        self.layers = layers

        self.cost: float = -1

    # Returns an array of activations in the output Layer
    def predict(self, inputs: Iterable[float]) -> NDArray[float]:
        is_input_layer = True
        for layer in self.layers:
            if is_input_layer:
                inputs = np.array(inputs)
                if len(layer.activations) != len(inputs):
                    raise ValueError("The length of input_activations must be the same as the number of Neurons in the input Layer!")
                layer.activations = np.array(inputs, copy=True)
                is_input_layer = False
                continue
            layer.forward()
        predictions = self.layers[-1].activations
        return predictions

    def current_cost(self, targets: NDArray[float]):
        predictions = self.layers[-1].activations
        if len(predictions) != len(targets):
            raise ValueError("The length of targets must be the same as count of the Neurons in the output Layer!")
        return self.loss_func.cost(predictions, targets)

    # Returns a gradient
    def backprop(self, targets: NDArray[float]) -> list[list[NDArray, NDArray]]:
        output_layer = self.layers[-1]
        predictions = output_layer.activations
        output_layer.a_grad = self.loss_func.derivative(predictions, targets)

        for layer in reversed(self.layers):
            layer.backward()

        gradient = []
        for layer in self:
            if layer.previous_layer:
                gradient.append([layer.w_grad, layer.z_grad])

        return gradient

    # Update weights and biases
    def update_weights(self, gradient: list[list[NDArray, NDArray]], learning_rate: float = 0.001):
        idx = 0
        for layer in self:
            if layer.previous_layer:
                weights_grad, biases_grad = gradient[idx]

                # Clip gradients to a certain range
                np.clip(weights_grad, -1.0, 1.0, out=weights_grad)
                np.clip(biases_grad, -1.0, 1.0, out=biases_grad)

                layer.weights -= weights_grad * learning_rate
                layer.biases -= biases_grad * learning_rate
                idx += 1

    def train(
        self,
        dataset: Iterable[tuple[NDArray[float], NDArray[float]]],
        epochs: int = 10,
        batch_size: int = -1,
        learning_rate: float = 0.001,
        log_info: bool = True,
        validation_split: float = 0.15
    ):
        if not dataset:
            raise ValueError("Training dataset is empty.")

        if not (0 <= validation_split < 1):
            raise ValueError("Validation split must be between 0 and 1.")

        beta1 = 0.9  # Decay rate for the first moment estimate
        beta2 = 0.999  # Decay rate for the second moment estimate
        epsilon = 1e-8  # Small constant to prevent division by zero

        # Initialize Adam parameters
        m_t = []  # First moment vector (mean of gradients)
        v_t = []  # Second moment vector (uncentered variance of gradients)
        t = 0  # Timestep for bias correction

        # Initialize m_t and v_t with zero matrices
        for layer in self.layers:
            if layer.previous_layer:
                m_t.append([np.zeros_like(layer.weights), np.zeros_like(layer.biases)])
                v_t.append([np.zeros_like(layer.weights), np.zeros_like(layer.biases)])

        # Convert dataset to a list for easy shuffling
        dataset = list(dataset)
        random.shuffle(dataset)

        # Split dataset into training and validation sets
        split_index = len(dataset) if validation_split == 0 else int((1 - validation_split) * len(dataset))
        training_data = dataset[:split_index]
        validation_data = dataset[split_index:]

        if batch_size <= 0:
            batch_size = len(training_data)

        min_cost = float('inf')
        epochs_since_improvement = 0

        for epoch in range(epochs):
            random.shuffle(training_data)  # Shuffle training data each epoch for better training
            cost_sum, count = 0, 0

            # Process each mini-batch
            for batch_start in range(0, len(training_data), batch_size):
                batch = training_data[batch_start:batch_start + batch_size]
                gradient_sum = None

                for inputs, targets in batch:
                    self.predict(inputs)
                    cost_sum += self.current_cost(targets)
                    gradient = self.backprop(targets)

                    if gradient_sum:
                        for i in range(len(gradient)):
                            gradient_sum[i][0] += gradient[i][0]  # sum weights
                            gradient_sum[i][1] += gradient[i][1]  # sum biases
                    else:
                        gradient_sum = gradient

                    count += 1

                if gradient_sum is None:
                    continue

                # Calculate the average gradient for the mini-batch
                for i in range(len(gradient_sum)):
                    gradient_sum[i][0] /= len(batch)  # avg weights
                    gradient_sum[i][1] /= len(batch)  # avg biases

                # Update Adam moving averages and apply bias correction
                t += 1  # Increment timestep
                for i in range(len(gradient_sum)):
                    g_w, g_b = gradient_sum[i]  # Gradients for weights and biases
                    m_t[i][0] = beta1 * m_t[i][0] + (1 - beta1) * g_w  # Update first moment
                    m_t[i][1] = beta1 * m_t[i][1] + (1 - beta1) * g_b
                    v_t[i][0] = beta2 * v_t[i][0] + (1 - beta2) * (g_w ** 2)  # Update second moment
                    v_t[i][1] = beta2 * v_t[i][1] + (1 - beta2) * (g_b ** 2)

                    # Compute bias-corrected first and second moments
                    m_hat_w = m_t[i][0] / (1 - beta1 ** t)
                    m_hat_b = m_t[i][1] / (1 - beta1 ** t)
                    v_hat_w = v_t[i][0] / (1 - beta2 ** t)
                    v_hat_b = v_t[i][1] / (1 - beta2 ** t)

                    # Update weights and biases using Adam
                    weight_update = learning_rate * m_hat_w / (np.sqrt(v_hat_w) + epsilon)
                    bias_update = learning_rate * m_hat_b / (np.sqrt(v_hat_b) + epsilon)
                    self.layers[i + 1].weights -= weight_update
                    self.layers[i + 1].biases -= bias_update

            cost_avg = round(cost_sum / count * 1e6) / 1e6
            self.cost = cost_avg

            validation_cost_str = ""
            if validation_split != 0:
                # Evaluate on validation set
                val_cost_sum, val_count = 0, 0
                for inputs, targets in validation_data:
                    self.predict(inputs)
                    val_cost_sum += self.current_cost(targets)
                    val_count += 1

                val_cost_avg = round(val_cost_sum / val_count * 1e6) / 1e6
                validation_cost_str = f"| Validation Cost: {val_cost_avg} "

            if log_info:
                print(f"Epoch {epoch + 1}/{epochs} finished | Training Cost: {cost_avg} {validation_cost_str}| Learning Rate: {learning_rate}")

    def save(self, filepath: str = defaultSavePath):
        layer_neuron_counts = []
        for layer in self:
            layer_neuron_counts.append(str(layer.neuron_count))

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(",".join(layer_neuron_counts))  # Save how many neurons there are in each layer
            f.write("\n")
            f.write(",".join([layer.activation_func.__class__.__name__ for layer in self][1:]))  # Save activation functions
            f.write("\n")
            f.write(self.loss_func.__class__.__name__)  # Save loss function
            for layer in self.layers[1:]:
                f.write("\n\n")
                f.write(",".join(map(str, layer.biases)))  # Save biases
                for ws in layer.weights:  # Save weights
                    f.write("\n")
                    f.write(",".join(map(str, ws)))

    @staticmethod
    def load(filepath: str = defaultSavePath) -> Optional['NeuralNetwork']:
        def get_class_by_name(class_name: str):
            cls = globals().get(class_name)
            if cls and isinstance(cls, type):
                return cls()
            else:
                return None

        if not os.path.exists(filepath):
            return None

        network = None
        with open(filepath, "r", encoding="utf-8") as f:
            layers = f.read().split("\n\n")
            first = True
            layer_idx = 1
            for layer in layers:
                lines = layer.split("\n")
                if first:
                    layer_neuron_counts, act_fns, loss_fn = lines
                    layer_neuron_counts = list(map(int, layer_neuron_counts.split(",")))
                    act_fns = list(map(get_class_by_name, act_fns.split(",")))
                    loss_fn = get_class_by_name(loss_fn)
                    network = NeuralNetwork(layer_neuron_counts, act_fns, loss_fn)
                    first = False
                    continue
                i = 0
                for line in lines:
                    values = np.array(list(map(float, line.split(","))))
                    if i == 0:
                        network.layers[layer_idx].biases = values
                    else:
                        network.layers[layer_idx].weights[i-1] = values
                    i += 1
                layer_idx += 1
        return network

    def __iter__(self):
        return iter(self.layers)


class Layer:
    def __init__(self, neuron_count: int, previous_layer: Optional['Layer'], activation_func: ActivationFunction = ActivationFunction.default):
        self.neuron_count = neuron_count
        self.previous_layer = previous_layer
        self.activation_func = activation_func

        if previous_layer:
            self.weights: NDArray[float, float] = activation_func.init_weights(neuron_count, previous_layer.neuron_count)
            self.biases: NDArray[float] = np.zeros(neuron_count, dtype=float)
        else:
            self.weights = None
            self.biases = None
        self.z: NDArray[float] = np.zeros(neuron_count, dtype=float)
        self.activations: NDArray[float] = np.zeros(neuron_count, dtype=float)
        self.neurons: NDArray[Neuron] = np.array([Neuron(self, i) for i in range(neuron_count)], dtype=object)

        self.a_grad, self.z_grad, self.w_grad = None, None, None

    def forward(self):
        if self.previous_layer:
            self.z = self.weights.dot(self.previous_layer.activations) + self.biases
            self.activations = self.activation_func(self.z)

    def backward(self):
        if self.previous_layer:
            # b_grad (biases) == z_grad (activations before a. func.), they have the same derivative
            self.z_grad = self.activation_func.derivative(self.z)
            self.z_grad *= self.a_grad
            self.w_grad = np.outer(self.z_grad, self.previous_layer.activations)
            self.previous_layer.a_grad = np.dot(self.weights.T, self.z_grad)

    def __iter__(self):
        return iter(self.neurons)


class Neuron:
    def __init__(self, layer: Layer, index: int):
        self.layer = layer
        self.index = index

    def __str__(self):
        return f"[a={self.activation} b={self.bias}]"

    def __repr__(self):
        return self.__str__()

    @property
    def weights(self) -> NDArray:
        return self.layer.weights[self.index] if self.layer.previous_layer else None

    @weights.setter
    def weights(self, value: NDArray[float]):
        if self.layer.previous_layer is None:
            raise Exception("Cannot change weights of the input layer, it does not have any.")
        if len(self.layer.weights[self.index]) != len(value):
            raise ValueError("Cannot set weights, array lengths do not match.")
        self.layer.weights[self.index] = value

    @property
    def bias(self):
        return self.layer.biases[self.index] if self.layer.previous_layer else None

    @bias.setter
    def bias(self, value: float):
        if self.layer.previous_layer is None:
            raise Exception("Cannot change the bias of a Neuron in the input Layer, it does not have any.")
        self.layer.biases[self.index] = value

    @property
    def activation(self):
        return self.layer.activations[self.index]

    @activation.setter
    def activation(self, value: float):
        if self.layer.previous_layer is None:
            raise Exception("Cannot change the activation of a Neuron in the input Layer.")
        self.layer.activations[self.index] = value
