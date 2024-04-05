import asyncio
import os
import socket
import time
import threading
import pyaudio

server_address = ("127.0.0.1", 8080)
connected = False
in_progress = False
stop_event = threading.Event()
stop_call = threading.Event()

def send_keep_alive_message(client_socket, server_address):
    while not stop_event.is_set():
        try:
            time.sleep(10)
            if connected and not in_progress:
                client_socket.sendto(("CLIENT 1").encode("utf-8"), server_address)
                client_socket.recvfrom(1024)
        except Exception as e:
            print(f"Ошибка при отправке контрольного сообщения: {e}")
    
def download_file (client_socket, filename, filesize):
    try:
        file = open(filename, 'wb')
        received_data = 0
        while filesize-received_data>=1020:
            data, _ = client_socket.recvfrom(1024)
            if not data:
                break
            packet_number = int(data[:4].decode())
            packet_data = data[4:]
            client_socket.sendto(str(packet_number).encode("utf-8"), server_address)
            received_data +=len(packet_data)
            file.seek(packet_number * 1020)
            file.write(packet_data)
            percent_complete = (received_data/filesize)*100
            print (f"\r> Прогресс загрузки: {percent_complete:.2f}%", end="")

        if received_data < filesize: #отделяем последнюю порцию, чтобы не захватить лишние данные
            extra_data=filesize-received_data
            data, _ = client_socket.recvfrom(extra_data+4)
            packet_number = int(data[:4].decode())
            packet_data = data[4:]
            client_socket.sendto(str(packet_number).encode("utf-8"), server_address)
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
        

def upload_file (client_socket, server_address, filename):
    print (filename)
    packet_number = 0
    retry = 0
    try:
        with open(filename, 'rb') as file:
            while True:
                data=file.read(1020)
                if not data:
                    break
                data = str(packet_number).zfill(4).encode() + data
                client_socket.sendto(data, server_address)
                ack, _ = client_socket.recvfrom(1024)
                ack = int (ack.decode())
                print (ack)
                if ack == packet_number:
                    packet_number +=1
                    retry =0
                else:
                    print(f"[ПРОЦЕСС] Дейтаграмма {packet_number} потеряна")
                    retry +=1
                    file.seek(packet_number*1020)
                    if retry >=3:
                        print(f"[СИСТЕМА] Принимающая сторона перегружена. Снижение нагрузки...")
                        time.sleep(3)
                        retry = 0
        return "Файл успешно отправлен"
    except Exception as e:
        return f"Ошибка при отправке файла: {str(e)}"

def call_server(client_socket,server_address):
    audio_recorder = pyaudio.PyAudio()
    stream = audio_recorder.open (format=pyaudio.paInt16,channels=1,rate=44100, input=True, frames_per_buffer=1024)
    start_time=time.time()
    while True:
        data=stream.read(1024)
        client_socket.sendto(data,server_address)
        if time.time()-start_time > 15:
            break
        
    stream.stop_stream()
    stream.close()
    audio_recorder.terminate()
    return "CALL STOPPED"

def udp_mode():

    global connected
    global in_progress

    response = ""

    try:
        print("> ", end="")
        while True:

            user_input = input()

            if user_input == "CONNECT":  
                if not connected:
                    try:
                        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        server_ip = "localhost"
                        server_port = 8080
                        client_socket.settimeout(20)
                        client_socket.sendto(("CLIENT 1".encode("utf-8")), (server_ip, server_port))
                        data, _ = client_socket.recvfrom(1024)
                        if data == b'SERVER':
                            connected = True
                            keep_alive_thread = threading.Thread(target=send_keep_alive_message, args=(client_socket, server_address))
                            keep_alive_thread.daemon = True
                            keep_alive_thread.start()

                    except Exception as e:
                        return f"Ошибка соединения с сервером:  {str(e)}"
                else:
                    print (f"\n> Сессия уже идёт.")

            elif user_input.startswith ("DOWNLOAD ") and connected:
                f_name_to_download = user_input[9:]
                client_socket.sendto(("DOWNLOAD " + f_name_to_download).encode("utf-8"), server_address)
                response, _ = client_socket.recvfrom(1024)
                response = response.decode("utf-8")
                filesize = int(response[9:])
                in_progress = True
                download_file (client_socket, f_name_to_download, filesize)
                in_progress = False

            elif user_input.startswith("UPLOAD ") and connected:
                f_name_to_upload = user_input[7:]
                if os.path.exists(f_name_to_upload):
                    filesize = os.path.getsize(f_name_to_upload)
                    size=str(filesize)
                    client_socket.sendto(((user_input + ' ' + size).encode("utf-8")), server_address)
                    in_progress = True
                    upload_file(client_socket, server_address, f_name_to_upload)
                    response, _ = client_socket.recvfrom(1024)
                    response = response.decode("utf-8")
                    in_progress = False
                else:
                    print (f"> Файл с таким именем не существует.")
                

            elif user_input=="CALL SERVER" and connected:
                client_socket.sendto(user_input.encode("utf-8"), server_address)
                in_progress = True
                response = call_server(client_socket, server_address)
                in_progress = False

            elif user_input == "CLOSE" and connected:
                    client_socket.sendto(user_input.encode("utf-8"), server_address)
                    connected = False
                    stop_event.set()
                    client_socket.close()
                    print (f"> Cоединение закрыто.")
            
            elif user_input == "Q":
                break

            else:
                if connected:
                    client_socket.sendto(user_input.encode("utf-8"), server_address)    
                    response, _ = client_socket.recvfrom(1024)
                    response = response.decode("utf-8")
            
            print("> ", response, "\n> ", end="")
            

    except socket.timeout:  
        client_socket.sendto(user_input.encode("utf-8"), server_address)
        connected = False
        stop_event.set()
        client_socket.close()
        print (f"> Cоединение закрыто.")
    
def main():
    udp_mode()

if __name__ == "__main__":
    main()
