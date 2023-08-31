import sys
import json

a = int(sys.argv[1])
b = 2

c = a / b

output_data = {
    "a": a,
    "b": b,
    "c": c
}

print(json.dumps(output_data))  # Convert the dictionary to JSON and print it
sys.stdout.flush()