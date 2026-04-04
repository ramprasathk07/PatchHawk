class Node:
    def __init__(self, data):
        self.data = data
        self.next = None

class LinkedList:
    """A simple linked list."""
    def __init__(self):
        self.head = None
        
    def append(self, data):
        new_node = Node(data)
        if not self.head:
            self.head = new_node
            return
        last = self.head
        while last.next:
            last = last.next
        last.next = new_node