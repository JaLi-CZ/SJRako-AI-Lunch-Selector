from manim import *
import numpy as np

# Manim configurations
config.pixel_height = 1080
config.pixel_width = 1920
config.frame_height = 7.0
config.frame_width = 14.0
config.background_color = WHITE


# Custom MLP Visualization Class
class MLPVisualizer(Scene):
    def construct(self):
        # Example network structure: Layers with number of neurons
        layer_sizes = [8, 16, 128, 16, 1]  # Feel free to customize this for your needs

        # Example activations (random values for demonstration, replace with actual values)
        activations = [np.random.rand(size) for size in layer_sizes]

        # Example weights and biases (random values, replace with real values)
        weights = [np.random.randn(layer_sizes[i], layer_sizes[i + 1]) for i in range(len(layer_sizes) - 1)]
        biases = [np.random.randn(size) for size in layer_sizes[1:]]

        self.draw_network(layer_sizes, activations, weights, biases)

    def draw_network(self, layer_sizes, activations, weights, biases):
        # Coordinates and spacing
        layer_x_positions = np.linspace(-6, 6, len(layer_sizes))
        layer_y_spacing = 1.5

        neuron_radius = 0.2

        # Loop through layers
        for layer_idx, layer_size in enumerate(layer_sizes):
            layer_x = layer_x_positions[layer_idx]

            # Limit display if too many neurons in a layer
            num_neurons_display = min(layer_size, 10)  # Show max 10 neurons
            neuron_y_positions = np.linspace(-num_neurons_display / 2, num_neurons_display / 2, num_neurons_display)

            for neuron_idx, neuron_y in enumerate(neuron_y_positions):
                activation_value = activations[layer_idx][neuron_idx]

                # Create neuron (colored based on activation)
                neuron_color = interpolate_color(BLACK, WHITE, activation_value)
                neuron = Circle(radius=neuron_radius, color=BLACK, fill_opacity=1, fill_color=neuron_color)
                neuron.move_to([layer_x, neuron_y, 0])

                # Add neuron label (activation value)
                activation_label = Text(f"{activation_value:.2f}", font_size=24).next_to(neuron, UP)
                self.add(neuron, activation_label)

                # Draw weights if not input layer
                if layer_idx < len(weights):
                    next_layer_x = layer_x_positions[layer_idx + 1]
                    next_layer_size = layer_sizes[layer_idx + 1]
                    next_num_neurons_display = min(next_layer_size, 10)
                    next_neuron_y_positions = np.linspace(-next_num_neurons_display / 2, next_num_neurons_display / 2,
                                                          next_num_neurons_display)

                    for next_neuron_idx, next_neuron_y in enumerate(next_neuron_y_positions):
                        weight_value = weights[layer_idx][neuron_idx, next_neuron_idx]

                        # Create weight (colored based on value)
                        weight_color = interpolate_color(RED, GREEN,
                                                         (weight_value + 1) / 2)  # -1 -> RED, 0 -> average, 1 -> GREEN
                        line = Line([layer_x + neuron_radius, neuron_y, 0],
                                    [next_layer_x - neuron_radius, next_neuron_y, 0], color=weight_color)

                        # Add weight label (value)
                        weight_label = Text(f"{weight_value:.2f}", font_size=16).next_to(line.get_center(), UP,
                                                                                         buff=SMALL_BUFF)
                        self.add(line, weight_label)

        # Add ellipsis (...) if too many neurons
        if layer_size > num_neurons_display:
            ellipsis = Text("...", font_size=36).move_to([layer_x, 0, 0])
            self.add(ellipsis)

    def export_as_image(self):
        # You can call this after constructing the scene to export a PNG image
        self.wait(2)  # Allow time for scene construction
        self.renderer.save_frame(f"network_visualization.png")
