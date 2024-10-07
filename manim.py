from manimlib.imports import *
from manim import *
import math
import random

from manim import *
import random

class Animation(Scene):
    def construct(self):
        # Create the circles
        circles = []
        for i in range(1000):
            circle = Circle()
            x, y = (random.random() - 0.5) * 12, (random.random() - 0.5) * 7
            circle.move_to([x, y, 0])
            circle.scale(0.1)
            circle.set_color(Color(rgb=(random.random(), random.random(), random.random())))
            circle.set_fill(WHITE, 0.5)
            self.add(circle)
            circles.append(circle)

        # Store original positions for reference
        original_positions = {circle: circle.get_center() for circle in circles}

        # Create animations
        animations = []
        for i in range(10):
            # Random new positions
            new_positions = []
            for circle in circles:
                x, y = (random.random() - 0.5) * 12, (random.random() - 0.5) * 7
                new_positions.append([x, y, 0])
                # Create movement animation
                animations.append(
                    circle.animate.move_to(new_positions[-1])
                )

            # Play animations for this frame
            self.play(*animations)
            self.wait(1)

            # Clear animations list for the next frame
            animations.clear()

        # Wait at the end
        self.wait(5)

