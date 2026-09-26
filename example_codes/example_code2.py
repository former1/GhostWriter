class BankAccount:
    def __init__(self, owner, balance):
        self.owner = owner
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