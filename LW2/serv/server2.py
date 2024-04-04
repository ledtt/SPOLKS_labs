import socket
import time
import os

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ("localhost", 12345)
server_socket.bind(server_address)

client = 0
upload_in_progress = False
download_in_progress = False
start_time = 0

def handle_echo(data):
    return data


def handle_time(start_time):
    end_time = time.time()
    cur_time = end_time - start_time
    return str(cur_time)


def handle_help():
    print("[СИСТЕМА] Получен запрос на справку")
    return "Доступные команды:\n" "ECHO <текст>\n" "TIME\n" "CLOSE\n" "HELP"

def handle_upload(connection, filename, filesize, resume=False):
    global upload_in_progress
    try:
        file = open (filename, "ab" if resume else "wb")
        received_data = 0
        upload_in_progress = True
        while filesize-received_data>=1024:
            data = connection.recv(1024)
            if not data:
                break
            received_data +=len(data)
            file.write(data)
            percent_complete = (received_data/filesize)*100
            print (f"\r> Прогресс загрузки: {percent_complete:.2f}%", end="")

        if received_data < filesize: #отделяем последнюю порцию, чтобы не захватить лишние данные
            extra_data=filesize-received_data
            data = connection.recv(extra_data)
            file.write(data)
            file.close()
            print (f"\r> Прогресс загрузки: 100.00%\n")
        upload_in_progress = False
        return "Файл успешно загружен на сервер"
    except ConnectionResetError:
        return "Ошибка соединения"
    
    
def handle_download(connection, filename, resume=False):
    global download_in_progress
    try:
        filesize = os.path.getsize(filename)
        connection.send(("FILESIZE " + str(filesize)).encode("utf-8"))
        print (filename)
        if os.path.exists(filename):
            download_in_progress = True
            if not resume:
                with open(filename, 'rb') as file:
                    while True:
                        data=file.read(1024)
                        if not data:
                            break
                        connection.sendall(data)
            else:
                with open(filename, 'rb') as file:
                    file.seek(int(connection.recv(1024).decode("utf-8")))
                    while True:
                        data = file.read(1024)
                        if not data:
                            break
                        connection.send(data)
            download_in_progress = False
            return "Файл успешно отправлен"
        else:
            return "Файл не существует"
    except Exception as e:
        return f"Ошибка при отправке файла: {str(e)}"
    except ConnectionResetError:
        return "Ошибка соединения"

def reconnect_and_resume(filename,mode):
    global client
    global upload_in_progress
    global download_in_progress
    try:
        new_conn, new_addr = server_socket.accept()
        client_number = new_conn.recv(1024).decode("utf-8")
        if client == client_number[7:]:
            print(f"[ОТЛАДКА] Соединение с клиентом {new_addr} {client_number} восстановлено. Возобновление передачи данных...")
            if mode == 1:
                new_conn.sendall(("RESUME_DOWNLOAD " + filename).encode("utf-8"))
                response = handle_download(new_conn, filename, resume=True)
                new_conn.sendall(response.encode('utf-8'))

            if mode == 2:
                new_conn.sendall(("RESUME_UPLOAD " + filename).encode("utf-8")) #передаем имя
                response_size = new_conn.recv(1024).decode("utf-8") # получаем полный размер
                filesize =int(response_size[9:])
                position = os.path.getsize(filename)
                last_data = filesize-position
                pos=str(position)
                new_conn.sendall(pos.encode("utf-8"))
                response = handle_upload(new_conn, filename, last_data, resume=True)
                new_conn.sendall(response.encode('utf-8'))
    
        else:
            print (f"[СОСТОЯНИЕ СОЕДИНЕНИЯ] Соединение с клиентом {client} было окончательно разорвано")
            print(f"[СОСТОЯНИЕ СОЕДИНЕНИЯ] Установлено новое соединение:{new_addr} {client_number}")
            #if upload_in_progress:
            #    os.remove(os.path(filename))
            upload_in_progress = False
            #else: 
            download_in_progress = False
            client = client_number[7:]

        return new_conn
         
    except Exception as e:
        print(f"[CОСТОЯНИЕ СОЕДИНЕНИЯ] Ошибка при восстановлении соединения: {str(e)}")


def main():

    global start_time
    global client
    connected = False
    download_filename = ""
    upload_filename = ""

    server_socket.listen(1)
    start_time = time.time()

    print("[СИСТЕМА] Сервер запущен на {}:{}".format(*server_address))



    while True:
        if not connected:
            if upload_in_progress:
                print(f"[СОСТОЯНИЕ СОЕДИНЕНИЯ] Разрыв соеднения с клиентом {client} во время получения файла. Пытаемся восстановить.")
                conn = reconnect_and_resume(upload_filename, 2)
                connected = True
            elif download_in_progress:
                print(f"[СОСТОЯНИЕ СОЕДИНЕНИЯ] Разрыв соеднения с клиентом {client}  во время отправки файла. Пытаемся восстановить.")
                conn = reconnect_and_resume (download_filename, 1)
                connected = True
            else:
                conn, addr = server_socket.accept()
                client_number = conn.recv(1024).decode("utf-8")
                conn.sendall("OK".encode("utf-8"))
                client = client_number[7:]
                print(f"[СОСТОЯНИЕ СОЕДИНЕНИЯ] Установлено новое соединение:{addr} {client_number}")
                connected = True

            while connected:
                try:
                    data = conn.recv(1024)
                    if not data:
                        break

                    commands = data.decode('utf-8').split('/n')
                    print (commands)
                    for command in commands:
                        command = command.strip()
                        if not command:
                            continue  # Пропускаем пустые строки

                        command_parts = command.split(' ', 2)
                        cmd = command_parts[0]
                        result=""

                        if cmd == 'ECHO':
                            result = handle_echo(command_parts[1])
                        elif cmd == 'TIME':
                             result = handle_time(start_time)
                        elif cmd == 'HELP':
                            result = handle_help()
                
                        elif cmd == "UPLOAD": 
                            upload_filename = command_parts[1]
                            filesize = int(command_parts[2])
                            result = handle_upload(conn, upload_filename, filesize) 
                        elif cmd.startswith ("DOWNLOAD"):
                            download_filename = command_parts[1]
                            resume = cmd == "DOWNLOAD_RESUME"
                            result = handle_download(conn, download_filename, resume)

                        elif cmd == 'CLOSE':
                            conn.close()
                            print(f"[СОСТОЯНИЕ СОЕДИНЕНИЯ] Соединение с клиентом {client} разорвано.")
                            connected = False
                            break
                        else:
                            result = 'Неизвестная команда'

                        conn.sendall(result.encode('utf-8'))

                except ConnectionResetError:
                    connected = False
                    if not upload_in_progress and not download_in_progress:
                        print(f"[СОСТОЯНИЕ СОЕДИНЕНИЯ] Соединение с клиентом {client} разорвано.")

                except Exception as e:
                    print(f'Произощла ошибка: {str(e)}')

                finally:
                    break

        
if __name__ == "__main__":
    main()
