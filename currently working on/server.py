from socket import *
import sys
import threading
import time as pytime
from datetime import datetime, time
import os

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
        if url.find(link) != -1 or link.find(url) != -1:
            return True
    return False

# Sending 403 Error
def send_error_response(conn):
    with open("error403.html", 'r') as f:
        resdata = f.read()
    conn.send(b'HTTP/1.1 403 Forbidden\r\nContent-Type: text/html\r\n\r\n' + resdata.encode('ISO-8859-1'))

# Lưu cache
def save_image_cache(data, domain, file_path):
    file_path = file_path.rstrip('/')
    file_name = file_path[file_path.rfind('/')+1:]
    file_path = file_path[:-len(file_name)]
    try:
        os.makedirs("cache/"+domain+file_path, exist_ok = True)
    except:
        return 0
    with open(f'cache/{domain+file_path+file_name}', 'wb') as f:
        f.write(data)
    f.close()
    return os.getcwd() + '/cache/' + domain + file_path + file_name
def save_web_cache(data, file_extension, domain, file_path):
    if file_path[-1] != '/':
        file_path = file_path + '/'
    try:
        os.makedirs("cache/"+domain+file_path, exist_ok = True)
    except:
        return
    with open(f'cache/{domain+file_path}cache.{file_extension}', 'wb') as f:
        f.write(data)
    f.close()

# Trích xuất ảnh
def connect_image(domain, old_file_path, new_file_path, port, message):
    # Kết nối tới server ảnh
    if 'https://' in new_file_path:
        return
    elif 'http://' in new_file_path:
        new_domain = new_file_path[new_file_path.find('://')+3:]
        new_file_path = new_domain[mew_domain.find('/'):]
        new_domain = new_domain[:new_domain.find('/')]        
        server_temp = socket(AF_INET, SOCK_STREAM)
        server_temp.settimeout(timeout)
        try:
            server_temp.connect((new_domain, port))
        except:
            return
        msg = message.decode('ISO-8859-1')
        msg = msg.replace(domain+old_file_path, new_domain+new_file_path)
        msg = msg.replace(domain, new_domain)
        message = bytes(msg, 'utf-8')
        server_temp.sendall(message)
        data = b''
        while 1:
            try:
                temp_data = server_temp.recv(max_receive)
            except:
                server_temp.close()
                break
            else:
                if len(temp_data) > 0:
                    data = data + temp_data
                else:
                    server_temp.close()
                    break
        return save_image_cache(data.split(b'\r\n\r\n')[1], new_domain, new_file_path)
    else:
        new_file_path = '/' + new_file_path
        server_temp = socket(AF_INET, SOCK_STREAM)
        server_temp.settimeout(timeout)
        try:
            server_temp.connect((domain, port))
        except:
            return
        msg = message.decode('ISO-8859-1')
        msg = msg.replace(domain+old_file_path, domain+new_file_path)
        message = bytes(msg, 'utf-8')
        server_temp.sendall(message)
        data = b''
        while 1:
            try:
                temp_data = server_temp.recv(max_receive)
            except:
                server_temp.close()
                break
            else:
                if len(temp_data) > 0:
                    data = data + temp_data
                else:
                    server_temp.close()
                    break
        return save_image_cache(data.split(b'\r\n\r\n')[1], domain, new_file_path)
    
# Xử lý cache
def caching(data, domain, file_path, port, message):
    # Tách header và body
    header = data.split(b'\r\n\r\n')[0]
    body = data.split(b'\r\n\r\n')[1]

    # Tách kiểu dữ liệu
    content_type = header.split(b'Content-Type: ')[1].split(b'\r\n')[0].split(b';')[0].decode('ISO-8859-1')
    media_type = content_type.split('/')[0]
    file_extension = content_type.split('/')[1]
    print("media type:", media_type)
    print("file extension:", file_extension)
    if media_type not in {'text', 'image'}:
        return

    # Lưu cache ảnh được chèn trên web
    data_temp = data.split(b'<img src="')
    if len(data_temp) > 1:
        for i in data_temp[1:]:
            data = bytes(data.decode('ISO-8859-1').replace(i[:i.find(b'\"')].decode('ISO-8859-1'), connect_image(domain, file_path, i[:i.find(b'\"')].decode('ISO-8859-1'), port, message)), 'utf-8')

    # Lưu cache web hiện tại
    if media_type == 'text':
        save_web_cache(data, file_extension, domain, file_path)
    elif media_type == 'image':
        s = save_image_cache(body, domain, file_path)
    with open('cache.txt', 'a+') as cache:
        cache.write(domain + file_path + '\n' + str(datetime.now()) + '\n')
    cache.close()
    
# Xử lý kết nối
def connect(client, addr):
    # Time restriction
    if time_restriction.find("True") != -1:
        if not is_in_time_limit(datetime.now().time()):
            send_error_response(client)
            client.close()
            return
        
    print("Got connected from", addr)

    # Nhận tin từ client
    message = client.recv(max_receive)
    message = message[:-2]+b"Connection: Close\r\n\r\n"
    if message.find(b'Accept-Encoding:') != -1:
        message = message.replace(message[message.find(b'Accept-Encoding:'):].split(b'\r\n')[0] + b'\r\n', b'')
    msg = message.decode('ISO-8859-1')
    print(msg)
    
    # Method, domain, filepath, port
    if len(msg.split()) > 1:
        method = msg.split()[0]
        url = msg.split()[1]
    else:
        client.close()
        return
    if method not in {"GET", "POST", "HEAD"}:
        send_error_response(client)
        client.close()
        return
    if url.find('://') != -1:
        domain = url[url.find('://')+3:]
    else:
        domain = url
    file_path = domain[domain.find('/'):]
    domain = domain[:domain.find('/')]
    if domain.find(':') != -1:
        port = int(domain[domain.find(':')+1:])
        domain = domain[:domain.find(':')]
    else:
        port = 80

    print('request')
    print(message.decode('ISO-8859-1'))
    print("method:", method)
    print("domain:", domain)
    print("port:", port)
    print("filepath:", file_path, '\n')
    
    # Whitelisting 
    if whitelist_enable.find("True") != -1:
        if not is_in_white_list(domain):
            send_error_response(client)
            client.close()
            return
    
    # Kết nối tới server
    server = socket(AF_INET, SOCK_STREAM)
    server.settimeout(timeout)
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
    data = b''
    while 1:
        try:
            temp_data = server.recv(max_receive)
        except:
            server.close()
            break
        else:
            if len(temp_data) > 0:
                client.send(temp_data)
                data = data + temp_data
            else:
                server.close()
                break

    print("finish connect from", addr, "to", domain+file_path)
    client.close()

    # Caching data
    if data.split()[1] != b'200':
       return
    if(method == 'GET'):
        caching(data, domain, file_path, port, message)

# Building proxy  
def main():
    # Khởi tạo proxy
    proxy = socket(AF_INET, SOCK_STREAM)
    proxy.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    proxy.bind((host_ip, host_port))
    print("Ready to serve...")
    proxy.listen(10)

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
