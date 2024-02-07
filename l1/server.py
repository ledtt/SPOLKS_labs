import socket
import threading
import time

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ("localhost", 12345)
server_socket.bind(server_address)


def main():
    server_socket.listen()
    print("[СТАРТ] Сервер запущен на {}:{}".format(*server_address))
    start_time = time.time()
    while True:
        conn, addr = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr, start_time))
        thread.start()
        print(
            f"[СОСТОЯНИЕ СОЕДИНЕНИЯ] Активные соединения: {threading.activeCount() - 1}"
        )


def handle_echo(data):
    return data


def handle_time(start_time):
    end_time = time.time()
    cur_time = end_time - start_time
    return str(cur_time)


def handle_help():
    print("[СИСТЕМА] Получен запрос на справку")
    return "Доступные команды:\n" "ECHO <текст>\n" "TIME\n" "CLOSE\n" "HELP"


def handle_client(conn, addr, start_time):
    print(f"[СОСТОЯНИЕ СОЕДИНЕНИЯ] Установлено новое соединение:{addr}")
    connected = True
    try:

        while connected:

            try:
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break

                    commands = data.decode("utf-8").split("/n")
                    print(commands)
                    for command in commands:
                        command = command.strip()
                        if not command:
                            continue  # Пропускаем пустые строки

                        command_parts = command.split(" ", 1)
                        cmd = command_parts[0]
                        result = ""

                        if cmd == "ECHO":
                            result = handle_echo(command_parts[1])
                        elif cmd == "TIME":
                            result = handle_time(start_time)
                        elif cmd == "HELP":
                            result = handle_help()
                        elif cmd == "CLOSE":
                            print(
                                f"[СОСТОЯНИЕ СОЕДИНЕНИЯ] Соединение с клиентом {addr} разорвано"
                            )
                            connected = False
                            break
                        else:
                            result = "[СИСТЕМА] Неизвестная команда"

                        conn.send(result.encode("utf-8"))

            except ConnectionResetError:
                connections_count = threading.activeCount() - 2
                print(
                    "[СОСТОЯНИЕ СОЕДИНЕНИЯ] Соединение с клиентом было разорвано. Подключено клиентов:",
                    connections_count,
                )
                break

            finally:
                conn.close()

    # except KeyboardInterrupt:
    #   pass
    finally:
        server_socket.close()
        print("[КОНЕЦ] Сервер остановлен")


if __name__ == "__main__":
    main()
