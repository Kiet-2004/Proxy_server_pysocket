from socket import *
import sys
import threading
import time as pytime
from datetime import datetime, time 

if len(sys.argv) != 3:
    print("How to use: python server.py [IP] [PORT]")
    sys.exit(0)

host_ip = sys.argv[1]
host_port = int(sys.argv[2]) 
death_flag = False
#Read the config file
def read_config_file():
    file = open('config.txt', 'r')
    cache_time = file.readline()
    max_receive = file.readline()
    whitelist_enable = file.readline()
    whitelist_temp = file.readline()
    time_restriction = file.readline()
    time_temp = file.readline()
    timeout = file.readline()
      
    cache_time = int(cache_time[cache_time.find('=') + 1:])
    max_receive = int(max_receive[max_receive.find('=') + 1:])
    whitelist_enable = whitelist_enable[whitelist_enable.find('=') + 1:]
    whitelist_temp = whitelist_temp[whitelist_temp.find('=') + 1:]
    whitelist = whitelist_temp.split(',')
    time_restriction = time_restriction[time_restriction.find('=') + 1:]
    time_temp = time_temp[time_temp.find('=') + 1:]
    time_limit = time_temp.split('-')
    time_limit[0] = int(time_limit[0])
    time_limit[1] = int(time_limit[1])  
    timeout = int(timeout[timeout.find('=') + 1:])
    
    return cache_time, max_receive, whitelist_enable, whitelist, time_restriction, time_limit, timeout

cache_time, max_receive, whitelist_enable, whitelist, time_restriction, time_limit, timeout = read_config_file()


# Checking time
def is_in_time_limit(current_time):
    time1 = time(int(time_limit[0]),0,0)
    time2 = time(int(time_limit[1]),0,0)
    if time1 <= current_time and current_time <= time2:
        return True
    return False

# Checking whitelist
def is_in_white_list(url):
    for link in whitelist:
        if url in link:
            return True
    return False

#Sending response
def send_response(conn, status_code, content_type, response_data):
    header = f"HTTP/1.1 {status_code}\r\n"
    header += f"Content-Length: {len(response_data)}\r\n"
    header += f"Content-Type: {content_type}\r\n\r\n"

    response = header.encode() + response_data
    conn.send(response)
    return response.decode()

# Sending 403 Error
def send_error_response(conn):
    with open("error403.html", 'r') as f:
        resdata = f.read()
    conn.send(b'HTTP/1.1 403 Forbidden\r\nContent-Type: text/html\r\n\r\n' + resdata.encode())

# Xử lý kết nối
def connect(client, addr):
    print("Got connected from", addr)

    # Nhận tin từ client
    message = client.recv(max_receive)
    msg = message.decode()
    print(msg)
    
    
    # Phương thức, tên miền, filepath, port
    if len(msg.split()) > 1:
        method, url = msg.split(' ')[0], msg.split(' ')[1]
    else:
        client.close()
        return
    if method not in {"GET", "POST", "HEAD"}:
        send_error_response(client)
        client.close()
        return
    if url.find('://') != -1:
        domain = url[url.find('://')+3:]
    file_path = domain[domain.find('/'):]
    domain = domain[:domain.find('/')]
    if domain.find(':') != -1:
        port = int(domain[domain.find(':')+1:])
        domain = domain[:domain.find(':')]
    else:
        port = 80
    print(method, url, '\n')
    print("domain:", domain)
    print("port:", port)
    print("filepath:", file_path)

    # Kết nối tới server
    server = socket(AF_INET, SOCK_STREAM)
    server.settimeout(900)
    try:
        server.connect((domain, port))
    except:
        send_error_response(client)
        print("error")
        client.close()
        global death_flag
        death_flag = True
        return
    server.sendall(message)
    
    # Nhận thông tin từ server
    while 1:
        try:
            data = server.recv(max_receive)
        except:
            server.close()
            break
        else:
            if len(data) > 0:
                print(data)
                client.send(data)
            else:
                server.close()
                break
    print("finish connect from", addr, "to", domain+file_path)
    client.close()

# Building proxy  
def main():
    # Khởi tạo proxy
    proxy = socket(AF_INET, SOCK_STREAM)
    proxy.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    proxy.bind((host_ip, host_port))
    print("Ready to serve...")
    proxy.listen(5)

    # Chờ kết nối từ client
    while 1:
        if death_flag:
            break
        client, addr = proxy.accept()
        t = threading.Thread(name=addr[0]+":"+str(addr[1]), target=connect, args=(client, addr))
        t.setDaemon(True)
        t.start()
    sys.exit(0)
    
main()
