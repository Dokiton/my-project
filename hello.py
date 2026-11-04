from datetime import datetime


def main():
    name = input("Введите имя: ")
    today = datetime.now().strftime("%d.%m.%Y")
    print(f"Салем, {name} бугын {today}")


if __name__ == "__main__":
    main()
