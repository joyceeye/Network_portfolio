"""5700 - project 1"""
import socket
import json
import random
import string
import urllib.request
import random
import ssl

# server side
# instead of transferred library from each other
def random_pick_secret_word(url):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    file = urllib.request.urlopen(url, context=context)
    word = file.readlines()
    secret_word = random.choice(word).decode('utf-8').strip()  # Add decode('utf-8') because urlopen returns bytes
    file.close()
    return secret_word


def check_the_word_position(guess_word, secret_word):
    marks = []
    # secret_word = client.random_pick_secret_word(url)
    for i in range(len(guess_word)):
        if guess_word[i] == secret_word[i]:
            marks.append(2)
        elif guess_word[i] in secret_word:
            marks.append(1)
        else:
            marks.append(0)
    return marks


def server_handle_guess(guess_data, secret_word, game_id):
    if guess_data["id"] != game_id:
        raise ValueError("Invalid game ID")
    
    
    if guess_data["word"] == secret_word: 
        response = {
            "type": "bye",
            "id": game_id,
            "flag": "" 
        }
        response_string = json.dumps(response) + "\n"
        print(f"sending the second message: {response_string}")
        return response_string

    
    marks = check_the_word_position(guess_data["word"], secret_word)
    # keeps the history message
    response = {
        "type": "retry",
        "id": game_id,
        "guesses": [{
            "word": guess_data["word"],
            "marks": marks
        }]
    }

    response_string = json.dumps(response) + "\n"
    print(f"sending the second message: {response_string}")

    return response_string


def main():
    # create a server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    port = 27993 # this port could be changed to other numbers

    # public host name
    server.bind((socket.gethostname(), port))

    server.listen(5)
    print(f"server is listening on port {port}")

    # server and client's connection
    print("test for while - true")
    try:
        # client sends a start msg
        # server recv
        client, addr = server.accept()
        print(f"connected client at {addr}")

        data = client.recv(1024).decode()
        print(f"Server: Data received from client are: {data}")

        # {"type": "start", "id": <string>}\n
        game_id = ""
        start_msg = {"type": "start", "id": game_id}
        message = json.dumps(start_msg) + "\n" #json format
        client.send(message.encode())
        print(f"Server sends the first message(S->C): {start_msg}") 
        
        # Pick secret word
        url = "https://4700.network/projects/project1-words.txt"
        secret_word = random_pick_secret_word(url)
        print(f"Server pick a secret word is: {secret_word}")
        
        guess_count = 0
        # hanlde guess
        while guess_count < 500:
            try:
                guess_data = client.recv(1024).decode()
                guess_data = json.loads(guess_data) # loads data
                response_string = server_handle_guess(guess_data, secret_word, game_id)
                client.send(response_string.encode())
                if "bye" in response_string:
                    break
                guess_count += 1
                
            except Exception as e:
                error_msg = {"type": "error", "message": str(e)}
                error_msg1 = json.dumps(error_msg) + "\n"
                client.send(error_msg1.encode())
                break

        client.close()
    
    except OSError as e:
            print(f"Socket error occurred: {e}")

    except KeyboardInterrupt:
        server.close()
    finally:
        server.close()

if __name__ == "__main__":
    main()