import socket
import sys
import threading
import time as pytime
import configparser
from datetime import datetime, time 

def read_config_file(filename):
    config = configparser.ConfigParser()
    config.read(filename)

    # Get values from the "default" section
    cache_time = config.getint('default', 'cache_time')
    whitelisting = config.get('default', 'whitelisting')
    time = config.get('default', 'time')
    timeout = int(config.get('default', 'timeout'))
    enabling_whitelist = config.getboolean('default', 'enabling_whitelist')
    time_restriction = config.getboolean('default', 'time_restriction')
    max_recieve = config.getint('default', 'max_recieve')

    # Process the whitelisting string into a list
    whitelist_items = [item.strip() for item in whitelisting.split(',')]
    timelist=[timeline.strip() for timeline in time.split('-')]

    return cache_time, whitelist_items, timelist, timeout, enabling_whitelist, time_restriction, max_recieve

file_path = 'config.ini'
cache_time, whitelist, allow_time,timeout, enabling_whitelist, time_restriction, max_recieve = read_config_file(file_path)

def send_response(conn, status_code, content_type, response_data):
    header = f"HTTP/1.1 {status_code}\r\n"
    header += f"Content-Length: {len(response_data)}\r\n"
    header += f"Content-Type: {content_type}\r\n\r\n"

    response = header.encode() + response_data
    conn.send(response)
    return response.decode()

def send_error_response(conn):
    with open("error403.html", 'r') as f:
        resdata = f.read()
    ctype = "text/html"
    send_response(conn, b"403 Forbidden", ctype, resdata.encode())

cache = {}
def is_cache_valid(url):
    if url in cache:
        current_time = pytime.time()
        last_update_time = cache[url]["last_update_time"]
        if current_time - last_update_time < cache_time:
            return True
    return False

def is_in_allowing_time(t):
    if not time_restriction:
        return True
    time1 = time(int(allow_time[0]),0,0)
    time2 = time(int(allow_time[1]),0,0)
    if time1 <= t <= time2:
        return True
    return False

def is_in_whitelist(url):
    for link in whitelist:
        if url in link:
            return True
    return False

def proxy(conn, proxy_url,data):
    request = data.split(b'\r\n')[0]
    req_method = request.split(b' ')[0]
    http_pos = proxy_url.decode().find("://") # find pos of ://
    if (http_pos==-1):
        temp = proxy_url.decode()
    else:
        temp = proxy_url.decode()[(http_pos+3):] # get the rest of url
    if not is_in_allowing_time(datetime.now().time()):
        send_error_response(conn)
        conn.close()
        return
    if is_cache_valid(temp):
        print(f"[*] SENDING CACHED RESPONSE FOR: {temp}")
        conn.send(cache[temp]["cache"])
        conn.close()
        return    
    url=temp
    port_pos = temp.find(":") # find the port pos (if any)
    # find end of web server
    webserver_pos = temp.find("/")
    if webserver_pos == -1:
        webserver_pos = len(temp)

    webserver = ""
    port = -1
    if (port_pos==-1 or webserver_pos < port_pos): 

        # default port 
        port = 80 
        webserver = temp[:webserver_pos] 
        tail = temp[webserver_pos:]
    else: # specific port 
        port = int((temp[(port_pos+1):])[:webserver_pos-port_pos-1])
        webserver = temp[:port_pos] 
        tail = temp[webserver_pos:]
    if enabling_whitelist:
        if not is_in_whitelist(webserver):
            send_error_response(conn)
            conn.close()
            return
    sv = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    sv.settimeout(timeout)
    try:
        sv.connect((webserver, port))
        firstline = f"{req_method.decode()} {tail} {request.split(b' ')[2].decode()}"
        secondline = f"Host: {webserver}:{port}"
        headers = data.split(b'\r\n\r\n')
        temp = headers[0].split(b'\r\n')
        temp[0] = firstline.encode()
        temp[1] = secondline.encode()
        temp = b'\r\n'.join(temp)+ b'\r\n'+ b'Connection: Close' + b"\r\n\r\n" +headers[1]
        #proxy_res= firstline.encode() + temp.encode()
        print(f"SENDING REQUEST TO WEB SERVER: \n{temp.decode()}")
        sv.send(temp)
        res=b""
        while True:
            # receive data from web server
            temp=sv.recv(max_recieve)
            res = res+temp
            if (len(temp)<=0): break
            try:
                print(f"RECIVED WEB SERVER RESPONSE: \n{temp.decode()}")
            except:
                print(f"RECIVED WEB SERVER RESPONSE: \n{temp.decode('latin1')}")
        conn.send(res) # send to browser/client   
        cache[url]={
            "cache": res,
            "last_update_time": pytime.time() 
        }
        print("here is cache")
        print(cache[url])
        print("here is cache")
        sv.close()
        conn.close()
    except socket.timeout:
        send_error_response(conn)
        print("Connection timed out. Unable to connect to the server.")
        sv.close()
        conn.close()

