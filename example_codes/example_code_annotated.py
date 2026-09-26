def calculate_average(scores):
    total = sum(scores)
    average = total / len(scores)
    return average


def get_grade(average):
    if average >= 90:
        return "A"
    elif average >= 80:
        return "B"
    elif average >= 70:
        return "C"
    else:
        return "F"


def print_result(student_name, scores):
    average = calculate_average(scores)
    grade = get_grade(average)

    print(f"{student_name}'s average is {average}")
    print(f"Final grade: {grade}")


scores = [85, 90, 78, 92]
print_result("Alex", scores)