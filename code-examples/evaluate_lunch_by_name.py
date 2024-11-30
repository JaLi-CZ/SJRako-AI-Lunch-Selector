from lunch_evaluation import evaluate_lunch

while True:
    lunch_name = input("Enter a lunch name: ")
    properties = evaluate_lunch(lunch_name)

    for property_name, property_value in properties.items():
        print(f" > {property_name}: {property_value}/100")

    print()  # Print blank line
