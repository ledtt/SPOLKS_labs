import socket
import os
import time
import pyaudio
import threading

calling = False


def handle_help():
    print("[СИСТЕМА] Получен запрос на справку")
    return "Доступные команды:\n" "CALL SERVER\n" "UPLOAD <имя файла>\n" "DOWNLOAD <имя файла>\n" "CONNECT\n" "CLOSE\n" "HELP"

def handle_upload_udp(server_socket, client_address, filename, filesize):
    try:
        file = open(filename, 'wb')
        received_data = 0
        while filesize-received_data>=1020:
            data, _ = server_socket.recvfrom(1024)
            if not data:
                break
            packet_number = int(data[:4].decode())
            packet_data = data[4:]
            server_socket.sendto(str(packet_number).encode("utf-8"), client_address)
            received_data +=len(packet_data)
            file.seek(packet_number * 1020)
            file.write(packet_data)
            percent_complete = (received_data/filesize)*100
            print (f"\r> Прогресс загрузки: {percent_complete:.2f}%", end="")

        if received_data < filesize: #отделяем последнюю порцию, чтобы не захватить лишние данные
            extra_data=filesize-received_data
            data, _ = server_socket.recvfrom(extra_data+4)
            packet_number = int(data[:4].decode())
            packet_data = data[4:]
            server_socket.sendto(str(packet_number).encode("utf-8"), client_address)
            received_data +=len(packet_data)
            file.seek(packet_number * 1020)
            file.write(data)

        file.close()
        print (f"\r> Прогресс загрузки: 100.00%\n")
        return "Файл успешно загружен на сервер"
    except socket.timeout:
        return "Превышено время ожидания. Сессия завершена"
    except Exception as e:
        print(f"Error handling upload request: {e}")



def handle_download_udp(server_socket, client_address, filename):
    try:
        filesize = os.path.getsize(filename)
        server_socket.sendto(("FILESIZE " + str(filesize)).encode("utf-8"), client_address)
        print (filename)
        if os.path.exists(filename):
            with open(filename, 'rb') as file:
                packet_number = 0
                retry = 0
                while True:
                    data = file.read(1020)
                    if not data: 
                        break
                    data = str(packet_number).zfill(4).encode() + data 
                    server_socket.sendto(data, client_address)
                    ack, _ = server_socket.recvfrom(1024)
                    ack = int(ack.decode())
                    print (ack)
                    if ack == packet_number:
                        packet_number += 1
                        retry = 0
                    else: 
                        print(f"[ПРОЦЕСС] Дейтаграмма {packet_number} потеряна")
                        retry += 1
                        file.seek(packet_number*1020)
                        if retry >= 3:
                            print(f"[СИСТЕМА] Принимающая сторона перегружена. Снижение нагрузки...")
                            time.sleep(3)
                            retry = 0
            return "Файл успешно отправлен"    
        else:
            return "Файл не существует"
    except Exception as e:
        return f"Ошибка при отправке файла: {str(e)}"

def handle_call(server_socket):
    try:
        audio_player = pyaudio.PyAudio()
        stream = audio_player.open(format=pyaudio.paInt16, channels=1, rate=44100, output=True)
        start_time = time.time()
        while True:
            data, _ = server_socket.recvfrom(8096)  # Получаем данные звука
            if time.time()-start_time>15:
                break
            else: 
                stream.write(data)  # Воспроизводим звук

        stream.stop_stream()
        stream.close()
        audio_player.terminate()
    except Exception as e:
        print(f"Error handling call request: {e}")

def udp_server(host,port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    print(f"[СИСТЕМА] Сервер запущен на {host} {port}")
    connected = False

    while True:
        if not connected:
            data, client_address = server_socket.recvfrom(1024)
            data = data.decode("utf-8")
            if data.startswith ("CLIENT"):
                print(data + " is connected")
                server_socket.sendto(("SERVER").encode("utf-8"), client_address)
                connected = True

        while connected:
            try:
                data, client_address = server_socket.recvfrom(1024)
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

                    if cmd == 'HELP':
                        result = handle_help()
                    elif cmd == "UPLOAD":
                        upload_filename = command_parts[1]
                        filesize = int (command_parts[2]) 
                        result = handle_upload_udp(server_socket, client_address, upload_filename, filesize)
                    elif cmd == "DOWNLOAD":
                        download_filename = command_parts[1]
                        resume = cmd == "DOWNLOAD_RESUME"
                        result = handle_download_udp (server_socket, client_address, download_filename)
                    elif cmd == "CALL":
                        handle_call(server_socket)

                    elif cmd == "CLOSE":
                        print(f"[СОСТОЯНИЕ] Сессия завершена.")
                        connected = False
                        break
                    elif cmd == "CLIENT":
                        data = "CLIENT"
                        server_socket.sendto(data.encode("utf-8"), client_address)
                        connected = True
                        server_socket.settimeout(15)
                    else:
                        result = "Неизвестная команда"
                        
                    server_socket.sendto(result.encode("utf-8"), client_address)
             

            except socket.timeout:
                print("[СОСТОЯНИЕ] Клиент не активен. Сессия завершена")
                connected = False

            except Exception as e:
                print(f'Произощла ошибка: {str(e)}')

            finally:
                break
                    

if __name__ == "__main__":
    udp_server("127.0.0.1", 8080)