import socket
import threading


def receive_responses(client_socket):
    while True:
        try:
            response = client_socket.recv(1024).decode("utf-8")
            # if response == "Инициирована попытка скачивания": 
            #     print("Введите полное имя необходимого файла: ")
            #     need_filename = input()
            #     client_socket.send(need_filename.encode("utf-8"))
            #     wr_file = open("D:\\SPOLKS\\l2\\dwnld_test.txt", "wb")
            #     #while True:
            #     data = client_socket.recv(1024)
            #     if not data:
            #         print("Ошибка открытия файла ")
            #     wr_file.write(data)
            #     wr_file.close() 
            #     print("Передача файла завершена")
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

            if user_input == "UPLOAD":
                #user's file
                print("Введите полное имя файла, который Вы желаете загрузить на сервер")
                f_name_to_upload = input()
               # f = open("D:\\SPOLKS\\l2\\test.txt", "+rb")
                f = open(f_name_to_upload, "+rb")
                data_to_send = f.read(1024)
                while(data_to_send):
                    client_socket.send(data_to_send)
                    data_to_send = f.read(1024)  
            if user_input == "CLOSE":
                break

    finally:
        client_socket.close()


if __name__ == "__main__":
    main()
