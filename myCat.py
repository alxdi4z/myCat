import sys
import socket
import getopt
import threading
import subprocess

# define algumas variáveis globais
listen = False
command = False
upload = False
execute = ''
target = ''
upload_destination = ''
port = 0
opts = ''


def usage():
    print('(=｀ω´=) MyNetcat\n')
    print('Uso: meu_netcat.py -t host_alvo -p porta')
    print('-l --listen : Escutando em [host]:[porta] por futuras conexões')
    print('-e --execute=arquivo_para_executar : executa o arquivo fornecido ao receber uma conexão')
    print('-c --command : executa um comando')
    print(
        '-u --upload=destino : ao receber uma conexão faz o upload de um arquivo e o salva em [destino]')
    print()
    print('Exemplos:')
    print('meu_netcat.py -t 192.168.0.1 -p 5555 -l -c')
    print('meu_netcat.py -t 192.168.0.1 -p 5555 -l -u=c:\\alvo.exe')
    print('meu_netcat.py -t 192.168.0.1 -p 5555 -l -e=\'cat /etc/passwd\'')
    print('echo \'ABCDEFG\' | ./meu_netcat.py -t 192.168.0.1 -p 135')
    sys.exit(0)


def client_sender(buffer):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # conecta-se ao nosso host alvo
        client.connect((target, port))
        if len(buffer):
            client.send(buffer)
        while True:
            # agora espera receber dados de volta
            recv_len = 1
            response = ''

            while recv_len:
                data = client.recv(4096)
                recv_len = len(data)
                response += data.decode()

                if recv_len < 4096:
                    break

            print(response,)

            # espera mais dados de entrada
            buffer = input('')
            buffer += '\n'

            # envia os dados
            client.send(buffer.encode('utf-8'))

    except Exception as e:
        print(f'[*] Exception: {e}! Saindo T.T')
        # encerra a conexao
        client.close()


def client_handler(client_socket):
    global upload
    global execute
    global command

    # verifica se é upload
    if len(upload_destination):
        # le todos os bytes e grava em nosso destino
        file_buffer = ''

        # permanece lendo os dados até que nao haja mais nenhum disponivel
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            else:
                file_buffer += data.decode()

        # agora tentaremos gravar esses bytes
        try:
            file_descriptor = open(upload_destination, 'wb')
            file_descriptor.write(file_buffer.encode('utf-8'))
            file_descriptor.close()

            # confirma que gravamos o arquivo
            client_socket.send(f'[*] Arquivo salvo em {upload_destination}')

        except Exception as e:
            client_socket.send(
                f'[!] Erro ao salvar arquivo em {upload_destination}. Exception: {e}')

    # verifica se é execução de comando
    if len(execute):
        # executa o comando
        output = run_command(execute)
        client_socket.send(output)

    # entra em outro laço se um shell de comandos foi solicitado
    if command:
        while True:
            # mostra um prompt simples
            client_socket.send('<meu_netcat:#> '.encode('utf-8'))
            # agora ficamos recebendo dados até vermos um linefeed (tecla enter)
            cmd_buffer = ''
            while '\n' not in cmd_buffer:
                b = client_socket.recv(1024)
                cmd_buffer += b.decode()

            # envia de volta a saída do comando
            response = run_command(cmd_buffer)

            # envia de volta a resposta
            client_socket.send(response)


def server_loop():
    global target

    # se não houver nenhum alvo definido, ouviremos todas as interfaces
    if not len(target):
        target = '0.0.0.0'

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((target, port))
    print(f'[*] Escutando em [{target}]:[{port}]')
    server.listen(5)

    while True:
        client_socket, addr = server.accept()

        # dispara uma thread para cuidar de nosso novo cliente
        client_thread = threading.Thread(
            target=client_handler, args=(client_socket,))
        client_thread.start()


def run_command(com):
    # remove a quebra de linha do comando
    com = com.rstrip()

    # executa o comando e obtém os dados de saída
    try:
        output = subprocess.check_output(
            com, stderr=subprocess.STDOUT, shell=True)
    except Exception as e:
        output = f'[!] Falha ao executar comando. Exception: {e}\r\n'

    # envia os dados de saída de volta para o cliente
    return output


def main():
    global listen
    global opts
    global port
    global execute
    global command
    global upload_destination
    global target

    if not len(sys.argv[1:]):
        usage()

    # le as opcoes da linha de comando
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hle:t:p:cu', [
                                   'help', 'listen', 'execute', 'target', 'port', 'command', 'upload'])
    except getopt.GetoptError as err:
        print(str(err))
        usage()

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        elif o in ('-l', '--listen'):
            listen = True
        elif o in ('-e', '--execute'):
            execute = a
        elif o in ('-c', '--command'):
            command = True
        elif o in ('-u', '--upload'):
            upload_destination = a
        elif o in ('-t', '--target'):
            target = a
        elif o in ('-p', '--port'):
            port = int(a)
        else:
            assert False, '[!] Opção inválida'

    # iremos ouvir ou simplesmente enviar dados de stdin?
    if not listen and len(target) and port > 0:
        # le o buffer da linha de comando
        # isso causara um bloqueio, portanto envie um CTRL-D se nao estiver
        # enviando dados de entrada para stdin
        buffer = sys.stdin.read()

        # envia os dados
        client_sender(buffer)

    if listen:
        server_loop()


main()
