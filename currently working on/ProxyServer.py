from socket import *
import sys
import threading
import time
from datetime import datetime, time, timedelta
import os

# Đọc file config
def read_config_file():
    file = open('config.txt', 'r')
    cache_time = file.readline()
    max_receive = file.readline()
    whitelist_enable = file.readline()
    whitelist_temp = file.readline()
    time_restriction = file.readline()
    time_temp = file.readline()
    timeout = file.readline()
    host_ip = file.readline()
    host_port = file.readline()
      
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
    host_ip = host_ip[host_ip.find('=') + 1:]
    host_ip = host_ip.strip('\n')
    host_port = int(host_port[host_port.find('=') + 1:])
    
    return cache_time, max_receive, whitelist_enable, whitelist, time_restriction, time_limit, timeout, host_ip, host_port

cache_time, max_receive, whitelist_enable, whitelist, time_restriction, time_limit, timeout, host_ip, host_port = read_config_file()

# Kiểm tra thời gian có nằm trong thời gian giới hạn không
def is_in_time_limit(current_time):
    time1 = time(int(time_limit[0]),0,0)
    time2 = time(int(time_limit[1]),0,0)
    if time1 <= current_time and current_time <= time2:
        return True
    return False

# Kiểm tra có nằm trong whitelist không
def is_in_white_list(url):
    for link in whitelist:
        if url.find(link) != -1 or link.find(url) != -1:
            return True
    return False

# Gửi 403 error
def send_error_response(conn):
    with open("error403.html", 'r') as f:
        resdata = f.read()
    conn.send(b'HTTP/1.1 403 Forbidden\r\nContent-Type: text/html\r\n\r\n' + resdata.encode('ISO-8859-1'))

# Xử lý tên miền thành tên file
def fileProcess(file_path):
    file_path = file_path.rstrip('/')
    if file_path.find('?') != -1:
        file_path = file_path[:file_path.find('?')]
    file_name = file_path[file_path.rfind('/')+1:]
    file_path = file_path[:-len(file_name)]
    if not file_path:
        file_path = '/'
    if not file_name:
        file_name = f'cache.html'
    if file_name.find('.') == -1:
        file_name = file_name + f'.html'
    return file_path, file_name
    
# Lụm cache
def getCache(client, domain, file_path):
    file_path, file_name = fileProcess(file_path)
    try:
        f = open('cache.txt', 'r+')
    except:
        return False
    else:
        cache = f.read()
        if cache.find(domain + file_path + file_name) != -1:
            time_cache = datetime.strptime(cache[cache.find(domain + file_path + file_name):].split('\n')[1], '%Y-%m-%d %H:%M:%S.%f')
            time_lim = timedelta(seconds = cache_time)
            print("connect to" + domain + file_path + file_name)
            print("last caching:", time_cache)
            print("time from last caching:", datetime.now() - time_cache)
            if datetime.now() - time_cache >= time_lim:
                new_cache = ""
                for temp_cache in cache.split(domain + file_path + file_name + '\n' + str(time_cache) + '\n'):
                    if temp_cache:
                        new_cache = new_cache + temp_cache
                f.truncate(0)
                f.seek(0)
                f.write(new_cache)
                f.close()
                return False
            f.close
        else:
            return False
                                      
    try:
        f = open(f'cache/{domain+file_path+file_name}', 'rb')
    except:
        return False
    else:
        data = f.read()
        f.close()
        client.send(data)
        return True

# Xử lý cache
def caching(data, domain, file_path):
    # Tách header và body
    header = data.split(b'\r\n\r\n')[0]
    body = data.split(b'\r\n\r\n')[1]

    # Tách kiểu dữ liệu
    media_type = header.split(b'Content-Type: ')[1].split(b'\r\n')[0].split(b';')[0].decode('ISO-8859-1').split('/')[0]
    print("media type:", media_type)
    if media_type not in {'text', 'image'}:
        return

    file_path, file_name = fileProcess(file_path)
        
    os.makedirs("cache/"+domain+file_path, exist_ok = True)
    with open(f'cache/{domain+file_path+file_name}', 'wb') as f:
        f.write(data)
    
    with open('cache.txt', 'a') as cache:
        cache.write(domain + file_path + file_name + '\n' + str(datetime.now()) + '\n')
    
# Xử lý kết nối
def connect(client, addr):
    # Time restriction
    if time_restriction.find("True") != -1:
        if not is_in_time_limit(datetime.now().time()):
            print("TIME RESTRICTION")
            send_error_response(client)
            client.close()
            return
        
    print("Got connected from", addr)

    # Nhận tin từ client
    message = client.recv(max_receive)
    ## Dùng Connection close để ngắt kết nối khi nhận đủ dữ liệu
    message = message[:-2]+b"Connection: Close\r\n\r\n"
    ## Bỏ encode để dễ đọc :")
    if message.find(b'Accept-Encoding:') != -1:
        message = message.replace(message[message.find(b'Accept-Encoding:'):].split(b'\r\n')[0] + b'\r\n', b'')
    msg = message.decode('ISO-8859-1')
    
    # Trích xuất method, domain, filepath, port
    if len(msg.split()) > 1:
        method = msg.split()[0]
        url = msg.split()[1]
    else:
        client.close()
        return
    ## Kiểm tra method
    if method not in {"GET", "POST", "HEAD"}:
        send_error_response(client)
        client.close()
        return
    ##
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

    # print('request')
    # print(message.decode('ISO-8859-1'))
    # print("method:", method)
    # print("domain:", domain)
    # print("port:", port)
    # print("filepath:", file_path, '\n')

    # Whitelisting 
    if whitelist_enable.find("True") != -1:
        if not is_in_white_list(domain):
            print("NOT IN WHITELIST")
            send_error_response(client)
            client.close()
            return
    
    # Kiểm tra cache
    if getCache(client, domain, file_path):
        print("got data from cache <3")
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

    # Lưu vô cache
    if data.split()[1] != b'200':
       return
    if(method == 'GET'):
        caching(data, domain, file_path)

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
        client, addr = proxy.accept()
        
        t = threading.Thread(name=addr[0]+":"+str(addr[1]), target=connect, args=(client, addr))
        t.setDaemon(True)
        t.start()
    sys.exit(0)
    
main()
