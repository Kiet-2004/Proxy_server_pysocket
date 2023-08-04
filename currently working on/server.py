from socket import *
import sys
import threading
import _thread
import time as pytime
from datetime import datetime, time 

if len(sys.argv) != 3:
    print("How to use: python server.py [IP] [PORT]")
    sys.exit(0)

host_ip = sys.argv[1]
port = int(sys.argv[2]) 

#Read the config file
def read_config_file():
    file = open('config.txt', 'r')
    cache_time_temp = file.readline()
    max_receive = file.readline()
    whitelist_enable = file.readline()
    whitelist_temp = file.readline()
    time_restriction = file.readline()
    time_temp = file.readline()
    timeout = file.readline()
      
    cache_time = int(cache_time_temp[cache_time_temp.find('=') + 1:])
    whitelist_temp = whitelist_temp[whitelist_temp.find('=') + 1:]
    time_temp = time_temp[time_temp.find('=') + 1:]
    whitelist = whitelist_temp.split(',')
    time_limit = time_temp.split('-')
    time_limit[0] = int(time_limit[0])
    time_limit[1] = int(time_limit[1])  
    timeout = int(timeout[timeout.find('=') + 1: ])
    max_receive = int(max_receive[max_receive.find('=') + 1:])
    whitelist_enable = whitelist_enable[whitelist_enable.find('=') + 1:]
    time_restriction = time_restriction[time_restriction.find('=') + 1:]
    
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
    ctype = "text/html"
    send_response(conn, b"403 Forbidden", ctype, resdata.encode())

# Building proxy  
def process():
    s = socket(AF_INET, SOCK_STREAM)
    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    s.bind((host_ip, port))
    print("Ready to serve...")
    s.listen(5)
    while True:
        c, adr = s.accept()
        print("Got connected from", adr)
        msg = c.recv(max_receive).decode()
        print(msg)    
        method = msg[0:msg.find(' ')]
        print(method)
        filename = msg.split()[1].partition("/")[2]
        print(filename)
        filetouse = "/" + filename
        print(filetouse)
        c.close()
        break
    sys.exit(0)
    
process()