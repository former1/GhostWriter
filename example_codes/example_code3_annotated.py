def calculate_total(price, quantity):
    total = price * quantity
    return total


def apply_discount(total, discount_percent):
    discount = total * discount_percent / 100
    discounted_total = total - discount
    return discounted_total


def add_tax(discounted_total, tax_percent):
    tax = discounted_total * tax_percent / 100
    final_price = discounted_total + tax
    return final_price


def create_receipt(price, quantity, discount_percent, tax_percent):
    total = calculate_total(price, quantity)
    discounted_total = apply_discount(total, discount_percent)
    final_price = add_tax(discounted_total, tax_percent)

    return final_price


result = create_receipt(20, 3, 10, 8)

print(result)