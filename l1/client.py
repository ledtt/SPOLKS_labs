import socket
import threading


def receive_responses(client_socket):
    while True:
        try:
            response = client_socket.recv(1024).decode("utf-8")
            if not response:
                break
            print("> ", response, "\n> ", end="")

        except (ConnectionAbortedError, ConnectionResetError):
            print("Соединение было сброшено сервером.")
            break


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ("localhost", 12345)

    try:
        client_socket.connect(server_address)
        print(f"Успешно подключено к серверу {server_address}")

        # Запускаем отдельный поток для приема ответов от сервера
        response_thread = threading.Thread(
            target=receive_responses, args=(client_socket,)
        )
        response_thread.start()

        print("> ", end="")
        while True:
            user_input = input()
            client_socket.sendall(user_input.encode("utf-8"))

            if user_input == "CLOSE":
                break

    finally:
        client_socket.close()


if __name__ == "__main__":
    main()