def process_get_request(conn, req_url,data):
    req_url1 = req_url.strip(b'/')
    if req_url1 == b"":
        url = 'index.html'
        ctype = "text/html"
    elif req_url1 == b"favicon.ico":
        url = req_url1.decode()
        ctype = "image/x-icon"
    else:
        url = req_url1.decode()
        ctype = "application/x-www-form-urlencoded"

    try:
        with open(url, 'rb') as f:
            resdata = f.read()
    except IOError:
        # Handle proxy 
        proxy(conn, req_url,data)
        return ctype, b'', True

    return ctype, resdata, False

def process_head_request(conn, req_url,data):
    req_url1 = req_url.strip(b'/')
    if req_url1 == b"":
        url = 'index.html'
        ctype = "text/html"
    elif req_url1 == b"favicon.ico":
        url = req_url1.decode()
        ctype = "image/x-icon"
    else:
        url = req_url1.decode()
        ctype = "application/x-www-form-urlencoded"

    try:
        with open(url, 'rb') as f:
            resdata = f.read()
    except IOError:
        # Handle proxy 
        proxy(conn, req_url,data)
        return True
    header = f"HTTP/1.1 200\r\n"
    header += f"Content-Length: {len(resdata)}\r\n"
    header += f"Content-Type: {ctype}\r\n\r\n"
    conn.send(header.encode())
    conn.close()
    return True

def process_post_request(conn, req_url, data):
    
    if req_url == b"submit":
        # Handle form submission
        try:
            post_data = data.split(b'\r\n\r\n')[1]
            with open("post.txt", 'a') as f:
                f.write('\n'+post_data.decode())
            resdata = "success uploading".encode()
            ctype = "text/plain"
            temp=send_response(conn, "200", ctype, resdata)
            print(f"RESPONSE: {temp}")
            conn.close()
        except IOError:
            with open("error403.html", 'rb') as f:
                resdata = f.read()
            ctype = "text/html"
            send_response(conn, "403 Forbidden", ctype, resdata)
            conn.close()
    elif req_url == b"upload":
        # Handle file upload 
        des1 = data.decode().find('File-Name:')
        des2 = data.find(b'\r\n\r\n')
        filename = data.decode()[des1 + 11:].split('\n')[0]
        url = filename.strip('\n').strip('\r').strip('\r\n')
        resdata = f'You have uploaded: {filename}'.encode()
        ctype = "text/plain"  # Set a generic Content-Type since it's a text response
        with open(url, 'wb') as f:  # Use 'wb' mode for writing binary data
            f.write(data[des2 + 4:])
        send_response(conn, b"403 Forbidden", ctype, resdata)
        conn.close()
    else:
        try:
            proxy(conn, req_url, data)
        except:
            # Return a 403 Forbidden response for unknown POST requests
            send_error_response(conn)
            conn.close()

def process(conn, addr):
    while True:
        data = conn.recv(max_recieve)
        if not data:
            return

        print(data.decode())

        request = data.split(b'\r\n')[0]
        req_method = request.split(b' ')[0]
        req_url = request.split(b' ')[1]
        #proxy_url = request.split(b' ')[1]
        print(f"[*] Request from user: {addr}")
        proxy = False
        if req_method == b'GET':
            ctype, resdata, proxy = process_get_request(conn, req_url,data)
        elif req_method == b'HEAD':
            proxy = process_head_request(conn, req_url,data)
        elif req_method == b'POST':
            process_post_request(conn, req_url.strip(b'/'), data)
            return
        else:
            # Return a 403 Forbidden response for unsupported methods
            send_error_response(conn)
            conn.close()
            return
        if proxy == False:    
            send_response(conn, "200", ctype, resdata)
            conn.close()
        return

def main():
    if len(sys.argv) != 3:
        print("Usage: python server.py <HOST> <PORT>")
        sys.exit(1)

    HOST = sys.argv[1]
    PORT = int(sys.argv[2])

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    print(f'Server running on {HOST}:{PORT}')

    s.listen(5)
    while True:
        client, caddr = s.accept()
        thread = threading.Thread(target=process, args=(client,caddr))
        thread.start()

if __name__ == "__main__":
    main()
