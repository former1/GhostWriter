# # Defines the BankAccount class
# Defines a BankAccount class that lets you create accounts with an owner and balance, and perform deposits, withdrawals, and balance checks.
class BankAccount:
    # # Describing the three parameters of __init__
    # Initializes a new object with an owner and a balance by storing them as instance attributes.
    def __init__(self, owner, balance):
        # # stores owner name in object attribute
        self.owner = owner
        # # Sets initial balance on the object
        self.balance = balance

    def deposit(self, amount):
        self.balance += amount

    def withdraw(self, amount):
        if amount > self.balance:
            print("Not enough money")
            return

        self.balance -= amount

    def show_balance(self):
        print(f"{self.owner}'s balance is {self.balance}")


account = BankAccount("Alex", 100)

account.deposit(50)
account.withdraw(30)
account.show_balance()