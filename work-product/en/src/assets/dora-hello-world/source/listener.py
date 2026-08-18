from dora import Node


node = Node()

for event in node:
    if event["type"] == "INPUT":
        message = event["value"][0].as_py()
        print(f"listener received: {message} from {event['id']}")
    elif event["type"] == "STOP":
        break
